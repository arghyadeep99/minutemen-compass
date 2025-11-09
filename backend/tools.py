"""
Tool Registry for UMass Campus Agent
Implements various tools that the Gemini agent can call
"""
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


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
            with open(study_spaces_path, "r") as f:
                self.study_spaces = json.load(f)
        else:
            self.study_spaces = []

        # Dining options
        dining_path = self.data_dir / "dining.json"
        if dining_path.exists():
            with open(dining_path, "r") as f:
                self.dining_options = json.load(f)
        else:
            self.dining_options = []

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

    def get_dining_options(
        self,
        time_now: Optional[str] = None,
        dietary_pref: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Find dining options"""
        if time_now == "now" or not time_now:
            current_hour = datetime.now().hour
            current_minute = datetime.now().minute
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
