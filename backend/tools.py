"""
Tool Registry for UMass Campus Agent
Implements various tools that the LangGraph agent can call
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

from dining_scraper import DiningScraper


class ToolRegistry:
    """Registry for all available tools"""

    def __init__(self):
        self.data_dir = Path("data")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.dining_scraper = DiningScraper(cache_dir=self.data_dir / "cache")
        self._load_data()

    def _load_data(self):
        """Load JSON data files"""
        # Study spaces
        study_spaces_path = self.data_dir / "study_spaces.json"
        if study_spaces_path.exists():
            with open(study_spaces_path, "r") as f:
                self.study_spaces = json.load(f)
        else:
            self.study_spaces = []

        # Resources
        resources_path = self.data_dir / "resources.json"
        if resources_path.exists():
            with open(resources_path, "r") as f:
                self.resources = json.load(f)
        else:
            self.resources = []

        # Bus schedules
        bus_path = self.data_dir / "bus_schedules.json"
        if bus_path.exists():
            with open(bus_path, "r") as f:
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
        """Get course information (placeholder)"""
        # This would integrate with UMass course catalog API
        return {
            "message": "Course information lookup is currently being set up.",
            "suggestion": (
                f"For information about {course_code}, please check SPIRE "
                "or contact the department directly."
            ),
            "info_type": info_type,
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
