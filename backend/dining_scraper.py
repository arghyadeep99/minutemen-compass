"""
Web scraper for UMass Dining menus
Fetches live menu data from umassdining.com
"""
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

