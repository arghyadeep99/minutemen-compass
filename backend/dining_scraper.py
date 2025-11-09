"""
Dining scraper: crawl the configured UMass Dining Locations & Menus page
and follow venue links to extract structured information.
"""
from __future__ import annotations

import re
import json
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Set
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


DEFAULT_BASE_URL = "https://umassdining.com/locations-menus"
USER_AGENT = "UMassCampusAgent/1.0 (+https://example.edu) Python-httpx"


@dataclass
class DiningVenue:
    name: str
    url: str
    description: Optional[str] = None
    hours_text: Optional[str] = None
    dietary_options: Optional[List[str]] = None
    location_text: Optional[str] = None
    category: Optional[str] = None  # e.g., "Dining Commons", "Cafe", etc.

@dataclass
class DiningMenu:
    hall: str
    url: str
    date_text: Optional[str]
    meals: Dict[str, Dict[str, List[str]]]  # meal -> { category -> [items] }


def _create_client() -> httpx.Client:
    return httpx.Client(
        headers={"User-Agent": USER_AGENT},
        timeout=httpx.Timeout(15.0, connect=10.0),
        follow_redirects=True,
    )


def _is_same_site(parent_url: str, candidate_url: str) -> bool:
    p = urlparse(parent_url)
    c = urlparse(candidate_url)
    return (p.scheme, p.netloc) == (c.scheme, c.netloc)


def _extract_text(el) -> str:
    text = el.get_text(separator=" ", strip=True) if el else ""
    # Collapse excessive whitespace
    return re.sub(r"\s+", " ", text).strip()


def _extract_dietary_options(text: str) -> List[str]:
    options: Set[str] = set()
    lower = text.lower()
    if "vegan" in lower:
        options.add("vegan")
    if "vegetarian" in lower:
        options.add("vegetarian")
    if "halal" in lower:
        options.add("halal")
    if "gluten" in lower:
        # Could be "gluten free" or "gluten-free"
        options.add("gluten-free")
    if "kosher" in lower:
        options.add("kosher")
    return sorted(options)


def _extract_hours_text(soup: BeautifulSoup) -> Optional[str]:
    # Heuristic: find sections/headings containing 'hour'
    candidates = []
    for tag in soup.find_all(text=re.compile(r"hours?", re.I)):
        # Include some surrounding context
        section = tag.parent
        if section:
            # Grab nearby text
            context = _extract_text(section)
            if len(context) > 15:
                candidates.append(context)
    # Fallback to any time-pattern heavy blocks
    if not candidates:
        time_like = soup.find_all(text=re.compile(r"\b\d{1,2}:\d{2}\b"))
        if time_like:
            # Try to get a reasonable chunk from first occurrence
            par = time_like[0].parent
            if par:
                return _extract_text(par)[:600]
    if not candidates:
        return None
    # Return the most descriptive candidate
    return sorted(candidates, key=len, reverse=True)[0][:800]


def _guess_category(text: str) -> Optional[str]:
    t = text.lower()
    if any(k in t for k in ["dining commons", "dc"]):
        return "Dining Commons"
    if any(k in t for k in ["cafe", "espresso", "coffee"]):
        return "Cafe"
    if any(k in t for k in ["food truck"]):
        return "Food Truck"
    if any(k in t for k in ["grab", "grab ‘n go", "grab 'n go"]):
        return "Grab 'N Go"
    if any(k in t for k in ["campus center", "retail"]):
        return "Retail"
    return None


def _extract_description(soup: BeautifulSoup) -> Optional[str]:
    # Prefer meta description
    meta = soup.find("meta", attrs={"name": "description"})
    if meta and meta.get("content"):
        return meta["content"].strip()[:500]
    # Fallback: first meaningful paragraph
    for p in soup.find_all("p"):
        txt = _extract_text(p)
        if len(txt) >= 40:
            return txt[:500]
    return None


def _collect_links_from_main(soup: BeautifulSoup, base_url: str) -> List[str]:
    links: List[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        abs_url = urljoin(base_url, href)
        # Keep within the same site
        if not _is_same_site(base_url, abs_url):
            continue
        # Heuristic: we only want "location/venue" pages; keep likely relevant paths
        if any(k in abs_url.lower() for k in [
            "locations", "menus", "dining", "berkshire", "worcester", "franklin",
            "hampshire", "cafe", "campus-center", "grab", "retail", "commonwealth",
            "student-business", "food-truck"
        ]):
            links.append(abs_url)
    # Dedupe while preserving order
    seen: Set[str] = set()
    uniq = []
    for url in links:
        if url not in seen:
            uniq.append(url)
            seen.add(url)
    return uniq


def scrape_dining(base_url: str = DEFAULT_BASE_URL, max_venues: int = 60) -> List[DiningVenue]:
    venues: List[DiningVenue] = []
    with _create_client() as client:
        main_resp = client.get(base_url)
        main_resp.raise_for_status()
        main_soup = BeautifulSoup(main_resp.text, "lxml")

        venue_links = _collect_links_from_main(main_soup, base_url)
        # Also include the base page itself for overview content
        candidate_pages = [base_url] + venue_links
        candidate_pages = candidate_pages[: max_venues + 1]

        for url in candidate_pages:
            try:
                resp = client.get(url)
                resp.raise_for_status()
            except Exception:
                continue
            soup = BeautifulSoup(resp.text, "lxml")

            # Title / Name
            title_tag = soup.find("h1") or soup.find("title")
            name = _extract_text(title_tag) if title_tag else url
            if not name:
                name = url

            page_text = _extract_text(soup)
            description = _extract_description(soup)
            hours_text = _extract_hours_text(soup)
            dietary_options = _extract_dietary_options(page_text)
            category = _guess_category(page_text)

            # Some light normalization: if the page appears to be the root page, skip as a venue
            if url == base_url and "locations" in name.lower() and "menus" in name.lower():
                # Keep only as informational, not a venue entry
                continue

            venues.append(
                DiningVenue(
                    name=name,
                    url=url,
                    description=description,
                    hours_text=hours_text,
                    dietary_options=dietary_options or None,
                    location_text=None,
                    category=category,
                )
            )
    return venues


def get_dining_data_cached(
    base_url: str = DEFAULT_BASE_URL,
    cache_hours: int = 6,
    data_dir: Path | str = "data",
) -> List[Dict]:
    """
    Return cached dining data if recent; otherwise scrape and refresh cache.
    """
    data_path = Path(data_dir) / "dining.json"
    meta_path = Path(data_dir) / "dining.meta.json"

    now = time.time()
    try:
        if data_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            last_ts = float(meta.get("last_updated_ts", 0))
            cached_count = int(meta.get("count", 0))
            # Only use cache if it's recent AND non-empty
            if now - last_ts <= cache_hours * 3600 and cached_count > 0:
                return json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        # Ignore cache errors and proceed to scrape
        pass

    venues = scrape_dining(base_url=base_url)
    data = [asdict(v) for v in venues]

    # Persist cache
    Path(data_dir).mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {"last_updated_ts": now, "base_url": base_url, "count": len(data)}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    return data


def _collect_menu_links_from_main(soup: BeautifulSoup, base_url: str) -> Dict[str, str]:
    """
    Find menu page links like /locations-menus/<hall>/menu and map to hall names.
    The main page typically has links to /locations-menus/<hall>, so we construct
    the menu URL by appending /menu.
    """
    hall_to_url: Dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = urljoin(base_url, href)
        if not _is_same_site(base_url, abs_url):
            continue
        path = urlparse(abs_url).path.lower()
        
        # Look for dining hall links like /locations-menus/worcester
        if "/locations-menus/" in path:
            # Skip the base locations-menus page itself
            parts = path.rstrip("/").split("/")
            if len(parts) >= 3:  # Must have at least /locations-menus/hall
                hall_name = _extract_text(a)
                if hall_name:
                    # Construct menu URL by appending /menu if not already present
                    menu_url = abs_url.rstrip("/") + ("/menu" if not abs_url.endswith("/menu") else "")
                    hall_to_url[hall_name] = menu_url
    return hall_to_url


_MEAL_NAMES = [
    "Breakfast",
    "Brunch",
    "Lunch",
    "Dinner",
    "Late Night",
]


def _is_meal_header(text: str) -> Optional[str]:
    """
    Check if a header text represents a meal name (Breakfast, Lunch, Dinner, etc.).
    Only matches exact meal names to avoid matching category names like "Breakfast Entrees".
    """
    t = (text or "").strip()
    for name in _MEAL_NAMES:
        # Use exact match (case-insensitive) to avoid matching "Breakfast Entrees" as "Breakfast"
        if t.lower() == name.lower():
            return name
    return None


def _parse_menu_page(soup: BeautifulSoup) -> Tuple[Optional[str], Dict[str, Dict[str, List[str]]]]:
    """
    Parse a UMass menu page into: (date_text, meals -> categories -> items)
    Heuristic approach based on headings and following lists.
    """
    # Date line usually like "Menu For Sat November 08, 2025"
    date_text = None
    for tag in soup.find_all(text=re.compile(r"\bMenu\s+For\b", re.I)):
        date_text = _extract_text(tag.parent)
        break

    meals: Dict[str, Dict[str, List[str]]] = {}
    current_meal: Optional[str] = None
    current_category: Optional[str] = None

    # Consider h1-h4 as structural boundaries
    headers = soup.find_all(re.compile(r"^h[1-4]$"))
    for i, hdr in enumerate(headers):
        hdr_text = _extract_text(hdr)
        meal_name = _is_meal_header(hdr_text)
        if meal_name:
            current_meal = meal_name
            meals.setdefault(current_meal, {})
            current_category = None
            continue

        if current_meal:
            # Treat any non-meal header as a category within current meal
            current_category = hdr_text
            if not current_category:
                continue
            meals[current_meal].setdefault(current_category, [])

            # Collect items until the next header
            items: List[str] = []
            # Explore siblings until reaching a header or None
            for sib in hdr.next_siblings:
                if getattr(sib, "name", None) and re.match(r"^h[1-4]$", sib.name or ""):
                    break
                # Skip text nodes and non-element siblings
                if not getattr(sib, "name", None):
                    continue
                
                # Check if sibling is directly a <li> element (common in UMass dining pages)
                if sib.name == "li":
                    txt = _extract_text(sib)
                    if txt:
                        items.append(txt)
                # Look for list items nested in <ul> containers
                elif sib.name == "ul":
                    for li in sib.find_all("li"):
                        txt = _extract_text(li)
                        if txt:
                            items.append(txt)
                # Look for <ul> nested within other containers (e.g., <div>)
                else:
                    for ul in sib.find_all("ul"):
                        for li in ul.find_all("li"):
                            txt = _extract_text(li)
                            if txt:
                                items.append(txt)
                
                # Also look for direct paragraphs that contain item-like lines
                if sib.name == "p":
                    txt = _extract_text(sib)
                    if txt and len(txt) > 2 and not txt.lower().startswith("upcoming menus"):
                        # Paragraphs can contain many words; keep shorter lines as items
                        if len(txt) <= 120:
                            items.append(txt)
            if items:
                meals[current_meal][current_category].extend(items)

    # Cleanup: remove empty categories/meals
    meals = {
        meal: {cat: items for cat, items in cats.items() if items}
        for meal, cats in meals.items()
        if any(items for items in cats.values())
    }

    return date_text, meals


def scrape_menus(base_url: str = DEFAULT_BASE_URL, max_halls: int = 20) -> List[DiningMenu]:
    """
    Scrape menu pages for multiple dining halls starting from the base locations page.
    """
    menus: List[DiningMenu] = []
    with _create_client() as client:
        main_resp = client.get(base_url)
        main_resp.raise_for_status()
        main_soup = BeautifulSoup(main_resp.text, "lxml")

        hall_links = _collect_menu_links_from_main(main_soup, base_url)
        # Keep deterministic order
        items = list(hall_links.items())[:max_halls]

        for hall_label, menu_url in items:
            try:
                resp = client.get(menu_url)
                resp.raise_for_status()
            except Exception:
                continue
            soup = BeautifulSoup(resp.text, "lxml")

            # Determine hall name: prefer page H1 text if available
            h1 = soup.find("h1")
            hall_name = _extract_text(h1) if h1 else hall_label

            date_text, meals = _parse_menu_page(soup)
            if meals:
                menus.append(
                    DiningMenu(
                        hall=hall_name,
                        url=menu_url,
                        date_text=date_text,
                        meals=meals,
                    )
                )
    return menus


def get_dining_menus_cached(
    base_url: str = DEFAULT_BASE_URL,
    cache_hours: int = 3,
    data_dir: Path | str = "data",
) -> List[Dict]:
    """
    Return cached dining menus if recent; otherwise scrape and refresh cache.
    """
    data_path = Path(data_dir) / "dining_menus.json"
    meta_path = Path(data_dir) / "dining_menus.meta.json"

    now = time.time()
    try:
        if data_path.exists() and meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            last_ts = float(meta.get("last_updated_ts", 0))
            cached_count = int(meta.get("count", 0))
            # Only use cache if it's recent AND non-empty
            if now - last_ts <= cache_hours * 3600 and cached_count > 0:
                return json.loads(data_path.read_text(encoding="utf-8"))
    except Exception:
        pass

    scraped = scrape_menus(base_url=base_url)
    data = [asdict(m) for m in scraped]

    Path(data_dir).mkdir(parents=True, exist_ok=True)
    data_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    meta_path.write_text(
        json.dumps(
            {"last_updated_ts": now, "base_url": base_url, "count": len(data)},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return data

