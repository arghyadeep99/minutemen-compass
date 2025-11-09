"""
Scraper for UMass CICS pages (advising FAQs, approved alternate courses,
courses, research areas, contact us). Fetches raw HTML, stores to disk,
and builds a searchable JSON index for quick retrieval.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


DEFAULT_CICS_URLS: List[str] = [
    "https://www.cics.umass.edu/advising/ms-program-advising/ms-advising-faqs",
    "https://www.cics.umass.edu/academics/academic-policies/graduate-programs-policies/approved-alternate-courses",
    "https://www.cics.umass.edu/academics/courses",
    "https://www.cics.umass.edu/research/research-areas?page=0",
    "https://www.cics.umass.edu/about/contact-us",
]

USER_AGENT = "UMassCampusAgent/1.0 (+https://example.edu) Python-httpx"


def _create_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(20.0, connect=10.0),
        follow_redirects=True,
    )


def _slugify_url(url: str) -> str:
    parsed = urlparse(url)
    # Use path and query to create a filesystem-safe name
    base = (parsed.netloc + parsed.path).strip("/").replace("/", "_")
    if parsed.query:
        base += "_" + re.sub(r"[^a-zA-Z0-9]+", "-", parsed.query).strip("-")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", base).strip("-")
    return slug or "index"


def _extract_text(soup: BeautifulSoup) -> str:
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


@dataclass
class CicsPage:
    url: str
    title: Optional[str]
    html_file: str  # relative path under data_dir
    text: Optional[str]


def _fetch_single(url: str, out_dir: Path) -> Optional[CicsPage]:
    with _create_client() as client:
        try:
            resp = client.get(url)
            resp.raise_for_status()
        except Exception:
            return None

    soup = BeautifulSoup(resp.text, "lxml")
    title_tag = soup.find("h1") or soup.find("title")
    title = (title_tag.get_text(strip=True) if title_tag else "").strip() or None
    text = _extract_text(soup)

    slug = _slugify_url(url)
    html_path = out_dir / f"{slug}.html"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path.write_text(resp.text, encoding="utf-8")

    rel_html = str(html_path.relative_to(out_dir.parent))
    return CicsPage(url=url, title=title, html_file=rel_html, text=text)


def refresh_cics_pages(
    urls: Optional[List[str]] = None,
    data_dir: Path | str = "data",
    raw_subdir: str = "cics_pages",
) -> List[Dict]:
    """
    Force refresh of all provided URLs. Stores raw HTML files under data/{raw_subdir}
    and writes an index to data/cics_pages.json with text for searching.
    """
    urls = list(urls or DEFAULT_CICS_URLS)
    base_dir = Path(data_dir)
    raw_dir = base_dir / raw_subdir
    base_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    pages: List[CicsPage] = []
    for url in urls:
        page = _fetch_single(url, out_dir=raw_dir)
        if page:
            pages.append(page)

    # Persist index
    data = [asdict(p) for p in pages]
    (base_dir / "cics_pages.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (base_dir / "cics_pages.meta.json").write_text(
        json.dumps(
            {
                "last_updated_ts": time.time(),
                "count": len(data),
                "raw_dir": str(raw_dir),
                "sources": urls,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return data


def get_cics_pages_cached(
    urls: Optional[List[str]] = None,
    cache_hours: int = 24,
    data_dir: Path | str = "data",
    force: bool = False,
) -> List[Dict]:
    """
    Return cached CICS pages if recent; otherwise refresh.
    """
    urls = list(urls or DEFAULT_CICS_URLS)
    base_dir = Path(data_dir)
    data_path = base_dir / "cics_pages.json"
    meta_path = base_dir / "cics_pages.meta.json"

    now = time.time()
    try:
        if not force and data_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            last_ts = float(meta.get("last_updated_ts", 0))
            cached_count = int(meta.get("count", 0))
            if now - last_ts <= cache_hours * 3600 and cached_count > 0:
                return json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    return refresh_cics_pages(urls=urls, data_dir=data_dir)


def _score_text(query: str, title: str, text: str) -> int:
    """
    Very simple relevance score: sum of word occurrences, with higher weight for title.
    """
    q = query.strip().lower()
    if not q:
        return 0
    words = [w for w in re.split(r"\W+", q) if w]
    if not words:
        return 0

    ttl = (title or "").lower()
    body = (text or "").lower()

    score = 0
    for w in words:
        score += 5 * ttl.count(w)
        score += body.count(w)
    return score


def _make_snippet(text: str, query: str, window: int = 180) -> str:
    t = text or ""
    q = query.strip()
    if not t:
        return ""
    # Find first occurrence of any query word
    words = [w for w in re.split(r"\W+", q) if w]
    idx = -1
    for w in words:
        i = t.lower().find(w.lower())
        if i != -1:
            idx = i
            break
    if idx == -1:
        idx = 0
    start = max(0, idx - window // 2)
    end = min(len(t), start + window)
    snippet = t[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(t):
        snippet = snippet + "…"
    return snippet


def search_cics_pages(
    query: str,
    data_dir: Path | str = "data",
    limit: int = 5,
) -> Dict:
    """
    Search cached CICS pages by simple keyword scoring. Returns top matches with snippets.
    """
    base_dir = Path(data_dir)
    data_path = base_dir / "cics_pages.json"
    if not data_path.exists():
        return {"results": [], "count": 0, "note": "No CICS cache found. Run refresh first."}

    items: List[Dict] = json.loads(data_path.read_text(encoding="utf-8"))
    scored: List[Tuple[int, Dict]] = []
    for it in items:
        s = _score_text(query, it.get("title") or "", it.get("text") or "")
        if s > 0:
            scored.append((s, it))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = []
    for _, it in scored[: max(1, int(limit))]:
        snippet = _make_snippet(it.get("text") or "", query=query, window=220)
        top.append(
            {
                "url": it.get("url"),
                "title": it.get("title"),
                "html_file": it.get("html_file"),
                "snippet": snippet,
            }
        )

    return {
        "results": top,
        "count": len(top),
        "note": "Keyword search over cached CICS pages",
    }


# ---------- Approved Alternate Courses (Structured) ----------

APPROVED_ALTERNATE_URL = (
    "https://www.cics.umass.edu/academics/academic-policies/graduate-programs-policies/approved-alternate-courses"
)


def _html_path_for_url(data_dir: Path | str, url: str, raw_subdir: str = "cics_pages") -> Path:
    slug = _slugify_url(url)
    return Path(data_dir) / raw_subdir / f"{slug}.html"


def _ensure_html_cached(url: str, data_dir: Path | str = "data") -> str:
    """
    Ensure the raw HTML for the given URL is cached. Returns HTML string.
    """
    path = _html_path_for_url(data_dir, url)
    if not path.exists():
        # Refresh only this URL to write its HTML
        refresh_cics_pages(urls=[url], data_dir=data_dir)
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        # As a fallback, fetch directly and write
        with _create_client() as client:
            resp = client.get(url)
            resp.raise_for_status()
            html = resp.text
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(html, encoding="utf-8")
            return html


def _extract_course_like_lines(soup: BeautifulSoup) -> List[str]:
    """
    Heuristically extract course-like lines from lists and tables.
    """
    lines: List[str] = []

    # From list items
    for li in soup.find_all("li"):
        txt = re.sub(r"\s+", " ", li.get_text(" ", strip=True))
        if txt:
            lines.append(txt)

    # From tables (each row as a line)
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            cells = [re.sub(r"\s+", " ", td.get_text(" ", strip=True)) for td in tr.find_all(["td", "th"])]
            row_txt = " | ".join([c for c in cells if c])
            if row_txt:
                lines.append(row_txt)

    # De-duplicate while preserving order
    seen = set()
    uniq: List[str] = []
    for t in lines:
        if t not in seen:
            uniq.append(t)
            seen.add(t)
    return uniq


def _parse_approved_alternate_courses_html(html: str) -> List[Dict]:
    """
    Parse HTML content of the 'Approved Alternate Courses' page into structured entries.
    Each entry contains a detected course code (if any) and the full line for safety.
    """
    soup = BeautifulSoup(html, "lxml")

    # Optional: limit to a main content container if present
    main = soup.find(attrs={"id": re.compile(r"(content|main)", re.I)}) or soup

    lines = _extract_course_like_lines(main)

    course_pattern = re.compile(r"\b([A-Z]{2,})\s?(\d{2,3}[A-Z]?)\b")
    results: List[Dict] = []
    for line in lines:
        m = course_pattern.search(line)
        entry: Dict[str, Optional[str]] = {
            "department": None,
            "course_number": None,
            "course_code": None,
            "title_or_notes": None,
            "raw": line,
        }
        if m:
            dept = m.group(1)
            num = m.group(2)
            entry["department"] = dept
            entry["course_number"] = num
            entry["course_code"] = f"{dept} {num}"
            # Try to split the line around the code to get a title/notes
            parts = re.split(course_pattern, line, maxsplit=1)
            if parts and len(parts) >= 3:
                tail = parts[-1].strip(" -:|")
                entry["title_or_notes"] = tail if tail else None
        else:
            # Not strictly code-like, but include as context (policy notes, sections)
            entry["title_or_notes"] = line
        results.append(entry)  # Keep liberal capture; filtering happens later

    # Remove obvious duplicates by course_code + title_or_notes
    dedup: List[Dict] = []
    seen_keys = set()
    for r in results:
        key = (r.get("course_code"), r.get("title_or_notes") or r.get("raw"))
        if key not in seen_keys:
            dedup.append(r)
            seen_keys.add(key)

    return dedup


def get_approved_alternate_courses_cached(
    data_dir: Path | str = "data",
    force: bool = False,
) -> Dict:
    """
    Return structured list of approved alternate courses parsed from the cached HTML.
    When force=True, re-fetches the HTML first.
    """
    base_dir = Path(data_dir)
    out_path = base_dir / "cics_approved_alternate_courses.json"
    meta_path = base_dir / "cics_approved_alternate_courses.meta.json"

    if force:
        html = _ensure_html_cached(APPROVED_ALTERNATE_URL, data_dir=data_dir)
        parsed = _parse_approved_alternate_courses_html(html)
        out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        meta_path.write_text(
            json.dumps({"last_updated_ts": time.time(), "source_url": APPROVED_ALTERNATE_URL}, indent=2),
            encoding="utf-8",
        )
        return {"source_url": APPROVED_ALTERNATE_URL, "results": parsed, "count": len(parsed)}

    # Try cached
    try:
        if out_path.exists() and meta_path.exists():
            data = json.loads(out_path.read_text(encoding="utf-8"))
            return {"source_url": APPROVED_ALTERNATE_URL, "results": data, "count": len(data)}
    except Exception:
        pass

    # Ensure HTML exists, then parse
    html = _ensure_html_cached(APPROVED_ALTERNATE_URL, data_dir=data_dir)
    parsed = _parse_approved_alternate_courses_html(html)
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(
        json.dumps({"last_updated_ts": time.time(), "source_url": APPROVED_ALTERNATE_URL}, indent=2),
        encoding="utf-8",
    )
    return {"source_url": APPROVED_ALTERNATE_URL, "results": parsed, "count": len(parsed)}


# ---------- Additional Structured Extractors (FAQs, Research Areas, Contacts, Courses Index) ----------

FAQ_URL = "https://www.cics.umass.edu/advising/ms-program-advising/ms-advising-faqs"
COURSES_URL = "https://www.cics.umass.edu/academics/courses"
RESEARCH_AREAS_URL = "https://www.cics.umass.edu/research/research-areas?page=0"
CONTACT_URL = "https://www.cics.umass.edu/about/contact-us"


def _parse_faqs_html(html: str) -> List[Dict[str, str]]:
    """
    Extract question/answer pairs from the MS Advising FAQs page.
    Heuristic: treat headings and bold questions ending with '?' as questions,
    accumulate following paragraphs/lists until the next question.
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.find(attrs={"id": re.compile(r"(content|main)", re.I)}) or soup

    # Candidates for question blocks
    question_nodes = []
    for tag in main.find_all(["h2", "h3", "strong", "p", "li"]):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        if text.endswith("?"):
            question_nodes.append(tag)

    # Fallback: find bold within paragraphs that end with '?'
    if not question_nodes:
        for strong in main.find_all("strong"):
            t = strong.get_text(" ", strip=True)
            if t.endswith("?"):
                question_nodes.append(strong)

    faqs: List[Dict[str, str]] = []
    seen_questions = set()

    def is_question_like(node) -> bool:
        t = (node.get_text(" ", strip=True) if node else "").strip()
        return bool(t and t.endswith("?"))

    for qnode in question_nodes:
        qtext = qnode.get_text(" ", strip=True)
        if not qtext or qtext in seen_questions:
            continue
        # Gather siblings until next question-like node or section break
        answer_parts: List[str] = []
        ptr = qnode
        # Walk next siblings within the same parent
        while True:
            ptr = ptr.find_next_sibling()
            if ptr is None:
                break
            if ptr.name in ["h2", "h3"] and is_question_like(ptr):
                break
            if ptr.name in ["strong", "p", "li"] and is_question_like(ptr):
                break
            # Collect text content
            txt = ptr.get_text(" ", strip=True)
            if txt:
                answer_parts.append(txt)
            # Stop if we hit a large nav/aside/footer block
            if ptr.name in ["footer", "nav", "aside"]:
                break
        answer = " ".join(answer_parts).strip()
        if answer:
            faqs.append({"question": qtext, "answer": answer})
            seen_questions.add(qtext)

    # Deduplicate and keep stable order
    uniq: List[Dict[str, str]] = []
    seen = set()
    for item in faqs:
        key = (item["question"], item["answer"])
        if key not in seen:
            uniq.append(item)
            seen.add(key)
    return uniq


def get_cics_faqs_cached(data_dir: Path | str = "data", force: bool = False) -> Dict:
    base_dir = Path(data_dir)
    out_path = base_dir / "cics_faqs.json"
    meta_path = base_dir / "cics_faqs.meta.json"

    if force:
        html = _ensure_html_cached(FAQ_URL, data_dir=data_dir)
        parsed = _parse_faqs_html(html)
        out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": FAQ_URL}, indent=2), encoding="utf-8")
        return {"source_url": FAQ_URL, "results": parsed, "count": len(parsed)}

    try:
        if out_path.exists():
            data = json.loads(out_path.read_text(encoding="utf-8"))
            return {"source_url": FAQ_URL, "results": data, "count": len(data)}
    except Exception:
        pass

    html = _ensure_html_cached(FAQ_URL, data_dir=data_dir)
    parsed = _parse_faqs_html(html)
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": FAQ_URL}, indent=2), encoding="utf-8")
    return {"source_url": FAQ_URL, "results": parsed, "count": len(parsed)}


def _parse_research_areas_html(html: str) -> List[Dict[str, str]]:
    """
    Extract research area titles and short descriptions from the research areas page.
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.find(attrs={"id": re.compile(r"(content|main)", re.I)}) or soup

    areas: List[Dict[str, str]] = []
    # Heuristic: find blocks with headers and a paragraph following
    for block in main.find_all(["div", "article", "section"]):
        header = block.find(["h2", "h3"])
        if not header:
            continue
        title = header.get_text(" ", strip=True)
        if not title or len(title) > 120:
            continue
        para = block.find("p")
        desc = para.get_text(" ", strip=True) if para else ""
        if title and desc:
            areas.append({"area": title, "description": desc})

    # Fallback: scan headings sequentially and pick next paragraph
    if not areas:
        for h in main.find_all(["h2", "h3"]):
            title = h.get_text(" ", strip=True)
            if not title:
                continue
            nxt = h.find_next_sibling("p")
            if nxt:
                desc = nxt.get_text(" ", strip=True)
                if desc:
                    areas.append({"area": title, "description": desc})

    # Dedup by area
    uniq: List[Dict[str, str]] = []
    seen = set()
    for a in areas:
        k = a["area"]
        if k not in seen:
            uniq.append(a)
            seen.add(k)
    return uniq


def get_cics_research_areas_cached(data_dir: Path | str = "data", force: bool = False) -> Dict:
    base_dir = Path(data_dir)
    out_path = base_dir / "cics_research_areas.json"
    meta_path = base_dir / "cics_research_areas.meta.json"

    if force:
        html = _ensure_html_cached(RESEARCH_AREAS_URL, data_dir=data_dir)
        parsed = _parse_research_areas_html(html)
        out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": RESEARCH_AREAS_URL}, indent=2), encoding="utf-8")
        return {"source_url": RESEARCH_AREAS_URL, "results": parsed, "count": len(parsed)}

    try:
        if out_path.exists():
            data = json.loads(out_path.read_text(encoding="utf-8"))
            return {"source_url": RESEARCH_AREAS_URL, "results": data, "count": len(data)}
    except Exception:
        pass

    html = _ensure_html_cached(RESEARCH_AREAS_URL, data_dir=data_dir)
    parsed = _parse_research_areas_html(html)
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": RESEARCH_AREAS_URL}, indent=2), encoding="utf-8")
    return {"source_url": RESEARCH_AREAS_URL, "results": parsed, "count": len(parsed)}


def _parse_contact_us_html(html: str) -> Dict[str, Any]:
    """
    Extract key contacts: address, main phone, dean contact, frequently contacted offices with emails.
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.find(attrs={"id": re.compile(r"(content|main)", re.I)}) or soup
    text = re.sub(r"\s+", " ", main.get_text(" ", strip=True))

    # Address block heuristic: look for 'Computer Science Building' line
    address = None
    addr_match = re.search(r"(Computer Science Building.*?Amherst.*?\d{5}(?:-\d{4})?)", text, flags=re.I)
    if addr_match:
        address = addr_match.group(1).strip()

    # Phone numbers
    phones = re.findall(r"\(\d{3}\)\s?\d{3}-\d{4}", text)
    main_phone = phones[0] if phones else None

    # Emails (normalized)
    emails = re.findall(r"[A-Za-z0-9._%+-]+\s*\[\s*at\s*\]\s*[A-Za-z0-9.-]+\s*\[\s*dot\s*\]\s*[A-Za-z]{2,}", text)

    # Frequently contacted offices: simple extraction of label + email in proximity
    offices: List[Dict[str, Optional[str]]] = []
    office_candidates = [
        "Undergraduate Advising",
        "Career Development",
        "Computing Facilities",
        "Marketing & Communications",
        "Dean's Office",
        "Graduate Program Admissions",
        "Undergraduate Program Admissions",
    ]
    for label in office_candidates:
        # Find a window around the label
        m = re.search(re.escape(label) + r".{0,120}", text, flags=re.I)
        email_norm = None
        if m:
            window = m.group(0)
            # Capture normalized 'name [at] domain [dot] tld'
            m2 = re.search(r"([A-Za-z0-9._%+-]+)\s*\[\s*at\s*\]\s*([A-Za-z0-9.-]+)\s*\[\s*dot\s*\]\s*([A-Za-z]{2,})", window)
            if m2:
                email_norm = f"{m2.group(1)}@{m2.group(2)}.{m2.group(3)}"
        offices.append({"office": label, "email": email_norm})

    # Dean line
    dean = None
    dm = re.search(r"Dean\s+([A-Za-z .'-]+)", text)
    if dm:
        dean = dm.group(1).strip()

    return {
        "address": address,
        "main_phone": main_phone,
        "emails_observed": emails,
        "offices": offices,
        "dean": dean,
    }


def get_cics_contacts_cached(data_dir: Path | str = "data", force: bool = False) -> Dict:
    base_dir = Path(data_dir)
    out_path = base_dir / "cics_contacts.json"
    meta_path = base_dir / "cics_contacts.meta.json"

    if force:
        html = _ensure_html_cached(CONTACT_URL, data_dir=data_dir)
        parsed = _parse_contact_us_html(html)
        out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": CONTACT_URL}, indent=2), encoding="utf-8")
        return {"source_url": CONTACT_URL, "results": parsed, "count": (len(parsed.get("offices") or []) if isinstance(parsed, dict) else 0)}

    try:
        if out_path.exists():
            data = json.loads(out_path.read_text(encoding="utf-8"))
            return {"source_url": CONTACT_URL, "results": data, "count": (len(data.get("offices") or []) if isinstance(data, dict) else 0)}
    except Exception:
        pass

    html = _ensure_html_cached(CONTACT_URL, data_dir=data_dir)
    parsed = _parse_contact_us_html(html)
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": CONTACT_URL}, indent=2), encoding="utf-8")
    return {"source_url": CONTACT_URL, "results": parsed, "count": (len(parsed.get("offices") or []) if isinstance(parsed, dict) else 0)}


def _parse_courses_index_html(html: str) -> Dict[str, List[Dict[str, str]]]:
    """
    Extract a navigable index from the Courses page:
      - key sections and their links/titles (Schedule, Descriptions, Plan, Overrides, etc.)
    """
    soup = BeautifulSoup(html, "lxml")
    main = soup.find(attrs={"id": re.compile(r"(content|main)", re.I)}) or soup
    sections: Dict[str, List[Dict[str, str]]] = {}

    for a in main.find_all("a", href=True):
        text = a.get_text(" ", strip=True)
        href = a["href"]
        if not text or not href:
            continue
        label = text.lower()
        if any(key in label for key in ["course schedule", "course descriptions", "offering plan", "override", "prereq", "catalog", "registration", "university+"]):
            cat = "links"
            sections.setdefault(cat, []).append({"text": text, "href": href})

    # Keep unique by href+text
    for k, arr in list(sections.items()):
        uniq = []
        seen = set()
        for it in arr:
            key = (it["text"], it["href"])
            if key not in seen:
                uniq.append(it)
                seen.add(key)
        sections[k] = uniq

    return sections


def get_cics_courses_index_cached(data_dir: Path | str = "data", force: bool = False) -> Dict:
    base_dir = Path(data_dir)
    out_path = base_dir / "cics_courses_index.json"
    meta_path = base_dir / "cics_courses_index.meta.json"

    if force:
        html = _ensure_html_cached(COURSES_URL, data_dir=data_dir)
        parsed = _parse_courses_index_html(html)
        out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
        meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": COURSES_URL}, indent=2), encoding="utf-8")
        return {"source_url": COURSES_URL, "results": parsed, "count": sum(len(v) for v in parsed.values())}

    try:
        if out_path.exists():
            data = json.loads(out_path.read_text(encoding="utf-8"))
            return {"source_url": COURSES_URL, "results": data, "count": sum(len(v) for v in data.values())}
    except Exception:
        pass

    html = _ensure_html_cached(COURSES_URL, data_dir=data_dir)
    parsed = _parse_courses_index_html(html)
    out_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(json.dumps({"last_updated_ts": time.time(), "source_url": COURSES_URL}, indent=2), encoding="utf-8")
    return {"source_url": COURSES_URL, "results": parsed, "count": sum(len(v) for v in parsed.values())}

