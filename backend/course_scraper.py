"""
Course Scraper for UMass CICS Course Descriptions
Extracts course information from Fall 2025 and Spring 2026 course description pages
"""
import re
import json
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime, timedelta


class CourseScraper:
    """Scraper for UMass CICS course descriptions"""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        """Initialize the scraper with optional cache directory"""
        self.base_url = "https://content.cs.umass.edu/content"
        self.fall_2025_url = f"{self.base_url}/fall-2025-course-description"
        self.spring_2026_url = f"{self.base_url}/spring-2026-course-descriptions"
        
        # Set up cache directory
        self.cache_dir = cache_dir or Path(__file__).parent / "data" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Use a session for better connection handling
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
    
    def _get_cache_path(self, semester: str) -> Path:
        """Get cache file path for a semester"""
        # Normalize semester name for filename
        semester_normalized = semester.lower().replace(' ', '_')
        return self.cache_dir / f"courses_{semester_normalized}.json"
    
    def _is_cache_valid(self, cache_path: Path, max_age_hours: int = 168) -> bool:
        """Check if cache file is still valid (default 7 days for courses)"""
        if not cache_path.exists():
            return False
        file_time = datetime.fromtimestamp(cache_path.stat().st_mtime)
        age = datetime.now() - file_time
        return age < timedelta(hours=max_age_hours)
    
    def _load_cache(self, cache_path: Path) -> Optional[List[Dict[str, Any]]]:
        """Load course data from cache"""
        if self._is_cache_valid(cache_path):
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Handle both list format and dict format
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and 'courses' in data:
                        return data['courses']
                    return data
            except Exception:
                return None
        return None
    
    def _save_cache(self, cache_path: Path, courses: List[Dict[str, Any]]):
        """Save course data to cache"""
        try:
            cache_data = {
                "courses": courses,
                "cached_at": datetime.now().isoformat(),
                "count": len(courses)
            }
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save cache to {cache_path}: {e}")
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from URL"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def parse_course(self, course_html: str, semester: str) -> Optional[Dict[str, Any]]:
        """Parse a single course from HTML"""
        soup = BeautifulSoup(course_html, 'html.parser')
        
        # Extract course code and title from h2 (course headings are in h2 tags)
        heading = soup.find('h2')
        if not heading:
            # Fallback to h3 if h2 not found
            heading = soup.find('h3')
        
        if not heading:
            return None
        
        heading_text = heading.get_text(strip=True)
        # Pattern: "CICS 110: Foundations of Programming" or "COMPSCI 230: Computer Systems Principles"
        # Skip if it's just "2025 Fall" or similar semester headers
        if re.match(r'^\d{4}\s+(Fall|Spring|Summer|Winter)', heading_text, re.I):
            return None
        
        match = re.match(r'^([A-Z]+\s+\d+[A-Z]?):\s*(.+)$', heading_text)
        if not match:
            return None
        
        course_code = match.group(1).strip()
        course_title = match.group(2).strip()
        
        # Extract instructor(s) - look for h3 with "Instructor" (instructors are in h3 tags)
        instructors = []
        # Try h3 first (most common)
        instructor_elem = soup.find('h3', string=re.compile(r'Instructor', re.I))
        if not instructor_elem:
            # Try h4
            instructor_elem = soup.find('h4', string=re.compile(r'Instructor', re.I))
        if not instructor_elem:
            # Try finding text that contains "Instructor"
            instructor_text_elem = soup.find(string=re.compile(r'Instructor\(s\):', re.I))
            if instructor_text_elem:
                instructor_elem = instructor_text_elem.find_parent()
        
        if instructor_elem:
            instructor_text = instructor_elem.get_text(strip=True)
            # Remove "Instructor(s):" prefix
            instructor_text = re.sub(r'^Instructor\(s\):\s*', '', instructor_text, flags=re.I)
            instructors = [i.strip() for i in instructor_text.split(',') if i.strip()]
        
        # Extract full text content
        full_text = soup.get_text(separator=' ', strip=True)
        
        # Extract description - everything between instructor and prerequisites
        description = ""
        description_start = False
        description_parts = []
        
        # Look for paragraphs and divs
        for elem in soup.find_all(['p', 'div']):
            text = elem.get_text(strip=True)
            # Skip empty or very short elements
            if len(text) < 20:
                continue
            # Skip instructor line
            if 'Instructor' in text and len(text) < 150:
                continue
            # Skip course code line
            if course_code in text and len(text) < 80:
                continue
            # Skip prerequisites line (we'll extract separately)
            if 'Prerequisite' in text and len(text) < 200:
                continue
            # Skip credits line
            if re.search(r'\d+\s+credit', text, re.I) and len(text) < 50:
                continue
            # This is likely description text
            if len(text) > 50:
                description_parts.append(text)
        
        description = ' '.join(description_parts).strip()
        
        # If no description found, try extracting from full text
        if not description:
            # Find text between instructor and prerequisite
            full_text_lower = full_text.lower()
            instructor_pos = full_text_lower.find('instructor')
            prereq_pos = full_text_lower.find('prerequisite')
            credits_pos = full_text_lower.find('credit')
            
            if instructor_pos != -1:
                start = instructor_pos + 100  # Skip instructor line
                end = prereq_pos if prereq_pos != -1 else (credits_pos if credits_pos != -1 else len(full_text))
                description = full_text[start:end].strip()
                # Clean up
                description = re.sub(r'\s+', ' ', description)
                if len(description) < 50:
                    description = ""
        
        # Extract prerequisites
        prerequisites = ""
        prereq_pattern = r'Prerequisite:\s*([^\.]+(?:\.|$))'
        prereq_match = re.search(prereq_pattern, full_text, re.I | re.DOTALL)
        if prereq_match:
            prerequisites = prereq_match.group(1).strip()
            # Remove trailing period if present
            prerequisites = prerequisites.rstrip('.')
        
        # Extract credits
        credits = None
        credits_pattern = r'(\d+)\s+credit'
        credits_match = re.search(credits_pattern, full_text, re.I)
        if credits_match:
            credits = int(credits_match.group(1))
        
        course_data = {
            "course_code": course_code,
            "course_title": course_title,
            "instructors": instructors,
            "description": description,
            "prerequisites": prerequisites,
            "credits": credits,
            "semester": semester
        }
        
        return course_data
    
    def scrape_semester(self, url: str, semester: str, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Scrape all courses from a semester page, using cache if available and valid"""
        cache_path = self._get_cache_path(semester)
        
        # Try to load from cache first
        if use_cache:
            cached_courses = self._load_cache(cache_path)
            if cached_courses is not None:
                return cached_courses
        
        # Cache miss or invalid - scrape from web (only if use_cache=False or cache invalid)
        html = self.fetch_page(url)
        if not html:
            # If fetch fails and we have stale cache, use it
            if cache_path.exists():
                cached_courses = self._load_cache(cache_path)
                if cached_courses is not None:
                    return cached_courses
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        courses = []
        
        # Find the main content area
        main_content = soup.find('main') or soup.find('article') or soup.find('div', class_=re.compile(r'content|main', re.I))
        if not main_content:
            main_content = soup
        
        # Find all course sections (h2 tags with course codes)
        # Course headings are in h2 tags, not h3
        all_headings = main_content.find_all(['h2', 'h3'])
        
        for i, heading in enumerate(all_headings):
            heading_text = heading.get_text(strip=True)
            
            # Skip semester headers like "2025 Fall"
            if re.match(r'^\d{4}\s+(Fall|Spring|Summer|Winter)', heading_text, re.I):
                continue
            
            # Check if this is a course heading (contains course code pattern)
            if not re.match(r'^[A-Z]+\s+\d+[A-Z]?:\s*', heading_text):
                continue
            
            # Collect all content for this course until next h2
            # Include h3 tags (they contain instructors) but stop at next h2 (next course)
            course_elements = [heading]
            current = heading.find_next_sibling()
            while current:
                # Stop at next h2 (next course heading)
                if current.name == 'h2':
                    break
                # Include h3 (instructors) and other elements
                course_elements.append(current)
                current = current.find_next_sibling()
            
            # Create HTML string for this course section
            course_html = ''.join(str(elem) for elem in course_elements)
            
            course_data = self.parse_course(course_html, semester)
            if course_data:
                courses.append(course_data)
        
        # Save to cache
        if courses:
            self._save_cache(cache_path, courses)
        
        return courses
    
    def scrape_all_courses(self, use_cache: bool = True) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape courses from both semesters, using cache if available"""
        fall_courses = self.scrape_semester(self.fall_2025_url, "Fall 2025", use_cache=use_cache)
        spring_courses = self.scrape_semester(self.spring_2026_url, "Spring 2026", use_cache=use_cache)
        
        return {
            "fall_2025": fall_courses,
            "spring_2026": spring_courses
        }
    
    def save_courses(self, courses_data: Dict[str, List[Dict[str, Any]]], output_path: Path):
        """Save courses to JSON file"""
        # Flatten all courses into a single list with semester info
        all_courses = []
        for semester, courses in courses_data.items():
            for course in courses:
                all_courses.append(course)
        
        # Also create a lookup by course code
        courses_by_code = {}
        for course in all_courses:
            code = course["course_code"]
            if code not in courses_by_code:
                courses_by_code[code] = []
            courses_by_code[code].append(course)
        
        output_data = {
            "courses": all_courses,
            "courses_by_code": courses_by_code,
            "semesters": {
                "fall_2025": len(courses_data.get("fall_2025", [])),
                "spring_2026": len(courses_data.get("spring_2026", []))
            },
            "total_courses": len(all_courses),
            "unique_course_codes": len(courses_by_code)
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        
        print(f"Saved {len(all_courses)} courses to {output_path}")


def main():
    """Main function to scrape and save courses"""
    scraper = CourseScraper()
    courses_data = scraper.scrape_all_courses()
    
    # Save to data directory
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    output_path = data_dir / "courses.json"
    
    scraper.save_courses(courses_data, output_path)
    print(f"\nCourse data saved to {output_path}")


if __name__ == "__main__":
    main()

