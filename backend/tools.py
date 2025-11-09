"""
Tool Registry for UMass Campus Agent
Implements various tools that the Gemini agent can call
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import os
from zoneinfo import ZoneInfo

from dining_scraper import get_dining_data_cached, get_dining_menus_cached
from cics_scraper import (
    get_cics_pages_cached,
    search_cics_pages as search_cics_pages_cached,
    DEFAULT_CICS_URLS,
    get_approved_alternate_courses_cached,
    get_cics_faqs_cached,
    get_cics_research_areas_cached,
    get_cics_contacts_cached,
    get_cics_courses_index_cached,
)


class ToolRegistry:
    """Registry for all available tools"""

    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(exist_ok=True)
        self._load_data()

    def _load_data(self):
        """Load JSON data files"""
        # Study spaces
        study_spaces_path = self.data_dir / "study_spaces.json"
        if study_spaces_path.exists():
            with open(study_spaces_path, "r", encoding="utf-8") as f:
                self.study_spaces = json.load(f)
        else:
            self.study_spaces = []

        # Dining options
        dining_path = self.data_dir / "dining.json"
        if dining_path.exists():
            with open(dining_path, "r", encoding="utf-8") as f:
                self.dining_options = json.load(f)
        else:
            self.dining_options = []

        # Resources
        resources_path = self.data_dir / "resources.json"
        if resources_path.exists():
            with open(resources_path, "r", encoding="utf-8") as f:
                self.resources = json.load(f)
        else:
            self.resources = []

        # Bus schedules
        bus_path = self.data_dir / "bus_schedules.json"
        if bus_path.exists():
            with open(bus_path, "r", encoding="utf-8") as f:
                self.bus_schedules = json.load(f)
        else:
            self.bus_schedules = []

        # CICS pages cache (optional)
        cics_path = self.data_dir / "cics_pages.json"
        if cics_path.exists():
            try:
                with open(cics_path, "r", encoding="utf-8") as f:
                    self.cics_pages = json.load(f)
            except Exception:
                self.cics_pages = []
        else:
            self.cics_pages = []

    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Return tool schemas in Gemini function declaration format (flat list)."""
        return [
            {
                "name": "get_study_spots",
                "description": "Find study spaces on campus based on location, noise preference, and group size",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "Preferred location on campus (e.g., 'Central', 'North', 'South', 'LGRC', 'Library')",
                        },
                        "noise_preference": {
                            "type": "string",
                            "description": "Noise level preference: 'quiet', 'moderate', or 'collaborative'",
                            "enum": ["quiet", "moderate", "collaborative"],
                        },
                        "group_size": {
                            "type": "string",
                            "description": "Number of people: '1', '2-3', '4-6', '7+'",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_dining_options",
                "description": "Find dining options on campus based on current time and dietary preferences",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "time_now": {
                            "type": "string",
                            "description": "Current time in HH:MM format (24-hour) or 'now'",
                        },
                        "dietary_pref": {
                            "type": "string",
                            "description": "Dietary preference: 'vegetarian', 'vegan', 'halal', 'gluten-free', 'none'",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "scrape_dining_info",
                "description": "Scrape live dining info from the configured dining URL and filter results.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Optional search text, e.g., 'Berkshire', 'cafe', 'late night', etc.",
                        },
                        "dietary_pref": {
                            "type": "string",
                            "description": "Dietary preference to filter by: 'vegetarian', 'vegan', 'halal', 'gluten-free', 'kosher', 'none'",
                        },
                        "time_now": {
                            "type": "string",
                            "description": "Current time in HH:MM format (24-hour) or 'now'. Used for heuristics.",
                        },
                        "limit": {
                            "type": "number",
                            "description": "Maximum number of results to return (default 5).",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "scrape_dining_menu",
                "description": "Scrape structured dining menus (Worcester-style) across halls and filter by hall/meal.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "hall": {
                            "type": "string",
                            "description": "Hall name to filter (e.g., 'Worcester', 'Berkshire', 'Franklin', 'Hampshire').",
                        },
                        "meal": {
                            "type": "string",
                            "description": "Meal to filter: 'Breakfast', 'Brunch', 'Lunch', 'Dinner', 'Late Night'.",
                        },
                        "limit_halls": {
                            "type": "number",
                            "description": "Max number of halls to return (default 3).",
                        },
                        "limit_categories": {
                            "type": "number",
                            "description": "Max number of categories per hall/meal (default 8).",
                        },
                        "limit_items": {
                            "type": "number",
                            "description": "Max number of items per category (default 20).",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_support_resources",
                "description": "Find campus support resources for various needs (academic, mental health, financial, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "topic": {
                            "type": "string",
                            "description": "Type of support needed: 'mental_health', 'academic', 'financial', 'disability', 'general'",
                        }
                    },
                    "required": [],
                },
            },
            {
                "name": "get_bus_schedule",
                "description": "Get PVTA bus schedule information between campus locations",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "origin": {
                            "type": "string",
                            "description": "Starting location (e.g., 'Campus Center', 'Puffton', 'North Village')",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination location",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_course_info",
                "description": "Get information about courses, including course content, prerequisites, and instructor details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "course_code": {
                            "type": "string",
                            "description": "Course code (e.g., 'CS 187', 'MATH 131')",
                        },
                        "info_type": {
                            "type": "string",
                            "description": "Type of information needed: 'content', 'prerequisites', 'instructor', 'schedule'",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_facility_info",
                "description": "Get information about campus facilities (gyms, libraries, labs, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "facility_name": {
                            "type": "string",
                            "description": "Name of the facility",
                        },
                        "info_type": {
                            "type": "string",
                            "description": "Type of information: 'hours', 'location', 'amenities', 'availability'",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "report_facility_issue",
                "description": "Report a facility issue (broken equipment, maintenance, etc.)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "facility_name": {
                            "type": "string",
                            "description": "Name of the facility or location",
                        },
                        "issue_type": {
                            "type": "string",
                            "description": "Type of issue: 'maintenance', 'safety', 'accessibility', 'other'",
                        },
                        "description": {
                            "type": "string",
                            "description": "Brief description of the issue",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "get_current_time_est",
                "description": "Get the current time in the UMass Amherst timezone (America/New_York), with multiple formats.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "format": {
                            "type": "string",
                            "description": "Optional key to return a single value (e.g., 'iso', 'time_24h', 'time_12h', 'date', 'weekday', 'tz_abbreviation', 'utc_offset', 'unix_epoch', 'human', 'time', 'time24', 'time12')."
                        },
                        "include_seconds": {
                            "type": "boolean",
                            "description": "Whether to include seconds in time formats (default false)."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "refresh_cics_pages",
                "description": "Fetch and cache CICS pages (MS advising FAQs, approved alternate courses, courses, research areas, contact). Stores raw HTML and searchable text.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "urls": {
                            "type": "array",
                            "description": "Optional list of URLs to refresh. Defaults to CICS core pages.",
                            "items": {"type": "string"},
                        },
                        "force": {
                            "type": "boolean",
                            "description": "If true, bypass cache and force refetch (default false)."
                        },
                        "cache_hours": {
                            "type": "number",
                            "description": "Cache freshness window in hours when not forcing (default 24)."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "search_cics_pages",
                "description": "Search cached CICS pages to answer questions about CICS courses, advising, research areas, or contacts.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query, e.g., 'MS residency requirement', 'approved alternate courses for AI', 'CICS contact'."
                        },
                        "limit": {
                            "type": "number",
                            "description": "Max results to return (default 5)."
                        }
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "get_approved_alternate_courses",
                "description": "Return structured list of approved alternate courses (outside CS) for the MS program parsed from the official CICS page.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional keyword filter (e.g., 'MATH', 'STAT', 'optimization')."
                        },
                        "limit": {
                            "type": "number",
                            "description": "Max number of entries to return (default 50)."
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force refresh of the source page before returning results (default false)."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_cics_faqs",
                "description": "Return structured MS Advising FAQs (question/answer pairs) parsed from the CICS site.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional keyword filter applied to question and answer."
                        },
                        "limit": {
                            "type": "number",
                            "description": "Max number of FAQ entries to return (default 20)."
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force refresh of the source page before returning results (default false)."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_cics_research_areas",
                "description": "Return structured list of CICS research areas with short descriptions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional keyword filter applied to area/title and description."
                        },
                        "limit": {
                            "type": "number",
                            "description": "Max number of research areas to return (default 20)."
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force refresh of the source page before returning results (default false)."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_cics_contacts",
                "description": "Return structured CICS contact information (address, phone, frequently contacted offices).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional keyword filter applied to office names and emails."
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force refresh of the source page before returning results (default false)."
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "get_cics_courses_index",
                "description": "Return structured links and sections from the CICS Courses page (schedule, descriptions, offering plan, overrides, etc.).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filter": {
                            "type": "string",
                            "description": "Optional keyword filter applied to link text."
                        },
                        "limit": {
                            "type": "number",
                            "description": "Max number of links to return (default 20)."
                        },
                        "force": {
                            "type": "boolean",
                            "description": "Force refresh of the source page before returning results (default false)."
                        }
                    },
                    "required": []
                }
            },
        ]

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool call"""
        if tool_name == "get_study_spots":
            return self.get_study_spots(
                arguments.get("location"),
                arguments.get("noise_preference"),
                arguments.get("group_size"),
            )
        elif tool_name == "get_dining_options":
            return self.get_dining_options(
                arguments.get("time_now"),
                arguments.get("dietary_pref"),
            )
        elif tool_name == "scrape_dining_info":
            return self.scrape_dining_info(
                arguments.get("query"),
                arguments.get("dietary_pref"),
                arguments.get("time_now"),
                arguments.get("limit"),
            )
        elif tool_name == "scrape_dining_menu":
            return self.scrape_dining_menu(
                arguments.get("hall"),
                arguments.get("meal"),
                arguments.get("limit_halls"),
                arguments.get("limit_categories"),
                arguments.get("limit_items"),
            )
        elif tool_name == "get_support_resources":
            return self.get_support_resources(arguments.get("topic"))
        elif tool_name == "get_bus_schedule":
            return self.get_bus_schedule(
                arguments.get("origin"),
                arguments.get("destination"),
            )
        elif tool_name == "get_course_info":
            return self.get_course_info(
                arguments.get("course_code"),
                arguments.get("info_type"),
            )
        elif tool_name == "get_facility_info":
            return self.get_facility_info(
                arguments.get("facility_name"),
                arguments.get("info_type"),
            )
        elif tool_name == "report_facility_issue":
            return self.report_facility_issue(
                arguments.get("facility_name"),
                arguments.get("issue_type"),
                arguments.get("description"),
            )
        elif tool_name == "get_current_time_est":
            return self.get_current_time_est(
                arguments.get("format"),
                arguments.get("include_seconds"),
            )
        elif tool_name == "refresh_cics_pages":
            return self.refresh_cics_pages(
                arguments.get("urls"),
                arguments.get("force"),
                arguments.get("cache_hours"),
            )
        elif tool_name == "search_cics_pages":
            return self.search_cics_pages(
                arguments.get("query"),
                arguments.get("limit"),
            )
        elif tool_name == "get_approved_alternate_courses":
            return self.get_approved_alternate_courses(
                arguments.get("filter"),
                arguments.get("limit"),
                arguments.get("force"),
            )
        elif tool_name == "get_cics_faqs":
            return self.get_cics_faqs(
                arguments.get("filter"),
                arguments.get("limit"),
                arguments.get("force"),
            )
        elif tool_name == "get_cics_research_areas":
            return self.get_cics_research_areas(
                arguments.get("filter"),
                arguments.get("limit"),
                arguments.get("force"),
            )
        elif tool_name == "get_cics_contacts":
            return self.get_cics_contacts(
                arguments.get("filter"),
                arguments.get("force"),
            )
        elif tool_name == "get_cics_courses_index":
            return self.get_cics_courses_index(
                arguments.get("filter"),
                arguments.get("limit"),
                arguments.get("force"),
            )
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def get_study_spots(
        self,
        location: Optional[str] = None,
        noise_preference: Optional[str] = None,
        group_size: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find study spots matching criteria"""
        results = self.study_spaces.copy()

        # Filter by location
        if location:
            location_lower = location.lower()
            results = [
                s
                for s in results
                if location_lower in s.get("location", "").lower()
                or location_lower in s.get("name", "").lower()
            ]

        # Filter by noise preference
        if noise_preference:
            np_lower = noise_preference.lower()
            results = [
                s
                for s in results
                if s.get("type", "").lower() == np_lower
                or (np_lower == "quiet" and s.get("type", "").lower() in ["quiet", "silent"])
                or (
                    np_lower == "collaborative"
                    and s.get("type", "").lower() in ["collaborative", "moderate"]
                )
            ]

        # Filter by group size
        if group_size:
            results = [
                s
                for s in results
                if group_size in s.get("group_size", "")
                or (group_size == "1" and "1" in s.get("group_size", ""))
                or (
                    group_size in ["2-3", "4-6", "7+"]
                    and group_size in s.get("group_size", "")
                )
            ]

        # Limit results
        results = results[:5]

        return {
            "results": results,
            "count": len(results),
            "recommendation": f"Found {len(results)} study spots matching your criteria.",
        }

    def get_dining_options(
        self,
        time_now: Optional[str] = None,
        dietary_pref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find dining options"""
        if time_now == "now" or not time_now:
            now_et = datetime.now(ZoneInfo("America/New_York"))
            current_hour = now_et.hour
            current_minute = now_et.minute
            time_now = f"{current_hour:02d}:{current_minute:02d}"

        results = []
        for option in self.dining_options:
            # Check if open
            hours = option.get("hours", {})
            if hours:
                open_time = hours.get("open", "")
                close_time = hours.get("close", "")

                # Simple time check placeholder: right now, we just accept if times exist
                if open_time and close_time:
                    results.append(option)
            else:
                results.append(option)

        # Filter by dietary preference
        if dietary_pref:
            dietary_lower = dietary_pref.lower()
            results = [
                d
                for d in results
                if dietary_lower == "none"
                or dietary_lower
                in [p.lower() for p in d.get("dietary_options", [])]
            ]

        results = results[:5]

        return {
            "results": results,
            "count": len(results),
            "current_time": time_now,
            "recommendation": f"Found {len(results)} dining options open now.",
        }

    def scrape_dining_info(
        self,
        query: Optional[str] = None,
        dietary_pref: Optional[str] = None,
        time_now: Optional[str] = None,
        limit: Optional[int] = 5,
    ) -> Dict[str, Any]:
        """
        Scrape live dining information starting from the configured base URL.
        Falls back to cache within the last N hours.
        """
        base_url = os.getenv("DINING_BASE_URL") or "https://umassdining.com/locations-menus"

        # Get cached or live-scraped data
        scraped: List[Dict[str, Any]] = get_dining_data_cached(
            base_url=base_url,
            cache_hours=6,
            data_dir=self.data_dir,
        )

        results = scraped

        # Filter by query (search in name, description, category)
        if query:
            q = query.lower()
            results = [
                v
                for v in results
                if q in (v.get("name") or "").lower()
                or q in (v.get("description") or "").lower()
                or q in (v.get("category") or "").lower()
            ]

        # Filter by dietary preference if provided
        if dietary_pref and dietary_pref.lower() != "none":
            dp = dietary_pref.lower()
            results = [
                v
                for v in results
                if dp in [o.lower() for o in (v.get("dietary_options") or [])]
            ]

        # Heuristic for time-based filtering: if 'late' or 'now' requested, prefer entries with hours text
        if time_now == "now" or (isinstance(time_now, str) and time_now):
            results = [v for v in results if v.get("hours_text")]

        # Update in-memory options for reuse by get_dining_options
        try:
            self.dining_options = scraped
        except Exception:
            pass

        # Limit results
        max_items = int(limit) if isinstance(limit, (int, float)) else 5
        results = results[:max_items]

        return {
            "results": results,
            "count": len(results),
            "source": base_url,
            "note": "Live-scraped with caching (6h). Hours parsed heuristically.",
        }

    def scrape_dining_menu(
        self,
        hall: Optional[str] = None,
        meal: Optional[str] = None,
        limit_halls: Optional[int] = 3,
        limit_categories: Optional[int] = 8,
        limit_items: Optional[int] = 20,
    ) -> Dict[str, Any]:
        """
        Scrape Worcester-style menu pages for dining halls and filter the result.
        """
        base_url = os.getenv("DINING_BASE_URL") or "https://umassdining.com/locations-menus"
        menus: List[Dict[str, Any]] = get_dining_menus_cached(
            base_url=base_url,
            cache_hours=3,
            data_dir=self.data_dir,
        )

        # Filter by hall substring if provided
        if hall:
            hq = hall.lower()
            menus = [m for m in menus if hq in (m.get("hall") or "").lower()]

        # Apply hall limit
        max_h = int(limit_halls) if isinstance(limit_halls, (int, float)) else 3
        menus = menus[:max_h]

        # Filter meals/categories/items and apply limits
        def trim_menu(m: Dict[str, Any]) -> Dict[str, Any]:
            out = {
                "hall": m.get("hall"),
                "url": m.get("url"),
                "date_text": m.get("date_text"),
                "meals": {},
            }
            meals_obj = m.get("meals") or {}

            # If a specific meal requested, only include that
            meal_keys = [meal] if meal and meal in meals_obj else list(meals_obj.keys())

            max_c = int(limit_categories) if isinstance(limit_categories, (int, float)) else 8
            max_i = int(limit_items) if isinstance(limit_items, (int, float)) else 20

            for mk in meal_keys:
                cats = meals_obj.get(mk) or {}
                # Keep a stable order
                cat_items = list(cats.items())[:max_c]
                trimmed_cats = {}
                for cname, items in cat_items:
                    trimmed_cats[cname] = list(items)[:max_i] if isinstance(items, list) else []
                if trimmed_cats:
                    out["meals"][mk] = trimmed_cats
            return out

        trimmed = [trim_menu(m) for m in menus]
        # Remove any halls that ended up with no meals after filtering
        trimmed = [m for m in trimmed if m.get("meals")]

        return {
            "results": trimmed,
            "count": len(trimmed),
            "source": base_url,
            "note": "Menus scraped and cached (3h). Structure follows Worcester-style layout.",
        }

    def get_support_resources(self, topic: Optional[str] = None) -> Dict[str, Any]:
        """Find support resources"""
        if not topic:
            topic = "general"

        topic_lower = topic.lower()
        results = [
            r
            for r in self.resources
            if topic_lower in r.get("category", "").lower()
            or topic_lower == "general"
            or topic_lower in [c.lower() for c in r.get("tags", [])]
        ]

        results = results[:5]

        return {
            "results": results,
            "count": len(results),
            "recommendation": f"Found {len(results)} resources for {topic}.",
        }

    def get_bus_schedule(
        self,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get bus schedule information"""
        results = []

        for schedule in self.bus_schedules:
            if origin and destination:
                if (
                    origin.lower() in schedule.get("route", "").lower()
                    or origin.lower() in schedule.get("stops", [])
                ) and (
                    destination.lower() in schedule.get("route", "").lower()
                    or destination.lower() in schedule.get("stops", [])
                ):
                    results.append(schedule)
            elif origin:
                if origin.lower() in schedule.get("route", "").lower() or origin.lower() in [
                    s.lower() for s in schedule.get("stops", [])
                ]:
                    results.append(schedule)
            else:
                results.append(schedule)

        results = results[:3]

        return {
            "results": results,
            "count": len(results),
            "recommendation": f"Found {len(results)} bus routes.",
        }

    def get_course_info(
        self,
        course_code: Optional[str] = None,
        info_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get course information by searching cached CICS pages.
        Falls back to refreshing the cache if needed.
        """
        # Build a query string from provided parts
        parts = []
        if course_code:
            parts.append(str(course_code))
        if info_type:
            parts.append(str(info_type))
        query = " ".join(parts).strip() or "CICS courses"

        # Special-case: direct ask for approved alternate courses
        q_lower = query.lower()
        if any(k in q_lower for k in [
            "approved alternate",
            "outside of computer science",
            "outside computer science",
            "non-cs courses",
            "non cs courses",
            "approved umass amherst courses outside",
            "approved courses outside cs",
        ]):
            return self.get_approved_alternate_courses(filter=None, limit=100, force=False)

        # Ensure cache is present; if not, load it
        if not getattr(self, "cics_pages", None):
            try:
                self.cics_pages = get_cics_pages_cached(
                    urls=DEFAULT_CICS_URLS,
                    cache_hours=24,
                    data_dir=self.data_dir,
                    force=False,
                )
            except Exception:
                self.cics_pages = []

        # Search cached pages
        result = search_cics_pages_cached(
            query=query,
            data_dir=self.data_dir,
            limit=5,
        )

        # If nothing found, try a forced refresh and search again
        if not result.get("results"):
            try:
                self.cics_pages = get_cics_pages_cached(
                    urls=DEFAULT_CICS_URLS,
                    cache_hours=24,
                    data_dir=self.data_dir,
                    force=True,
                )
                result = search_cics_pages_cached(
                    query=query,
                    data_dir=self.data_dir,
                    limit=5,
                )
            except Exception as e:
                return {
                    "message": "Unable to fetch course information at this time.",
                    "error": str(e),
                    "query": query,
                }

        # Attach original query for context
        result["query"] = query
        return result

    def get_approved_alternate_courses(
        self,
        filter: Optional[str] = None,
        limit: Optional[int] = 50,
        force: Optional[bool] = False,
    ) -> Dict[str, Any]:
        """
        Return structured list of approved alternate courses parsed from CICS page.
        Supports optional keyword filtering and limiting.
        """
        data = get_approved_alternate_courses_cached(
            data_dir=self.data_dir,
            force=bool(force),
        )
        items = data.get("results", [])
        if filter and isinstance(filter, str) and filter.strip():
            q = filter.strip().lower()
            def matches(entry: Dict[str, Any]) -> bool:
                hay = " ".join([
                    str(entry.get("department") or ""),
                    str(entry.get("course_number") or ""),
                    str(entry.get("course_code") or ""),
                    str(entry.get("title_or_notes") or ""),
                    str(entry.get("raw") or ""),
                ]).lower()
                return q in hay
            items = [e for e in items if matches(e)]

        max_n = int(limit) if isinstance(limit, (int, float)) else 50
        items = items[:max_n]

        return {
            "source_url": data.get("source_url"),
            "count": len(items),
            "results": items,
            "note": "Structured extraction of approved alternate courses (heuristic).",
        }

    def get_facility_info(
        self,
        facility_name: Optional[str] = None,
        info_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get facility information (placeholder)"""
        # This would integrate with facility management system
        return {
            "message": f"Facility information for {facility_name} is being retrieved.",
            "suggestion": "Please check the UMass facilities website or contact facilities directly.",
            "info_type": info_type,
        }

    def report_facility_issue(
        self,
        facility_name: Optional[str] = None,
        issue_type: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Report a facility issue (placeholder)"""
        # This would integrate with work order system
        return {
            "message": f"Your report about {facility_name} has been logged.",
            "next_steps": "Please also report this to Facilities Services at (413) 545-6401 or facilities@umass.edu",
            "issue_type": issue_type,
            "description": description,
        }

    def get_current_time_est(
        self,
        format: Optional[str] = None,
        include_seconds: Optional[bool] = False,
    ) -> Dict[str, Any]:
        """
        Get the current time in the UMass Amherst timezone (America/New_York).
        Returns multiple formatted representations and timezone metadata.
        """
        tz = ZoneInfo("America/New_York")
        now_et = datetime.now(tz)

        def fmt_offset(dt: datetime) -> str:
            offset = dt.utcoffset()
            if offset is None:
                return "+00:00"
            total_seconds = int(offset.total_seconds())
            sign = "+" if total_seconds >= 0 else "-"
            total_seconds = abs(total_seconds)
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{sign}{hours:02d}:{minutes:02d}"

        time_fmt = "%H:%M:%S" if include_seconds else "%H:%M"
        time_12_fmt = "%I:%M:%S %p" if include_seconds else "%I:%M %p"

        payload: Dict[str, Any] = {
            "iso": now_et.isoformat(),
            "date": now_et.strftime("%Y-%m-%d"),
            "time_24h": now_et.strftime(time_fmt),
            "time_12h": now_et.strftime(time_12_fmt),
            "weekday": now_et.strftime("%A"),
            "tz_name": "America/New_York",
            "tz_abbreviation": now_et.tzname(),
            "utc_offset": fmt_offset(now_et),
            "unix_epoch": int(now_et.timestamp()),
            "human": now_et.strftime("%a %b %d, %Y %I:%M %p %Z"),
        }

        if format:
            key = format.lower()
            if key in payload:
                return {"format": key, "value": payload[key]}
            aliases = {
                "time": "time_24h",
                "time24": "time_24h",
                "time12": "time_12h",
                "tz": "tz_abbreviation",
            }
            if key in aliases and aliases[key] in payload:
                alias_key = aliases[key]
                return {"format": key, "value": payload[alias_key]}
            return {
                "error": f"Unknown format '{format}'. Available keys: {', '.join(sorted(payload.keys()))}",
                "available": sorted(payload.keys()),
            }

        return payload

    def refresh_cics_pages(
        self,
        urls: Optional[List[str]] = None,
        force: Optional[bool] = False,
        cache_hours: Optional[int] = 24,
    ) -> Dict[str, Any]:
        """
        Refresh or load cached CICS pages and keep them in memory for quick search.
        """
        # When not forcing, respect cache_hours. When forcing, this simply re-scrapes.
        records = get_cics_pages_cached(
            urls=urls or DEFAULT_CICS_URLS,
            cache_hours=int(cache_hours) if isinstance(cache_hours, (int, float)) else 24,
            data_dir=self.data_dir,
            force=bool(force),
        )
        # Update in-memory cache
        try:
            self.cics_pages = records
        except Exception:
            pass

        # Opportunistically (re)build structured caches for model-friendly consumption
        try:
            get_cics_faqs_cached(data_dir=self.data_dir, force=False)
            get_cics_research_areas_cached(data_dir=self.data_dir, force=False)
            get_cics_contacts_cached(data_dir=self.data_dir, force=False)
            get_cics_courses_index_cached(data_dir=self.data_dir, force=False)
        except Exception:
            # Non-fatal; search still works based on text index
            pass
        return {
            "message": "CICS pages refreshed",
            "count": len(records),
            "default_sources": DEFAULT_CICS_URLS,
        }

    def search_cics_pages(
        self,
        query: Optional[str],
        limit: Optional[int] = 5,
    ) -> Dict[str, Any]:
        """
        Search CICS cached pages. If cache missing, attempt to load it.
        """
        if not query or not isinstance(query, str) or not query.strip():
            return {"error": "Query cannot be empty."}

        # Try searching directly; if no cache, the helper returns with a note.
        result = search_cics_pages_cached(
            query=query,
            data_dir=self.data_dir,
            limit=int(limit) if isinstance(limit, (int, float)) else 5,
        )

        # Keep a small reference to last search results
        result["sources"] = ["Tool: search_cics_pages"]
        return result

    def get_cics_faqs(
        self,
        filter: Optional[str] = None,
        limit: Optional[int] = 20,
        force: Optional[bool] = False,
    ) -> Dict[str, Any]:
        data = get_cics_faqs_cached(data_dir=self.data_dir, force=bool(force))
        items = data.get("results", [])
        if filter and isinstance(filter, str) and filter.strip():
            q = filter.strip().lower()
            items = [
                it for it in items
                if q in (it.get("question", "").lower() + " " + it.get("answer", "").lower())
            ]
        max_n = int(limit) if isinstance(limit, (int, float)) else 20
        items = items[:max_n]
        return {"source_url": data.get("source_url"), "count": len(items), "results": items}

    def get_cics_research_areas(
        self,
        filter: Optional[str] = None,
        limit: Optional[int] = 20,
        force: Optional[bool] = False,
    ) -> Dict[str, Any]:
        data = get_cics_research_areas_cached(data_dir=self.data_dir, force=bool(force))
        items = data.get("results", [])
        if filter and isinstance(filter, str) and filter.strip():
            q = filter.strip().lower()
            items = [
                it for it in items
                if q in (it.get("area", "").lower() + " " + it.get("description", "").lower())
            ]
        max_n = int(limit) if isinstance(limit, (int, float)) else 20
        items = items[:max_n]
        return {"source_url": data.get("source_url"), "count": len(items), "results": items}

    def get_cics_contacts(
        self,
        filter: Optional[str] = None,
        force: Optional[bool] = False,
    ) -> Dict[str, Any]:
        data = get_cics_contacts_cached(data_dir=self.data_dir, force=bool(force))
        result = data.get("results", {})
        if not isinstance(result, dict):
            return {"source_url": data.get("source_url"), "results": result}

        offices = result.get("offices") or []
        if filter and isinstance(filter, str) and filter.strip():
            q = filter.strip().lower()
            offices = [
                o for o in offices
                if q in (o.get("office", "") or "").lower() or q in (o.get("email", "") or "").lower()
            ]
        trimmed = {
            "address": result.get("address"),
            "main_phone": result.get("main_phone"),
            "dean": result.get("dean"),
            "offices": offices,
        }
        return {"source_url": data.get("source_url"), "count": len(offices), "results": trimmed}

    def get_cics_courses_index(
        self,
        filter: Optional[str] = None,
        limit: Optional[int] = 20,
        force: Optional[bool] = False,
    ) -> Dict[str, Any]:
        data = get_cics_courses_index_cached(data_dir=self.data_dir, force=bool(force))
        index = data.get("results", {}) or {}
        links = index.get("links", []) if isinstance(index, dict) else []
        if filter and isinstance(filter, str) and filter.strip():
            q = filter.strip().lower()
            links = [l for l in links if q in (l.get("text", "") or "").lower()]
        max_n = int(limit) if isinstance(limit, (int, float)) else 20
        links = links[:max_n]
        return {"source_url": data.get("source_url"), "count": len(links), "results": {"links": links}}
