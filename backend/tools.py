"""
Tool Registry for UMass Campus Agent
Implements various tools that the LangGraph agent can call
"""
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from dining_scraper import get_dining_data_cached, get_dining_menus_cached

from dining_scraper import DiningScraper
from course_scraper import CourseScraper
from bus_schedule_parser import BusScheduleParser


class ToolRegistry:
    """Registry for all available tools"""

    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.dining_scraper = DiningScraper(cache_dir=self.data_dir / "cache")
        self.course_scraper = CourseScraper(cache_dir=self.data_dir / "cache")
        self.bus_schedule_parser = BusScheduleParser(cache_dir=self.data_dir / "cache")
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

        # Dining hall general information
        dining_path = self.data_dir / "dining.json"
        if dining_path.exists():
            with open(dining_path, "r") as f:
                self.dining_info = json.load(f)
        else:
            self.dining_info = []

        # Courses - Load from cache/JSON file only (no web requests on startup)
        self.courses = []
        self.courses_by_code = {}
        
        # First, try to load from cache files directly (no web requests)
        try:
            fall_cache_path = self.course_scraper._get_cache_path("Fall 2025")
            spring_cache_path = self.course_scraper._get_cache_path("Spring 2026")
            
            cached_courses = []
            
            # Load Fall 2025 from cache if valid
            fall_courses = self.course_scraper._load_cache(fall_cache_path)
            if fall_courses:
                cached_courses.extend(fall_courses)
            
            # Load Spring 2026 from cache if valid
            spring_courses = self.course_scraper._load_cache(spring_cache_path)
            if spring_courses:
                cached_courses.extend(spring_courses)
            
            # If cache has courses, use them
            if cached_courses:
                # Build lookup by course code
                courses_by_code = {}
                for course in cached_courses:
                    code = course.get("course_code", "")
                    if code:
                        if code not in courses_by_code:
                            courses_by_code[code] = []
                        courses_by_code[code].append(course)
                
                self.courses = cached_courses
                self.courses_by_code = courses_by_code
        except Exception as e:
            # Silently fail and fall back to JSON
            pass
        
        # Fallback to JSON file if cache is empty or failed
        if not self.courses:
            courses_path = self.data_dir / "courses.json"
            if courses_path.exists():
                try:
                    with open(courses_path, "r") as f:
                        courses_data = json.load(f)
                        self.courses = courses_data.get("courses", [])
                        self.courses_by_code = courses_data.get("courses_by_code", {})
                        
                        # Populate cache from JSON for future use (silently)
                        if self.courses:
                            try:
                                self._populate_course_cache(self.courses)
                            except Exception:
                                pass
                except Exception:
                    self.courses = []
                    self.courses_by_code = {}
    
    def _populate_course_cache(self, courses: List[Dict[str, Any]]):
        """Populate course cache files from course data"""
        # Group courses by semester
        courses_by_semester = {}
        for course in courses:
            semester = course.get("semester", "")
            if semester:
                if semester not in courses_by_semester:
                    courses_by_semester[semester] = []
                courses_by_semester[semester].append(course)
        
        # Save each semester to its cache file
        for semester, semester_courses in courses_by_semester.items():
            cache_path = self.course_scraper._get_cache_path(semester)
            self.course_scraper._save_cache(cache_path, semester_courses)

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
                "description": "Find dining options on campus based on current time and dietary preferences. Use dining_type='Grab N Go' to get only Grab N Go menus, or 'Dining Hall' for regular dining halls. Use location to filter by specific dining hall (e.g., 'Franklin', 'Berkshire', 'Worcester', 'Hampshire').",
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
                        "dining_type": {
                            "type": "string",
                            "description": "Type of dining: 'Dining Hall', 'Grab N Go', or leave empty for all",
                            "enum": ["Dining Hall", "Grab N Go", ""],
                        },
                        "location": {
                            "type": "string",
                            "description": "Filter by specific location: 'Franklin', 'Berkshire', 'Worcester', 'Hampshire'",
                        },
                    },
                    "required": [],
                },
            },
            {
                "name": "search_food_items",
                "description": "Search for specific food items or food types (e.g., sandwiches, burgers, vegetarian options, meat dishes) across dining halls. Can filter by location and meal period.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "food_type": {
                            "type": "string",
                            "description": "Type of food to search for (e.g., 'sandwich', 'burger', 'pizza', 'vegetarian', 'vegan', 'meat', 'chicken', 'soup', 'salad', 'pasta')",
                        },
                        "location": {
                            "type": "string",
                            "description": "Filter by specific dining hall: 'Franklin', 'Berkshire', 'Worcester', 'Hampshire', or leave empty for all",
                        },
                        "meal_period": {
                            "type": "string",
                            "description": "Filter by meal period: 'breakfast', 'lunch', 'dinner', 'late_night', or leave empty for all",
                        },
                    },
                    "required": ["food_type"],
                },
            },
            {
                "name": "get_dining_hall_info",
                "description": "Get general information about a dining hall including hours, location, features, manager contact, and other details. Use this when users ask about dining hall hours, location, features, or general information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dining_hall": {
                            "type": "string",
                            "description": "Name of the dining hall: 'Franklin', 'Berkshire', 'Worcester', 'Hampshire'",
                        },
                    },
                    "required": ["dining_hall"],
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
                "description": "Get PVTA bus schedule information for UMass Amherst. USE THIS TOOL when users ask about bus routes (e.g., 'route 31', 'bus 30', 'what is route B43'), bus schedules, next bus times, or bus stops. The tool downloads and parses actual PDF schedules from configured URLs. Uses EST timezone.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "route_number": {
                            "type": "string",
                            "description": "Bus route number (e.g., '30', '31', 'B43', '35'). EXTRACT THIS FROM THE USER'S QUERY - if they mention a route number, you MUST provide it here.",
                        },
                        "origin": {
                            "type": "string",
                            "description": "Starting location (e.g., 'Campus Center', 'Puffton', 'North Village')",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Destination location",
                        },
                        "stop": {
                            "type": "string",
                            "description": "Specific stop name to get next bus times",
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
                arguments.get("dining_type"),
                arguments.get("location"),
            )
        elif tool_name == "search_food_items":
            return self.search_food_items(
                arguments.get("food_type"),
                arguments.get("location"),
                arguments.get("meal_period"),
            )
        elif tool_name == "get_dining_hall_info":
            return self.get_dining_hall_info(
                arguments.get("dining_hall"),
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
                route_number=arguments.get("route_number"),
                origin=arguments.get("origin"),
                destination=arguments.get("destination"),
                stop=arguments.get("stop"),
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

    def _get_dining_info(self, dining_name: str) -> Optional[Dict[str, Any]]:
        """Get general information for a dining hall by name"""
        dining_name_lower = dining_name.lower()
        for info in self.dining_info:
            info_name_lower = info.get("name", "").lower()
            # Check if names match (e.g., "Worcester Commons" matches "Worcester")
            if dining_name_lower in info_name_lower or info_name_lower in dining_name_lower:
                return info
        return None

    def get_dining_options(
        self,
        time_now: Optional[str] = None,
        dietary_pref: Optional[str] = None,
        dining_type: Optional[str] = None,
        location: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find dining options using live web scraping"""
        if time_now == "now" or not time_now:
            current_hour = datetime.now().hour
            current_minute = datetime.now().minute
            time_now = f"{current_hour:02d}:{current_minute:02d}"
            current_hour_int = current_hour
        else:
            # Parse time string (HH:MM format)
            try:
                if ':' in time_now:
                    hour_str, minute_str = time_now.split(':')
                    current_hour_int = int(hour_str)
                else:
                    current_hour_int = datetime.now().hour
            except (ValueError, AttributeError):
                current_hour_int = datetime.now().hour

        # Determine current meal period based on time
        meal_period = None
        if 7 <= current_hour_int < 11:
            meal_period = "breakfast"
        elif 11 <= current_hour_int < 15:
            meal_period = "lunch"
        elif 15 <= current_hour_int < 21:
            meal_period = "dinner"
        elif 21 <= current_hour_int < 24 or 0 <= current_hour_int < 2:
            meal_period = "late_night"

        # Get all dining options from scraper
        try:
            all_options = self.dining_scraper.get_all_dining_options(
                meal_period=meal_period,
                dietary_pref=dietary_pref,
                dining_type=dining_type,
                location=location
            )
        except Exception as e:
            # Fallback to empty list if scraping fails
            print(f"Warning: Failed to scrape dining data: {e}")
            all_options = []

        # Format results to match expected structure
        results = []
        grab_n_go_unavailable = []
        
        for option in all_options:
            # Filter by location if specified
            if location:
                option_location = option.get("location", "").lower()
                location_lower = location.lower()
                # Check if location matches (e.g., "franklin" matches "Franklin Commons")
                if location_lower not in option_location and option_location not in location_lower:
                    continue
            
            # Get general information for this dining hall
            dining_name = option.get("name", "")
            general_info = self._get_dining_info(dining_name)
            
            formatted_option = {
                "name": option.get("name", ""),
                "location": option.get("location", ""),
                "type": option.get("type", ""),
                "hours": option.get("hours", {}),
                "dietary_options": option.get("dietary_options", []),
                "late_night": option.get("late_night", False),
            }
            
            # Merge general information if available
            if general_info:
                formatted_option["address"] = general_info.get("address", "")
                formatted_option["description"] = general_info.get("description", "")
                formatted_option["features"] = general_info.get("features", [])
                formatted_option["manager"] = general_info.get("manager", {})
                formatted_option["payment_methods"] = general_info.get("payment_methods", [])
                # Merge hours if not already present
                if not formatted_option.get("hours") and general_info.get("hours"):
                    formatted_option["hours"] = general_info["hours"]
                # Merge late_night info
                if general_info.get("late_night"):
                    formatted_option["late_night"] = True
                    formatted_option["late_night_hours"] = general_info.get("late_night_hours", "")
                # Merge kosher info for Franklin
                if general_info.get("kosher_dining"):
                    formatted_option["kosher_dining"] = True
                    formatted_option["kosher_hours"] = general_info.get("hours", {}).get("kosher", {})
            
            # Add all meals data for dining halls
            if option.get("type") == "Dining Hall" and "meals" in option:
                formatted_option["meals"] = option["meals"]
                # Add current meal items if available
                if meal_period and meal_period in option.get("meals", {}):
                    formatted_option["current_meal"] = meal_period
                    formatted_option["current_meal_items"] = option["meals"][meal_period]
                # If no current meal period, show all available meals summary
                elif not meal_period:
                    meals_summary = {}
                    for meal_type, items in option.get("meals", {}).items():
                        if items:
                            meals_summary[meal_type] = len(items)
                    formatted_option["available_meals"] = meals_summary
            
            # Add all items for Grab 'N Go
            if option.get("type") == "Grab 'N Go":
                if "items" in option and len(option["items"]) > 0:
                    formatted_option["items"] = option["items"]
                else:
                    # Grab 'N Go is unavailable (closed or no items)
                    formatted_option["unavailable"] = True
                    formatted_option["unavailable_reason"] = "This Grab 'N Go location is currently closed or has no menu available for this date."
                    grab_n_go_unavailable.append(option.get("name", "Unknown"))
            
            results.append(formatted_option)

        # Limit results
        results = results[:10]
        
        # Build recommendation message
        if dining_type and "Grab N Go" in dining_type:
            if len(results) == 0:
                recommendation = "No Grab 'N Go locations found."
            elif all(r.get("unavailable", False) for r in results):
                recommendation = f"All Grab 'N Go locations are currently unavailable. Locations checked: {', '.join(grab_n_go_unavailable)}"
            elif any(r.get("unavailable", False) for r in results):
                available = [r["name"] for r in results if not r.get("unavailable", False)]
                unavailable = [r["name"] for r in results if r.get("unavailable", False)]
                recommendation = f"Found {len(available)} available Grab 'N Go location(s): {', '.join(available)}. Unavailable: {', '.join(unavailable)}"
            else:
                recommendation = f"Found {len(results)} Grab 'N Go location(s) with menu available."
        else:
            recommendation = f"Found {len(results)} dining options. Current meal period: {meal_period or 'unknown'}"

        return {
            "results": results,
            "count": len(results),
            "current_time": time_now,
            "meal_period": meal_period,
            "recommendation": recommendation,
        }

    def search_food_items(
        self,
        food_type: str,
        location: Optional[str] = None,
        meal_period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Search for food items by type across dining halls"""
        food_type_lower = food_type.lower()
        
        # Define food type keywords and their matching patterns
        food_patterns = {
            'sandwich': ['sandwich', 'sub', 'wrap', 'panini', 'hoagie'],
            'burger': ['burger', 'patty'],
            'pizza': ['pizza'],
            'vegetarian': ['vegetarian', 'veg'],  # Will also check dietary tags
            'vegan': ['vegan', 'plant based', 'plant-based'],
            'meat': ['chicken', 'beef', 'pork', 'turkey', 'meat', 'sausage', 'bacon', 'ham', 'steak', 'kielbasa', 'chorizo', 'chourico'],
            'chicken': ['chicken'],
            'beef': ['beef', 'burger', 'steak', 'meatloaf'],
            'pork': ['pork', 'bacon', 'ham', 'sausage', 'kielbasa', 'chorizo', 'chourico'],
            'soup': ['soup', 'chowder', 'bisque', 'broth'],
            'salad': ['salad'],
            'pasta': ['pasta', 'spaghetti', 'ziti', 'penne', 'noodles', 'ramen'],
            'rice': ['rice', 'fried rice', 'jasmine rice'],
            'fish': ['fish', 'salmon', 'tuna', 'seafood', 'clam', 'shrimp'],
            'vegetables': ['vegetable', 'veggie', 'broccoli', 'carrot', 'spinach', 'kale', 'collard'],
            'dessert': ['dessert', 'cake', 'brownie', 'cookie', 'pie', 'ice cream', 'tiramisu'],
            'breakfast': ['waffle', 'pancake', 'french toast', 'omelet', 'egg', 'oatmeal', 'cereal'],
        }
        
        # Find matching patterns for the food type
        search_keywords = []
        for key, patterns in food_patterns.items():
            if key in food_type_lower or any(p in food_type_lower for p in patterns):
                search_keywords.extend(patterns)
                # Add the key itself
                if key not in search_keywords:
                    search_keywords.append(key)
        
        # If no specific pattern found, use the food_type itself as keyword
        if not search_keywords:
            search_keywords = [food_type_lower]
        
        # Get all dining options
        try:
            all_options = self.dining_scraper.get_all_dining_options(
                meal_period=meal_period,
                dining_type="Dining Hall",
                location=location
            )
        except Exception as e:
            print(f"Warning: Failed to get dining data: {e}")
            all_options = []
        
        matching_items = []
        
        for option in all_options:
            option_name = option.get("name", "")
            option_location = option.get("location", "")
            
            # Search through all meals
            meals = option.get("meals", {})
            for meal_type, items in meals.items():
                # Skip if meal_period filter is specified
                if meal_period and meal_type != meal_period:
                    continue
                
                for item in items:
                    item_name = item.get("name", "").lower()
                    item_dietary = [d.lower() for d in item.get("dietary", [])]
                    station = item.get("station", "")
                    
                    # Check if item matches search keywords
                    matches = False
                    match_reason = []
                    
                    # Check item name
                    for keyword in search_keywords:
                        if keyword in item_name:
                            matches = True
                            match_reason.append(f"contains '{keyword}'")
                            break
                    
                    # Check dietary tags for vegetarian/vegan
                    if 'vegetarian' in food_type_lower or ('veg' in food_type_lower and 'veggie' not in food_type_lower):
                        # Check dietary tags
                        if 'vegetarian' in item_dietary or 'vegan' in item_dietary:
                            matches = True
                            match_reason.append("marked as vegetarian/vegan")
                        # Also check item name for vegetarian indicators
                        veg_indicators = ['vegetable', 'veggie', 'tofu', 'bean', 'quinoa', 'plant based', 'plant-based', 'kelp']
                        if any(indicator in item_name for indicator in veg_indicators):
                            # Exclude if it contains meat words
                            meat_words_in_name = ['chicken', 'beef', 'pork', 'turkey', 'meat', 'sausage', 'bacon', 'ham', 'steak', 'fish', 'salmon', 'tuna', 'clam', 'shrimp']
                            if not any(meat_word in item_name for meat_word in meat_words_in_name):
                                matches = True
                                match_reason.append("appears to be vegetarian")
                    elif 'vegan' in food_type_lower:
                        if 'vegan' in item_dietary:
                            matches = True
                            match_reason.append("marked as vegan")
                        # Check for vegan indicators in name
                        vegan_indicators = ['plant based', 'plant-based', 'kelp', 'tofu']
                        if any(indicator in item_name for indicator in vegan_indicators):
                            meat_words_in_name = ['chicken', 'beef', 'pork', 'turkey', 'meat', 'sausage', 'bacon', 'ham', 'steak', 'fish', 'salmon', 'tuna', 'clam', 'shrimp', 'egg', 'dairy', 'cheese', 'milk']
                            if not any(meat_word in item_name for meat_word in meat_words_in_name):
                                matches = True
                                match_reason.append("appears to be vegan")
                    
                    # For meat searches, exclude vegetarian/vegan items
                    if any(meat_word in food_type_lower for meat_word in ['meat', 'chicken', 'beef', 'pork']):
                        # Skip if marked as vegetarian/vegan
                        if 'vegetarian' in item_dietary or 'vegan' in item_dietary:
                            continue
                        # Skip vegetarian alternatives
                        veg_alternatives = ['bean', 'tofu', 'plant', 'kelp', 'black bean']
                        if any(alt in item_name for alt in veg_alternatives) and any(word in item_name for word in ['burger', 'patty', 'sausage', 'chicken', 'beef']):
                            continue
                    
                    if matches:
                        matching_items.append({
                            "name": item.get("name", ""),
                            "location": option_location,
                            "dining_hall": option_name,
                            "meal_period": meal_type,
                            "station": station,
                            "dietary": item.get("dietary", []),
                            "match_reason": ", ".join(match_reason) if match_reason else "matches search"
                        })
        
        # Group by location and meal period
        grouped_results = {}
        for item in matching_items:
            key = f"{item['location']}_{item['meal_period']}"
            if key not in grouped_results:
                grouped_results[key] = {
                    "location": item["location"],
                    "dining_hall": item["dining_hall"],
                    "meal_period": item["meal_period"],
                    "items": []
                }
            grouped_results[key]["items"].append({
                "name": item["name"],
                "station": item["station"],
                "dietary": item["dietary"]
            })
        
        results = list(grouped_results.values())
        
        return {
            "food_type": food_type,
            "search_keywords": search_keywords,
            "results": results,
            "total_matches": len(matching_items),
            "locations_found": len(set(item["location"] for item in matching_items)),
            "recommendation": f"Found {len(matching_items)} {food_type} items across {len(set(item['location'] for item in matching_items))} location(s)."
        }
    
    def get_dining_hall_info(self, dining_hall: str) -> Dict[str, Any]:
        """Get general information about a dining hall"""
        dining_hall_lower = dining_hall.lower()
        
        # Find matching dining hall info
        matching_info = None
        for info in self.dining_info:
            info_name_lower = info.get("name", "").lower()
            # Check if names match (e.g., "Franklin" matches "Franklin Dining Commons")
            if dining_hall_lower in info_name_lower or info_name_lower in dining_hall_lower:
                matching_info = info
                break
        
        if not matching_info:
            return {
                "results": [],
                "count": 0,
                "recommendation": f"No information found for {dining_hall}. Available dining halls: Franklin, Berkshire, Worcester, Hampshire."
            }
        
        return {
            "results": [matching_info],
            "count": 1,
            "recommendation": f"Found information for {matching_info.get('name', dining_hall)}."
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
        route_number: Optional[str] = None,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        stop: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get bus schedule information from PDF or fallback to JSON"""
        # Debug logging
        print(f"[DEBUG] get_bus_schedule called with: route_number={route_number}, origin={origin}, destination={destination}, stop={stop}")
        
        # If PDF URLs are configured, ALWAYS prioritize PDF parsing
        has_pdf_config = bool(self.bus_schedule_parser.pdf_urls)
        print(f"[DEBUG] PDF URLs configured: {has_pdf_config}, URLs: {list(self.bus_schedule_parser.pdf_urls.keys())}")
        
        # If route_number is provided and PDF URLs are configured, use PDF parser
        if route_number and has_pdf_config:
            # Check if route exists in PDF URLs
            route_in_config = route_number in self.bus_schedule_parser.pdf_urls
            
            if route_in_config or "_default" in self.bus_schedule_parser.pdf_urls:
                try:
                    # Parse PDF for this specific route
                    schedule_data = self.bus_schedule_parser.parse_pdf(
                        route_number=route_number if route_in_config else None,
                        use_cache=True
                    )
                    
                    # Check if we got valid schedule data
                    print(f"[DEBUG] Schedule data keys: {list(schedule_data.keys())}")
                    if "error" not in schedule_data:
                        schedules = schedule_data.get("schedules", {})
                        print(f"[DEBUG] Found {len(schedules)} routes in parsed data")
                        
                        # Convert schedules dict to list format with comprehensive data
                        pdf_routes = []
                        for route_num, route_data in schedules.items():
                            # Match the requested route number
                            if route_number.upper() in route_num.upper() or route_num.upper() in route_number.upper():
                                # Calculate total schedule times
                                schedule_times = route_data.get("schedule_times", {})
                                total_times = sum(
                                    len(v.get("times", [])) if isinstance(v, dict) else 0 
                                    for v in schedule_times.values()
                                )
                                
                                pdf_routes.append({
                                    "route_number": route_num,
                                    "route_name": route_data.get("route_name", f"Route {route_num}"),
                                    "stops": route_data.get("stops", []),
                                    "directions": route_data.get("directions", []),
                                    "days_of_operation": route_data.get("days_of_operation", []),
                                    "effective_date": route_data.get("effective_date", ""),
                                    "schedule_times": schedule_times,
                                    "total_schedule_times": total_times,
                                    "schedule_lines": route_data.get("schedule_lines", [])[:20],  # More schedule context
                                    "raw_text": route_data.get("raw_text", [])[:30]  # More context for AI
                                })
                        
                        print(f"[DEBUG] Matched {len(pdf_routes)} routes for route_number={route_number}")
                        
                        # If we found routes in PDF, use them
                        if pdf_routes:
                            print(f"[DEBUG] Returning PDF data with {len(pdf_routes)} routes")
                            # If stop is provided, get next bus times
                            if stop:
                                next_times = self.bus_schedule_parser.get_next_bus_times(
                                    route_number=route_number,
                                    stop=stop
                                )
                                
                                if "error" not in next_times:
                                    return {
                                        "results": pdf_routes,
                                        "next_times": next_times,
                                        "count": len(pdf_routes),
                                        "recommendation": (
                                            f"Found route {route_number} from PDF schedule. "
                                            f"Next buses at {stop}: {', '.join(next_times.get('next_times', [])[:3])}"
                                        ),
                                        "source": "PDF schedule"
                                    }
                            
                            return {
                                "results": pdf_routes,
                                "count": len(pdf_routes),
                                "recommendation": f"Found {len(pdf_routes)} route(s) matching '{route_number}' from PDF schedule.",
                                "source": "PDF schedule",
                                "schedule_info": pdf_routes[0].get("schedule_lines", [])[:5] if pdf_routes else []
                            }
                        else:
                            # PDF parsed but route not found - try find_route as fallback
                            print(f"[DEBUG] No routes matched in parsed data, trying find_route...")
                            pdf_routes = self.bus_schedule_parser.find_route(
                                route_number=route_number,
                                route_name=None
                            )
                            if pdf_routes:
                                print(f"[DEBUG] find_route found {len(pdf_routes)} routes")
                                return {
                                    "results": pdf_routes,
                                    "count": len(pdf_routes),
                                    "recommendation": f"Found {len(pdf_routes)} route(s) matching '{route_number}' from PDF schedule.",
                                    "source": "PDF schedule"
                                }
                            else:
                                # PDF parsed but route still not found
                                print(f"[WARNING] PDF parsed but route {route_number} not found in schedules")
                                # Return what we have anyway, or return error
                                if schedules:
                                    # Return all schedules found as fallback
                                    all_routes = []
                                    for route_num, route_data in schedules.items():
                                        all_routes.append({
                                            "route_number": route_num,
                                            "route_name": route_data.get("route_name", f"Route {route_num}"),
                                            "stops": route_data.get("stops", []),
                                            "raw_text": route_data.get("raw_text", [])[:20],
                                            "schedule_lines": route_data.get("schedule_lines", [])[:10]
                                        })
                                    return {
                                        "results": all_routes,
                                        "count": len(all_routes),
                                        "recommendation": f"Found {len(all_routes)} route(s) in PDF (requested route {route_number} not found, showing all available routes).",
                                        "source": "PDF schedule"
                                    }
                    else:
                        # PDF parsing failed - return error info but don't fall back to JSON
                        # Only use JSON if PDF URLs are NOT configured
                        error_msg = schedule_data.get("error", "Unknown error")
                        print(f"[ERROR] PDF parsing failed: {error_msg}")
                        return {
                            "results": [],
                            "count": 0,
                            "recommendation": f"Could not parse PDF schedule for route {route_number}: {error_msg}. Please ensure PyPDF2 or pdfplumber is installed: pip install PyPDF2 pdfplumber",
                            "source": "PDF schedule (error)",
                            "error": error_msg
                        }
                except Exception as e:
                    # Log error and return error response instead of falling back to JSON
                    import traceback
                    error_msg = str(e)
                    print(f"Error parsing PDF for route {route_number}: {error_msg}")
                    traceback.print_exc()
                    return {
                        "results": [],
                        "count": 0,
                        "recommendation": f"Error parsing PDF schedule for route {route_number}: {error_msg}",
                        "source": "PDF schedule (error)",
                        "error": error_msg
                    }
        
        # Fallback to JSON data ONLY if:
        # 1. PDF URLs are NOT configured, OR
        # 2. Query is by origin/destination (not route_number)
        # NEVER fall back to JSON if route_number is provided and PDF URLs are configured
        
        # If route_number was provided and PDF URLs are configured, we should have returned above
        # So if we reach here with route_number, it means PDF URLs are NOT configured
        if route_number and not has_pdf_config:
            # Route number query but no PDF config - use JSON
            results = []
            for schedule in self.bus_schedules:
                if route_number.lower() in schedule.get("route", "").lower():
                    results.append(schedule)
            
            results = results[:3]
            return {
                "results": results,
                "count": len(results),
                "recommendation": f"Found {len(results)} bus routes (using fallback data).",
                "source": "JSON fallback"
            }
        
        # Origin/destination queries - use JSON fallback
        results = []
        for schedule in self.bus_schedules:
            if origin and destination:
                if (
                    origin.lower() in schedule.get("route", "").lower()
                    or origin.lower() in [s.lower() for s in schedule.get("stops", [])]
                ) and (
                    destination.lower() in schedule.get("route", "").lower()
                    or destination.lower() in [s.lower() for s in schedule.get("stops", [])]
                ):
                    results.append(schedule)
            elif origin:
                if origin.lower() in schedule.get("route", "").lower() or origin.lower() in [
                    s.lower() for s in schedule.get("stops", [])
                ]:
                    results.append(schedule)
            else:
                # No specific query - return all
                results.append(schedule)

        results = results[:3]

        return {
            "results": results,
            "count": len(results),
            "recommendation": f"Found {len(results)} bus routes.",
            "source": "JSON fallback"
        }

    def get_course_info(
        self,
        course_code: Optional[str] = None,
        info_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get course information from the course knowledge base"""
        if not course_code:
            # Return all courses if no specific code provided
            return {
                "results": self.courses,
                "count": len(self.courses),
                "recommendation": f"Found {len(self.courses)} courses. Please specify a course code (e.g., 'CICS 110') for detailed information.",
            }
        
        # Normalize course code (handle variations like "CICS110", "CICS 110", "cics 110")
        course_code_normalized = re.sub(r'\s+', ' ', course_code.upper().strip())
        
        # Try exact match first
        matching_courses = self.courses_by_code.get(course_code_normalized, [])
        
        # If no exact match, try fuzzy matching
        if not matching_courses:
            # Try matching without spaces
            course_code_no_space = course_code_normalized.replace(' ', '')
            for code, courses in self.courses_by_code.items():
                if code.replace(' ', '') == course_code_no_space:
                    matching_courses = courses
                    break
        
        # If still no match, try partial matching
        if not matching_courses:
            for code, courses in self.courses_by_code.items():
                if course_code_normalized in code or code in course_code_normalized:
                    matching_courses = courses
                    break
        
        if not matching_courses:
            # Try searching in course titles and descriptions
            search_term = course_code_normalized.lower()
            for course in self.courses:
                if (search_term in course.get("course_code", "").lower() or
                    search_term in course.get("course_title", "").lower() or
                    search_term in course.get("description", "").lower()):
                    matching_courses.append(course)
        
        if not matching_courses:
            return {
                "results": [],
                "count": 0,
                "recommendation": (
                    f"No course found matching '{course_code}'. "
                    "Available courses include CICS 110, CICS 160, CICS 210, INFO 248, COMPSCI 240, etc. "
                    "Please check the course code and try again."
                ),
            }
        
        # Filter by info_type if specified
        results = []
        for course in matching_courses:
            if info_type:
                info_type_lower = info_type.lower()
                filtered_course = {"course_code": course.get("course_code"), "course_title": course.get("course_title")}
                
                if info_type_lower in ["content", "description", "details"]:
                    filtered_course["description"] = course.get("description", "")
                    filtered_course["instructors"] = course.get("instructors", [])
                    filtered_course["credits"] = course.get("credits")
                    filtered_course["semester"] = course.get("semester")
                elif info_type_lower in ["prerequisite", "prerequisites", "prereq"]:
                    filtered_course["prerequisites"] = course.get("prerequisites", "")
                elif info_type_lower in ["instructor", "instructors", "professor", "prof"]:
                    filtered_course["instructors"] = course.get("instructors", [])
                elif info_type_lower in ["schedule", "time", "meeting"]:
                    filtered_course["schedule"] = course.get("schedule")
                    filtered_course["semester"] = course.get("semester")
                else:
                    # Return all info if info_type not recognized
                    filtered_course = course
                
                results.append(filtered_course)
            else:
                # Return all course information
                results.append(course)
        
        # Remove duplicates based on course_code and semester
        seen = set()
        unique_results = []
        for course in results:
            key = (course.get("course_code"), course.get("semester"))
            if key not in seen:
                seen.add(key)
                unique_results.append(course)
        
        return {
            "results": unique_results,
            "count": len(unique_results),
            "recommendation": (
                f"Found {len(unique_results)} course(s) matching '{course_code}'. "
                f"{'Filtered by ' + info_type + '.' if info_type else 'Showing all available information.'}"
            ),
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
