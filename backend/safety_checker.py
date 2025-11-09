"""
Safety Checker for Minutemen Compass
Implements ethical guardrails to detect and handle unsafe requests
"""
from typing import Dict, List

class SafetyChecker:
    """Checks user queries for safety concerns and provides appropriate responses"""
    
    def __init__(self):
        # Keywords that might indicate unsafe content
        self.unsafe_keywords = {
            "self_harm": ["suicide", "kill myself", "end my life", "hurt myself", "self harm"],
            "harassment": ["harass", "bully", "threaten", "intimidate"],
            "academic_dishonesty": ["cheat", "plagiarize", "copy homework", "exam answers"],
            "violence": ["hurt someone", "attack", "violence", "weapon"]
        }
        
        # Safe response templates
        self.safe_responses = {
            "self_harm": """I'm concerned about what you've shared. Your wellbeing is important.

Please reach out to these UMass resources immediately:
• Counseling Center: (413) 545-2337 (24/7 crisis support)
• Emergency Services: 911 or UMass Police: (413) 545-2121
• Crisis Text Line: Text HOME to 741741

You're not alone, and there are people who want to help.""",
            
            "harassment": """I can't help with requests that involve harassment or harm to others.

If you're experiencing harassment or need to report an incident:
• Dean of Students Office: (413) 545-2684
• Title IX Office: (413) 545-3464
• UMass Police: (413) 545-2121

These offices can provide support and guide you through reporting options.""",
            
            "academic_dishonesty": """I can't assist with academic dishonesty, including cheating or plagiarism.

For academic support instead:
• Learning Resource Center: (413) 545-5334
• Writing Center: (413) 545-0610
• Your course instructor or TA

These resources can help you succeed academically through legitimate means.""",
            
            "violence": """I can't assist with anything involving violence or harm to others.

If you're in immediate danger, call 911 or UMass Police: (413) 545-2121

For non-emergency concerns:
• Dean of Students Office: (413) 545-2684
• Counseling Center: (413) 545-2337"""
        }
    
    def check(self, user_query: str) -> Dict[str, any]:
        """
        Check if a user query is unsafe
        
        Returns:
            Dictionary with 'is_unsafe' boolean and 'response' string
        """
        query_lower = user_query.lower()
        
        # Check for unsafe keywords
        for category, keywords in self.unsafe_keywords.items():
            for keyword in keywords:
                if keyword in query_lower:
                    return {
                        "is_unsafe": True,
                        "category": category,
                        "response": self.safe_responses.get(category, self._default_safe_response())
                    }
        
        # Additional context-based checks
        if self._context_check_unsafe(query_lower):
            return {
                "is_unsafe": True,
                "category": "general",
                "response": self._default_safe_response()
            }
        
        return {
            "is_unsafe": False,
            "category": None,
            "response": ""
        }
    
    def _context_check_unsafe(self, query_lower: str) -> bool:
        """Additional context-based safety checks"""
        # Check for patterns that might indicate unsafe intent
        unsafe_patterns = [
            "how to harm",
            "how to hurt",
            "ways to cheat",
            "how to get away with"
        ]
        
        for pattern in unsafe_patterns:
            if pattern in query_lower:
                return True
        
        return False
    
    def _default_safe_response(self) -> str:
        """Default safe response for flagged queries"""
        return """I can't help with that request, but I'm here to help with campus-related questions!

I can help you with:
• Finding study spots
• Dining options
• Campus resources and support
• Bus schedules
• Facility information

What would you like to know about UMass campus?"""

