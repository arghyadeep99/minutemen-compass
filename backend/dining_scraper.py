"""
Web scraper for UMass Dining menus
Fetches live menu data from umassdining.com
"""
from __future__ import annotations

import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import re
from pathlib import Path


class DiningScraper:
    """Scraper for UMass Dining menu data"""
    
    BASE_URL = "https://umassdining.com"
    
    # Dining hall URLs
    DINING_HALLS = {
        "berkshire": "https://umassdining.com/locations-menus/berkshire/menu",
        "worcester": "https://umassdining.com/locations-menus/worcester/menu",
        "hampshire": "https://umassdining.com/locations-menus/hampshire/menu",
        "franklin": "https://umassdining.com/locations-menus/franklin/menu",
    }
    
    # Grab 'N Go URLs
    GRAB_N_GO = {
        "berkshire": "https://umassdining.com/menu/berkshire-grab-n-go-menu",
        "worcester": "https://umassdining.com/menu/worcester-grab-n-go",
        "hampshire": "https://umassdining.com/menu/hampshire-grab-n-go",
        "franklin": "https://umassdining.com/menu/franklin-grab-n-go",
    }
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the scraper with optional cache directory"""
        self.cache_dir = cache_dir or Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def _get_cache_path(self, location: str, meal_type: str) -> Path:
        """Get cache file path for a location and meal type"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.cache_dir / f"{location}_{meal_type}_{today}.json"
    
    def _is_cache_valid(self, cache_path: Path, max_age_hours: int = 2) -> bool:
        """Check if cache file is still valid"""
        if not cache_path.exists():
            return False
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - file_time
        return age < timedelta(hours=max_age_hours)
    
    def _load_cache(self, cache_path: Path) -> Optional[Dict[str, Any]]:
        """Load data from cache"""
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _save_cache(self, cache_path: Path, data: Dict[str, Any]):
        """Save data to cache"""
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")
    
    def _fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a webpage"""
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def _extract_dietary_info(self, item_text: str) -> List[str]:
        """Extract dietary information from menu item text"""
        dietary = []
        text_lower = item_text.lower()
        
        # Check for dietary indicators (these might be in icons/legends on the page)
        # Common patterns from UMass Dining
        if any(word in text_lower for word in ['vegetarian', 'veg']):
            dietary.append('vegetarian')
        if any(word in text_lower for word in ['vegan', 'plant based', 'plant-based']):
            dietary.append('vegan')
        if 'halal' in text_lower:
            dietary.append('halal')
        if any(word in text_lower for word in ['gluten-free', 'gluten free', 'gf']):
            dietary.append('gluten-free')
        
        return dietary
    
    def _parse_dining_hall_menu(self, soup: BeautifulSoup, location: str) -> Dict[str, Any]:
        """Parse dining hall menu page"""
        menu_data = {
            "location": location.capitalize(),
            "name": f"{location.capitalize()} Commons",
            "type": "Dining Hall",
            "meals": {
                "breakfast": [],
                "lunch": [],
                "dinner": [],
                "late_night": []
            },
            "dietary_options": [],
            "hours": {
                "open": "07:00",
                "close": "21:00"
            },
            "late_night": True
        }
        
        all_dietary = set()
        
        # Find the menu container
        menu_div = soup.find('div', id='dining_menu')
        if not menu_div:
            return menu_data
        
        # Meal period mappings: h2 text -> meal key, and corresponding div class
        meal_periods = {
            'Lunch': ('lunch', 'lunch_fp'),
            'Dinner': ('dinner', 'dinner_fp'),
            'Late Night': ('late_night', 'latenight_fp'),  # Note: class is 'latenight_fp' not 'late_night_fp'
        }
        
        # Process Lunch, Dinner, Late Night
        for meal_h2_text, (meal_key, div_class) in meal_periods.items():
            meal_h2 = None
            for h2 in menu_div.find_all('h2'):
                if h2.get_text().strip() == meal_h2_text:
                    meal_h2 = h2
                    break
            
            if meal_h2:
                # Find the div with the corresponding class
                meal_div = meal_h2.find_next_sibling('div', class_=div_class)
                if meal_div:
                    # Special handling for Lunch: it contains breakfast items
                    if meal_key == 'lunch':
                        # Parse breakfast stations separately
                        self._parse_meal_section(meal_div, 'breakfast', menu_data, all_dietary, 
                                                station_prefix='Breakfast')
                        # Then parse lunch stations
                        self._parse_meal_section(meal_div, 'lunch', menu_data, all_dietary,
                                                exclude_station_prefix='Breakfast')
                    else:
                        self._parse_meal_section(meal_div, meal_key, menu_data, all_dietary)
        
        menu_data["dietary_options"] = list(all_dietary)
        return menu_data
    
    def _parse_meal_section(self, meal_div: BeautifulSoup, meal_key: str, 
                           menu_data: Dict[str, Any], all_dietary: set,
                           station_prefix: Optional[str] = None,
                           exclude_station_prefix: Optional[str] = None):
        """Parse a meal section div (lunch_fp, dinner_fp, etc.)"""
        # Find all h2 tags (station names) within this div
        station_h2s = meal_div.find_all('h2')
        
        for station_h2 in station_h2s:
            station_name = station_h2.get_text().strip()
            
            # Skip if it's a meal period heading
            if station_name in ['Breakfast', 'Lunch', 'Dinner', 'Late Night']:
                continue
            
            # Filter by station prefix if specified
            if station_prefix and not station_name.startswith(station_prefix):
                continue
            if exclude_station_prefix and station_name.startswith(exclude_station_prefix):
                continue
            
            # Get all <li> elements after this h2 until the next h2
            current = station_h2.find_next_sibling()
            while current:
                # Stop if we hit another h2
                if current.name == 'h2':
                    break
                
                # Process <li> elements
                if current.name == 'li':
                    item_text = current.get_text().strip()
                    if item_text and len(item_text) > 2:
                        # Extract dietary information from img tags
                        dietary = []
                        icons = current.find_all('img', alt=True)
                        for icon in icons:
                            alt_text = icon.get('alt', '').lower()
                            if 'vegetarian' in alt_text or 'veg' in alt_text:
                                dietary.append('vegetarian')
                            if 'vegan' in alt_text or 'plant' in alt_text:
                                dietary.append('vegan')
                            if 'halal' in alt_text:
                                dietary.append('halal')
                            if 'gluten' in alt_text:
                                dietary.append('gluten-free')
                        
                        # Also check text for dietary info
                        text_dietary = self._extract_dietary_info(item_text)
                        dietary.extend([d for d in text_dietary if d not in dietary])
                        
                        menu_data["meals"][meal_key].append({
                            "name": item_text,
                            "station": station_name,
                            "dietary": dietary
                        })
                        all_dietary.update(dietary)
                
                current = current.find_next_sibling()
    
    def _parse_grab_n_go_menu(self, soup: BeautifulSoup, location: str) -> Dict[str, Any]:
        """Parse Grab 'N Go menu page"""
        menu_data = {
            "location": location.capitalize(),
            "name": f"{location.capitalize()} Grab 'N Go",
            "type": "Grab 'N Go",
            "items": [],
            "dietary_options": [],
            "hours": {
                "open": "07:00",
                "close": "22:00"
            },
            "late_night": False
        }
        
        # Check if location is closed
        page_text = soup.get_text().lower()
        if 'closed' in page_text and 'this location is closed' in page_text:
            # Location is closed, return empty menu
            return menu_data
        
        # Find the menu container (same structure as dining halls)
        menu_div = soup.find('div', id='dining_menu')
        if not menu_div:
            return menu_data
        
        all_dietary = set()
        
        # Grab 'N Go might use the same structure as dining halls
        # Check for meal period divs (lunch_fp, dinner_fp, etc.)
        meal_divs = menu_div.find_all('div', class_=re.compile(r'(lunch|dinner|breakfast|late)', re.I))
        
        if meal_divs:
            # Same structure as dining halls - parse each meal period
            for meal_div in meal_divs:
                # Find station headings (h2) and items (li)
                station_h2s = meal_div.find_all('h2')
                for station_h2 in station_h2s:
                    station_name = station_h2.get_text().strip()
                    # Skip meal period headings
                    if station_name in ['Breakfast', 'Lunch', 'Dinner', 'Late Night']:
                        continue
                    
                    # Get all <li> elements after this h2 until the next h2
                    current = station_h2.find_next_sibling()
                    while current:
                        if current.name == 'h2':
                            break
                        
                        if current.name == 'li':
                            item_text = current.get_text().strip()
                            if item_text and len(item_text) > 2:
                                # Extract dietary information from img tags
                                dietary = []
                                icons = current.find_all('img', alt=True)
                                for icon in icons:
                                    alt_text = icon.get('alt', '').lower()
                                    if 'vegetarian' in alt_text or 'veg' in alt_text:
                                        dietary.append('vegetarian')
                                    if 'vegan' in alt_text or 'plant' in alt_text:
                                        dietary.append('vegan')
                                    if 'halal' in alt_text:
                                        dietary.append('halal')
                                    if 'gluten' in alt_text:
                                        dietary.append('gluten-free')
                                
                                # Also check text for dietary info
                                text_dietary = self._extract_dietary_info(item_text)
                                dietary.extend([d for d in text_dietary if d not in dietary])
                                
                                # Skip navigation items
                                skip_keywords = ['meal plan', 'locations', 'sustainability', 'nutrition', 
                                               'press', 'events', 'about', 'privacy', 'partner', 
                                               'late night', 'retail', 'food truck', 'faq', 'parents',
                                               'additional resources', 'contact', 'facebook', 'twitter',
                                               'linkedin', 'instagram', 'youtube', 'tiktok']
                                if any(keyword in item_text.lower() for keyword in skip_keywords):
                                    current = current.find_next_sibling()
                                    continue
                                
                                menu_data["items"].append({
                                    "name": item_text,
                                    "station": station_name,
                                    "dietary": dietary
                                })
                                all_dietary.update(dietary)
                        
                        current = current.find_next_sibling()
        else:
            # Different structure - look for lists directly in dining_menu
            # Find all lists that aren't navigation
            lists = menu_div.find_all(['ul', 'ol'])
            for ul in lists:
                # Skip navigation lists
                parent_classes = ' '.join([c for c in ul.parent.get('class', [])])
                if 'menu' in parent_classes.lower() and 'navigation' not in parent_classes.lower():
                    continue
                
                items = ul.find_all('li')
                for item in items:
                    item_text = item.get_text().strip()
                    if item_text and len(item_text) > 3:
                        # Skip navigation items
                        skip_keywords = ['meal plan', 'locations', 'sustainability', 'nutrition', 
                                       'press', 'events', 'about', 'privacy', 'partner', 
                                       'late night', 'retail', 'food truck', 'faq', 'parents',
                                       'additional resources', 'contact', 'facebook', 'twitter',
                                       'linkedin', 'instagram', 'youtube', 'tiktok', 'closed',
                                       'upcoming menus', 'legends', 'menu for']
                        if any(keyword in item_text.lower() for keyword in skip_keywords):
                            continue
                        
                        # Check if parent is navigation
                        parent = item.find_parent(['nav', 'ul', 'div'])
                        if parent:
                            parent_classes = ' '.join([c for c in parent.get('class', [])])
                            if 'menu' in parent_classes.lower() or 'nav' in parent_classes.lower():
                                continue
                        
                        dietary = self._extract_dietary_info(item_text)
                        # Extract from img tags if present
                        icons = item.find_all('img', alt=True)
                        for icon in icons:
                            alt_text = icon.get('alt', '').lower()
                            if 'vegetarian' in alt_text or 'veg' in alt_text:
                                dietary.append('vegetarian')
                            if 'vegan' in alt_text or 'plant' in alt_text:
                                dietary.append('vegan')
                            if 'halal' in alt_text:
                                dietary.append('halal')
                            if 'gluten' in alt_text:
                                dietary.append('gluten-free')
                        
                        menu_data["items"].append({
                            "name": item_text,
                            "dietary": list(set(dietary))
                        })
                        all_dietary.update(dietary)
        
        menu_data["dietary_options"] = list(all_dietary)
        return menu_data
    
    def get_dining_hall_menu(self, location: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get menu for a dining hall"""
        location_lower = location.lower()
        if location_lower not in self.DINING_HALLS:
            return None
        
        cache_path = self._get_cache_path(location_lower, "dining_hall")
        
        # Try cache first
        if use_cache:
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        # Fetch from web
        url = self.DINING_HALLS[location_lower]
        soup = self._fetch_page(url)
        if not soup:
            return None
        
        menu_data = self._parse_dining_hall_menu(soup, location_lower)
        
        # Save to cache
        if use_cache:
            self._save_cache(cache_path, menu_data)
        
        return menu_data
    
    def get_grab_n_go_menu(self, location: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """Get menu for Grab 'N Go"""
        location_lower = location.lower()
        if location_lower not in self.GRAB_N_GO:
            return None
        
        cache_path = self._get_cache_path(location_lower, "grab_n_go")
        
        # Try cache first
        if use_cache:
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        # Fetch from web
        url = self.GRAB_N_GO[location_lower]
        soup = self._fetch_page(url)
        if not soup:
            return None
        
        menu_data = self._parse_grab_n_go_menu(soup, location_lower)
        
        # Save to cache
        if use_cache:
            self._save_cache(cache_path, menu_data)
        
        return menu_data
    
    def get_all_dining_options(self, meal_period: Optional[str] = None, 
                              dietary_pref: Optional[str] = None,
                              dining_type: Optional[str] = None,
                              location: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all dining options with optional filtering"""
        results = []
        
        # Determine which types to include
        include_dining_halls = True
        include_grab_n_go = True
        
        if dining_type:
            dining_type_lower = dining_type.lower()
            if "grab" in dining_type_lower or "n go" in dining_type_lower:
                include_dining_halls = False
            elif "dining hall" in dining_type_lower:
                include_grab_n_go = False
        
        # Determine which locations to include
        locations_to_check = None
        if location:
            location_lower = location.lower()
            # Map location names to our internal keys
            location_map = {
                'franklin': 'franklin',
                'berkshire': 'berkshire',
                'worcester': 'worcester',
                'hampshire': 'hampshire',
            }
            # Find matching location key
            matching_key = None
            for key, value in location_map.items():
                if location_lower in key or key in location_lower:
                    matching_key = key
                    break
            
            if matching_key:
                locations_to_check = [matching_key]
            else:
                # If no exact match, check all locations and filter later
                locations_to_check = None
        
        # Get all dining halls
        if include_dining_halls:
            locations = locations_to_check if locations_to_check else self.DINING_HALLS.keys()
            for loc in locations:
                if loc not in self.DINING_HALLS:
                    continue
                menu = self.get_dining_hall_menu(loc)
                if menu:
                    # Filter by meal period
                    if meal_period:
                        meal_period_lower = meal_period.lower()
                        if meal_period_lower in menu.get("meals", {}):
                            menu["current_meal_items"] = menu["meals"][meal_period_lower]
                        else:
                            continue
                    
                    # Filter by dietary preference
                    if dietary_pref and dietary_pref.lower() != "none":
                        dietary_lower = dietary_pref.lower()
                        if dietary_lower not in [d.lower() for d in menu.get("dietary_options", [])]:
                            continue
                    
                    results.append(menu)
        
        # Get all Grab 'N Go locations
        if include_grab_n_go:
            locations = locations_to_check if locations_to_check else self.GRAB_N_GO.keys()
            for loc in locations:
                if loc not in self.GRAB_N_GO:
                    continue
                menu = self.get_grab_n_go_menu(loc)
                if menu:
                    # Filter by dietary preference
                    if dietary_pref and dietary_pref.lower() != "none":
                        dietary_lower = dietary_pref.lower()
                        if dietary_lower not in [d.lower() for d in menu.get("dietary_options", [])]:
                            continue
                    
                    results.append(menu)
        
        return results
# Dining scraper: crawl the configured UMass Dining Locations & Menus page
# and follow venue links to extract structured information.

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
USER_AGENT = "MinutemenCompass/1.0 (+https://example.edu) Python-httpx"


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