"""
Bus Schedule PDF Parser for PVTA Bus Schedules
Downloads and parses bus schedule PDFs with caching and time-aware queries
"""
import os
import re
import json
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

try:
    import pytz
    EST = pytz.timezone('US/Eastern')
    HAS_PYTZ = True
except ImportError:
    # Fallback: EST is UTC-5 (or UTC-4 during DST)
    # For simplicity, use UTC-5 offset
    EST = timezone(timedelta(hours=-5))
    HAS_PYTZ = False

try:
    import PyPDF2
    PDF_LIBRARY = "PyPDF2"
except ImportError:
    try:
        import pdfplumber
        PDF_LIBRARY = "pdfplumber"
    except ImportError:
        PDF_LIBRARY = None

load_dotenv()


class BusScheduleParser:
    """Parser for PVTA bus schedule PDFs"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the parser with optional cache directory"""
        self.cache_dir = cache_dir or Path("data/cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Get PDF URLs from environment (can be single URL or JSON string with route->URL mapping)
        self.pdf_urls = self._load_pdf_urls()
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
        if PDF_LIBRARY is None:
            print("[ERROR] No PDF library found. Install PyPDF2 or pdfplumber:")
            print("  pip install PyPDF2 pdfplumber")
            print("  OR: pip install -r requirements.txt")
    
    def _load_pdf_urls(self) -> Dict[str, str]:
        """Load PDF URLs from environment variable"""
        pdf_url_config = os.getenv("BUS_SCHEDULE_PDF_URLS")
        pdf_url_single = os.getenv("BUS_SCHEDULE_PDF_URL")  # Legacy support
        
        urls = {}
        
        # Try JSON format first (route -> URL mapping)
        if pdf_url_config:
            try:
                urls = json.loads(pdf_url_config)
                if isinstance(urls, dict):
                    return urls
            except json.JSONDecodeError:
                # Not valid JSON, might be a single URL
                pass
        
        # Fallback to single URL (legacy support)
        if pdf_url_single:
            # If single URL provided, use it for all routes
            # Store as a special key that can be used as fallback
            urls["_default"] = pdf_url_single
        
        if not urls:
            print("Warning: BUS_SCHEDULE_PDF_URLS or BUS_SCHEDULE_PDF_URL not set in .env file")
        
        return urls
    
    def _get_cache_path(self, route_number: Optional[str] = None) -> Path:
        """Get cache file path for parsed schedule"""
        if route_number:
            # Cache per route
            route_safe = route_number.replace("/", "_").replace("\\", "_")
            return self.cache_dir / f"bus_schedule_{route_safe}.json"
        else:
            # General cache (for all routes combined)
            return self.cache_dir / "bus_schedule_parsed.json"
    
    def _is_cache_valid(self, cache_path: Path, max_age_hours: int = 24) -> bool:
        """Check if cache file is still valid (default 24 hours)"""
        if not cache_path.exists():
            return False
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        if HAS_PYTZ:
            current_time = datetime.now(EST)
            file_time = EST.localize(file_time) if file_time.tzinfo is None else file_time
        else:
            current_time = datetime.now(EST)
            file_time = file_time.replace(tzinfo=EST)
        age = current_time - file_time
        return age < timedelta(hours=max_age_hours)
    
    def _load_cache(self, cache_path: Path) -> Optional[Dict[str, Any]]:
        """Load parsed schedule from cache"""
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return None
        return None
    
    def _save_cache(self, cache_path: Path, schedule_data: Dict[str, Any]):
        """Save parsed schedule to cache"""
        try:
            schedule_data["cached_at"] = datetime.now(EST).isoformat()
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(schedule_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save cache: {e}")
    
    def _download_pdf(self, pdf_url: str) -> Optional[bytes]:
        """Download PDF from URL"""
        if not pdf_url:
            print(f"[DEBUG] No PDF URL provided")
            return None
        
        print(f"[DEBUG] Downloading PDF from: {pdf_url}")
        try:
            response = self.session.get(pdf_url, timeout=30)
            response.raise_for_status()
            content_length = len(response.content)
            print(f"[DEBUG] PDF downloaded successfully: {content_length} bytes")
            return response.content
        except Exception as e:
            print(f"[ERROR] Failed to download PDF from {pdf_url}: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _extract_text_from_pdf(self, pdf_content: bytes) -> str:
        """Extract text from PDF content"""
        if PDF_LIBRARY == "PyPDF2":
            return self._extract_with_pypdf2(pdf_content)
        elif PDF_LIBRARY == "pdfplumber":
            return self._extract_with_pdfplumber(pdf_content)
        else:
            raise ValueError("No PDF library available")
    
    def _extract_with_pypdf2(self, pdf_content: bytes) -> str:
        """Extract text using PyPDF2"""
        import io
        pdf_file = io.BytesIO(pdf_content)
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    
    def _extract_with_pdfplumber(self, pdf_content: bytes) -> str:
        """Extract text using pdfplumber"""
        import io
        pdf_file = io.BytesIO(pdf_content)
        
        text = ""
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    
    def _parse_schedule_text(self, text: str) -> Dict[str, Any]:
        """Parse schedule text into structured data with comprehensive extraction"""
        schedules = {}
        
        lines = text.split('\n')
        current_route = None
        route_start_idx = None
        
        # Look for route numbers (e.g., "Route 30", "30", "B43", "Route B43")
        route_patterns = [
            r'^Route\s+(\d+[A-Z]?)\b',
            r'^\s*(\d+[A-Z]?)\s*$',  # Just route number on its own line
            r'^\s*(\d+[A-Z]?)\s+',  # Route number at start of line
            r'\bRoute\s+([A-Z]\d+)\b',  # "Route B43"
        ]
        
        # Process lines to identify routes and their sections
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            # Try to identify route numbers
            route_found = False
            for pattern in route_patterns:
                match = re.match(pattern, line_stripped, re.I)
                if match:
                    route_num = match.group(1).upper()
                    if route_num not in schedules:
                        schedules[route_num] = {
                            "route_number": route_num,
                            "route_name": "",
                            "stops": [],
                            "directions": [],
                            "schedule_times": {},  # {direction: {stop: [times]}}
                            "days_of_operation": [],
                            "effective_date": "",
                            "raw_text": [],
                            "schedule_lines": []
                        }
                    current_route = route_num
                    route_start_idx = i
                    route_found = True
                    break
            
            # Collect all text for current route
            if current_route:
                schedules[current_route]["raw_text"].append(line_stripped)
        
        # Now parse each route's data in detail
        for route_num, route_data in schedules.items():
            self._parse_route_details(route_num, route_data, lines)
        
        return schedules
    
    def _parse_route_details(self, route_num: str, route_data: Dict[str, Any], all_lines: List[str]):
        """Parse detailed information for a specific route"""
        raw_text = route_data["raw_text"]
        
        # Extract effective date
        for line in raw_text[:10]:
            date_match = re.search(r'Effective\s+(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})', line, re.I)
            if date_match:
                route_data["effective_date"] = date_match.group(1)
                break
        
        # Extract route name/description (usually after route number)
        route_name_parts = []
        for i, line in enumerate(raw_text[:20]):
            # Look for descriptive text after route number
            if i > 0 and len(line) > 5 and not re.match(r'^\d+', line):
                # Check if it's not a time or stop header
                if not re.search(r'\d{1,2}:\d{2}', line) and not line.upper() in ['LEAVE', 'ARRIVE', 'TO', 'FROM']:
                    route_name_parts.append(line)
                    if len(route_name_parts) >= 2:
                        break
        if route_name_parts:
            route_data["route_name"] = " - ".join(route_name_parts[:2])
        
        # Extract stops from header section
        # The PDF has stops listed in header rows, often with concatenated words
        stops_found = []
        
        # Look for the header section (usually has "LEAVE", "ARRIVE", or stop names)
        header_section_start = None
        for i, line in enumerate(raw_text[:50]):
            line_upper = line.upper().strip()
            # Detect header section
            if 'LEAVE' in line_upper or 'ARRIVE' in line_upper:
                header_section_start = i + 1  # Start after LEAVE/ARRIVE
                break
        
        # Extract stops from header lines
        if header_section_start is not None:
            # Process header lines (usually 3-8 lines with stop names)
            for i in range(header_section_start, min(header_section_start + 15, len(raw_text))):
                line = raw_text[i].strip()
                
                # Stop if we hit schedule times or direction headers
                if re.search(r'\d{1,2}:\d{2}', line) or line.upper().startswith('TO ') or line.upper().startswith('FROM '):
                    break
                
                # Skip empty lines and labels
                if not line or line.upper() in ['FULL SERVICE WEEKDAY', 'FULL SERVICE WEEKEND']:
                    continue
                
                # Handle concatenated words (common in PDF extraction)
                # Split on capital letters: "APTS.AMHERST" -> "APTS", "AMHERST"
                # Split on periods: "APTS.AMHERST" -> "APTS", "AMHERST"
                line_fixed = re.sub(r'\.([A-Z])', r'. \1', line)  # Add space after period before capital
                line_fixed = re.sub(r'([a-z])([A-Z])', r'\1 \2', line_fixed)  # Add space between camelCase
                line_fixed = re.sub(r'([A-Z])([A-Z][a-z])', r'\1 \2', line_fixed)  # Split ALLCAPS followed by Capitalized
                
                # Extract potential stop names
                words = line_fixed.split()
                current_stop = []
                
                for word in words:
                    word_clean = word.strip('.,;:').upper()
                    
                    # Skip common non-stop words
                    skip_words = ['LEAVE', 'ARRIVE', 'TO', 'FROM', 'PVTA', 'THE', 'OFFICIAL', 'REAL', 'TIME', 
                                 'INFORMATION', 'APP', 'OF', 'WEEKDAY', 'WEEKEND', 'SERVICE', 'FULL']
                    if word_clean in skip_words:
                        if current_stop:
                            stop_name = ' '.join(current_stop)
                            if len(stop_name) > 2 and stop_name not in stops_found:
                                stops_found.append(stop_name)
                            current_stop = []
                        continue
                    
                    # Stop indicators that help identify stops
                    stop_indicators = ['APTS', 'APT', 'BUILDING', 'CENTER', 'STATION', 'STOP', 
                                      'LANE', 'STREET', 'ROAD', 'ESTATES', 'VILLAGE', 'POST', 'OFFICE',
                                      'ARTS', 'GRC', 'PSB', 'COWLES', 'BOULDERS', 'CLIFFSIDE', 
                                      'SUGARLOAF', 'TOWNEHOUSE', 'SUNDERLAND', 'HAMPSHIRE']
                    
                    # Build stop name
                    if any(indicator in word_clean for indicator in stop_indicators) or len(word_clean) > 3:
                        current_stop.append(word)
                    elif current_stop:
                        # Continue building current stop
                        current_stop.append(word)
                    else:
                        # Single word stop if it's substantial
                        if len(word_clean) > 4 and word_clean not in ['UMASS', 'AMHERST']:
                            if word_clean not in [s.upper() for s in stops_found]:
                                stops_found.append(word)
                
                # Add final stop if we have one
                if current_stop:
                    stop_name = ' '.join(current_stop)
                    if len(stop_name) > 2 and stop_name not in stops_found:
                        stops_found.append(stop_name)
        
        # Clean up and normalize stop names
        cleaned_stops = []
        known_stops_map = {
            'buildingcliffside': 'Cliffside APTS',
            'sunderlandarrive': 'Sunderland',
            'estatesleave': 'Sugarloaf Estates',
            'estatestownehouse': 'Townehouse APTS',
            'grc/psbamherst': 'UMASS GRC/PSB Amherst',
            'lanearrive': 'Cowles Lane',
            'boulders': 'Boulders APTS',
            'apts amherst': 'Boulders APTS Amherst',
        }
        
        for stop in stops_found:
            stop_lower = stop.lower()
            
            # Check known mappings first
            if stop_lower in known_stops_map:
                stop = known_stops_map[stop_lower]
            else:
                # Fix common concatenations
                stop = re.sub(r'building([a-z]+)', r'Building \1', stop, flags=re.I)
                stop = re.sub(r'([a-z]+)arrive', r'\1', stop, flags=re.I)
                stop = re.sub(r'([a-z]+)leave', r'\1', stop, flags=re.I)
                stop = re.sub(r'estates([a-z]+)', r'Estates \1', stop, flags=re.I)
                stop = re.sub(r'grc/psb([a-z]+)', r'GRC/PSB \1', stop, flags=re.I)
                stop = re.sub(r'([a-z]+)lane', r'\1 Lane', stop, flags=re.I)
                stop = re.sub(r'\bapts?\.?\s*amherst\b', 'APTS Amherst', stop, flags=re.I)
                stop = re.sub(r'\bpost\s*office\s*umass\b', 'Post Office UMASS', stop, flags=re.I)
                stop = re.sub(r'\bstudio\s*arts\b', 'Studio Arts Building', stop, flags=re.I)
                stop = re.sub(r'\bcliffside\s*apts?\b', 'Cliffside APTS', stop, flags=re.I)
                stop = re.sub(r'\bsugarloaf\s*estates\b', 'Sugarloaf Estates', stop, flags=re.I)
                stop = re.sub(r'\btownehouse\s*apts?\b', 'Townehouse APTS', stop, flags=re.I)
                stop = re.sub(r'\bgrc/psb\b', 'UMASS GRC/PSB', stop, flags=re.I)
                stop = re.sub(r'\bcowles\s*lane\b', 'Cowles Lane', stop, flags=re.I)
                stop = re.sub(r'\bboulders\b', 'Boulders APTS', stop, flags=re.I)
            
            # Capitalize properly
            words = stop.split()
            capitalized_words = []
            for word in words:
                word_upper = word.upper()
                if word_upper in ['APTS', 'APT', 'UMASS', 'GRC', 'PSB']:
                    capitalized_words.append(word_upper)
                elif word_upper in ['AMHERST', 'POST', 'OFFICE', 'ARTS', 'BUILDING']:
                    capitalized_words.append(word.capitalize())
                else:
                    capitalized_words.append(word.capitalize())
            stop = ' '.join(capitalized_words)
            
            # Final cleanup - remove single letter words and very short stops
            stop = re.sub(r'\b[A-Z]\s+', '', stop)  # Remove single letter words
            stop = stop.strip()
            
            if stop and len(stop) > 2 and stop not in cleaned_stops:
                cleaned_stops.append(stop)
        
        route_data["stops"] = cleaned_stops[:30]  # Increased limit
        
        # Extract directions
        directions = []
        for line in raw_text[:30]:
            if re.search(r'\bTo\s+([A-Z][A-Za-z\s]+)', line, re.I):
                dir_match = re.search(r'\bTo\s+([A-Z][A-Za-z\s]+)', line, re.I)
                if dir_match:
                    direction = dir_match.group(1).strip()
                    if direction not in directions:
                        directions.append(direction)
        route_data["directions"] = directions
        
        # Extract days of operation
        days_keywords = {
            'WEEKDAY': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
            'WEEKEND': ['Saturday', 'Sunday'],
            'FULL SERVICE': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
            'MONDAY': ['Monday'],
            'TUESDAY': ['Tuesday'],
            'WEDNESDAY': ['Wednesday'],
            'THURSDAY': ['Thursday'],
            'FRIDAY': ['Friday'],
            'SATURDAY': ['Saturday'],
            'SUNDAY': ['Sunday']
        }
        
        days_found = []
        for line in raw_text[:30]:
            line_upper = line.upper()
            for keyword, days in days_keywords.items():
                if keyword in line_upper:
                    for day in days:
                        if day not in days_found:
                            days_found.append(day)
        route_data["days_of_operation"] = days_found if days_found else ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        
        # Extract schedule times
        schedule_times = {}
        current_direction = None
        
        for line in raw_text:
            line_stripped = line.strip()
            
            # Detect direction headers
            if 'To ' in line_stripped or 'From ' in line_stripped:
                dir_match = re.search(r'(?:To|From)\s+([A-Z][A-Za-z\s]+)', line_stripped, re.I)
                if dir_match:
                    current_direction = dir_match.group(1).strip()
                    if current_direction not in schedule_times:
                        schedule_times[current_direction] = {}
            
            # Extract time rows
            # Look for lines with multiple times (schedule rows)
            time_matches = re.findall(r'\b(\d{1,2}):(\d{2})\b', line_stripped)
            if len(time_matches) >= 3:  # Multiple times = schedule row
                times = []
                for hour, minute in time_matches:
                    try:
                        h, m = int(hour), int(minute)
                        # Convert to 24-hour format if needed
                        time_str = f"{h:02d}:{m:02d}"
                        times.append(time_str)
                    except ValueError:
                        continue
                
                if times:
                    route_data["schedule_lines"].append(line_stripped)
                    # Store times - associate with stops if possible
                    if not schedule_times:
                        schedule_times["All"] = {"times": times}
                    elif current_direction:
                        if "times" not in schedule_times[current_direction]:
                            schedule_times[current_direction]["times"] = []
                        schedule_times[current_direction]["times"].extend(times)
        
        route_data["schedule_times"] = schedule_times
        
        # Store all schedule lines for reference
        if not route_data["schedule_lines"]:
            # Fallback: store lines with times
            for line in raw_text:
                if re.search(r'\d{1,2}:\d{2}', line):
                    route_data["schedule_lines"].append(line.strip())
    
    def parse_pdf(self, route_number: Optional[str] = None, use_cache: bool = True) -> Dict[str, Any]:
        """Parse PDF schedule with caching. If route_number is provided, parse that route's PDF."""
        print(f"[DEBUG] parse_pdf called: route_number={route_number}, use_cache={use_cache}")
        
        # Determine which PDF URL to use
        pdf_url = None
        if route_number and route_number in self.pdf_urls:
            pdf_url = self.pdf_urls[route_number]
            print(f"[DEBUG] Using route-specific PDF URL for route {route_number}")
        elif "_default" in self.pdf_urls:
            pdf_url = self.pdf_urls["_default"]
            print(f"[DEBUG] Using default PDF URL")
        elif self.pdf_urls:
            # Use first available URL
            pdf_url = list(self.pdf_urls.values())[0]
            print(f"[DEBUG] Using first available PDF URL")
        
        if not pdf_url:
            error_msg = "BUS_SCHEDULE_PDF_URLS not configured"
            print(f"[ERROR] {error_msg}")
            return {"error": error_msg}
        
        cache_path = self._get_cache_path(route_number)
        print(f"[DEBUG] Cache path: {cache_path}")
        
        # Try to load from cache first
        if use_cache:
            cached_data = self._load_cache(cache_path)
            if cached_data:
                print(f"[DEBUG] Using cached data (found {len(cached_data.get('schedules', {}))} routes)")
                return cached_data
            else:
                print(f"[DEBUG] No valid cache found, will download PDF")
        
        # Download and parse PDF
        pdf_content = self._download_pdf(pdf_url)
        if not pdf_content:
            # Try to use stale cache if download fails
            if cache_path.exists():
                cached_data = self._load_cache(cache_path)
                if cached_data:
                    return cached_data
            return {"error": f"Failed to download PDF for route {route_number or 'default'}"}
        
        # Extract text
        try:
            print(f"[DEBUG] Extracting text from PDF (size: {len(pdf_content)} bytes)")
            text = self._extract_text_from_pdf(pdf_content)
            print(f"[DEBUG] Extracted {len(text)} characters from PDF")
            if len(text) < 100:
                print(f"[WARNING] Very little text extracted. First 500 chars: {text[:500]}")
        except Exception as e:
            error_msg = f"Failed to extract text from PDF: {e}"
            print(f"[ERROR] {error_msg}")
            import traceback
            traceback.print_exc()
            return {"error": error_msg}
        
        # Parse schedule
        print(f"[DEBUG] Parsing schedule text...")
        schedules = self._parse_schedule_text(text)
        print(f"[DEBUG] Parsed {len(schedules)} routes from PDF")
        if schedules:
            for route_num, route_data in list(schedules.items())[:3]:
                stops = route_data.get("stops", [])
                print(f"[DEBUG] Route {route_num}: {len(stops)} stops - {', '.join(stops[:3])}")
        
        current_time = datetime.now(EST)
        result = {
            "schedules": schedules,
            "parsed_at": current_time.isoformat(),
            "source_url": pdf_url,
            "route_number": route_number
        }
        
        # Save to cache
        print(f"[DEBUG] Saving to cache: {cache_path}")
        self._save_cache(cache_path, result)
        
        return result
    
    def parse_all_routes(self, use_cache: bool = True) -> Dict[str, Any]:
        """Parse all route PDFs and combine results"""
        all_schedules = {}
        
        # Parse each route's PDF
        for route_num, pdf_url in self.pdf_urls.items():
            if route_num == "_default":
                # Parse default PDF (might contain multiple routes)
                result = self.parse_pdf(route_number=None, use_cache=use_cache)
                if "schedules" in result:
                    all_schedules.update(result["schedules"])
            else:
                # Parse route-specific PDF
                result = self.parse_pdf(route_number=route_num, use_cache=use_cache)
                if "schedules" in result:
                    all_schedules.update(result["schedules"])
        
        return {
            "schedules": all_schedules,
            "parsed_at": datetime.now(EST).isoformat(),
            "total_routes": len(all_schedules)
        }
    
    def find_route(self, route_number: Optional[str] = None, route_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find routes matching route number or name"""
        # If route_number is specified and we have a PDF for it, parse that specific PDF
        if route_number and route_number in self.pdf_urls:
            schedule_data = self.parse_pdf(route_number=route_number, use_cache=True)
        elif route_number and "_default" in self.pdf_urls:
            # Use default PDF
            schedule_data = self.parse_pdf(route_number=None, use_cache=True)
        elif self.pdf_urls:
            # Parse first available PDF
            first_route = list(self.pdf_urls.keys())[0]
            if first_route != "_default":
                schedule_data = self.parse_pdf(route_number=first_route, use_cache=True)
            else:
                schedule_data = self.parse_pdf(route_number=None, use_cache=True)
        else:
            return []
        
        if "error" in schedule_data:
            return []
        
        schedules = schedule_data.get("schedules", {})
        results = []
        
        for route_num, route_data in schedules.items():
            match = False
            
            if route_number:
                # Match route number
                if route_number.upper() in route_num.upper() or route_num.upper() in route_number.upper():
                    match = True
            
            if route_name:
                # Match route name
                route_name_lower = route_name.lower()
                route_data_name = route_data.get("route_name", "").lower()
                stops = [s.lower() for s in route_data.get("stops", [])]
                
                if (route_name_lower in route_data_name or 
                    any(route_name_lower in stop for stop in stops)):
                    match = True
            
            if match or (not route_number and not route_name):
                results.append({
                    "route_number": route_num,
                    "route_name": route_data.get("route_name", ""),
                    "stops": route_data.get("stops", []),
                    "raw_text": route_data.get("raw_text", [])[:20],  # More context
                    "schedule_lines": route_data.get("schedule_lines", [])[:10]
                })
        
        return results
    
    def get_next_bus_times(
        self, 
        route_number: Optional[str] = None,
        stop: Optional[str] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get next bus times for a route and stop"""
        if current_time is None:
            current_time = datetime.now(EST)
        else:
            # Ensure timezone aware
            if current_time.tzinfo is None:
                if HAS_PYTZ:
                    current_time = EST.localize(current_time)
                else:
                    current_time = current_time.replace(tzinfo=EST)
        
        # Parse PDF for the specific route if available
        if route_number and route_number in self.pdf_urls:
            schedule_data = self.parse_pdf(route_number=route_number, use_cache=True)
        else:
            schedule_data = self.parse_pdf(route_number=route_number, use_cache=True)
        
        if "error" in schedule_data:
            return {
                "error": schedule_data["error"],
                "next_times": []
            }
        
        # Find matching routes
        routes = self.find_route(route_number=route_number)
        
        if not routes:
            return {
                "error": f"No route found matching '{route_number}'",
                "next_times": []
            }
        
        # Parse times from raw text, filtering by stop if provided
        all_times = []
        for route in routes:
            raw_text = route.get("raw_text", [])
            schedule_lines = route.get("schedule_lines", [])
            
            # Use schedule_lines if available, otherwise use raw_text
            text_to_parse = schedule_lines if schedule_lines else raw_text
            
            # If stop is specified, only parse lines containing that stop
            if stop:
                text_to_parse = [
                    line for line in text_to_parse 
                    if stop.lower() in line.lower()
                ]
            
            # Extract times from text
            for line in text_to_parse:
                # Look for time patterns (HH:MM AM/PM)
                time_matches = re.findall(r'\b(\d{1,2}):(\d{2})\s*(AM|PM|am|pm)\b', line)
                for match in time_matches:
                    hour, minute, am_pm = match
                    hour = int(hour)
                    minute = int(minute)
                    
                    # Convert to 24-hour format
                    if am_pm.upper() == 'PM' and hour != 12:
                        hour += 12
                    elif am_pm.upper() == 'AM' and hour == 12:
                        hour = 0
                    
                    # Create datetime for today in EST
                    try:
                        bus_time = current_time.replace(hour=hour, minute=minute, second=0, microsecond=0)
                        
                        # If time has passed, assume it's for tomorrow
                        if bus_time < current_time:
                            bus_time += timedelta(days=1)
                        
                        all_times.append(bus_time)
                    except ValueError:
                        # Invalid time (e.g., hour > 23)
                        continue
        
        # Filter times after current time, sort, and get unique
        future_times = [t for t in all_times if t > current_time]
        future_times = sorted(set(future_times))[:10]  # Next 10 times
        
        return {
            "route_number": route_number,
            "stop": stop,
            "current_time": current_time.strftime("%I:%M %p %Z"),
            "next_times": [t.strftime("%I:%M %p %Z") for t in future_times],
            "next_times_24h": [t.strftime("%H:%M") for t in future_times],
            "timezone": "EST"
        }

