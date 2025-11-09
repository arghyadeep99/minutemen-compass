"""
Gemini API Client for handling chat interactions with tool support
"""
import os
from dotenv import load_dotenv
from typing import Dict, List, Any

from google import genai
from google.genai import types

load_dotenv()


class GeminiClient:
    """Client for interacting with Google Gemini API"""

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable not set. "
                "Please create a .env file with your API key."
            )

        # Create a Gemini client (reads API key here)
        self.client = genai.Client(api_key=api_key)

        # Model name can be changed if you want a different one
        self.model_name = "gemini-2.5-flash"
        # self.model_name = "gemini-2.5-pro"

        self.system_prompt = """You are the UMass Campus Agent, a helpful AI assistant for UMass Amherst students, faculty, and staff.

Your role:
- Answer questions about campus life, facilities, services, and resources
- Use tools to provide real-time, actionable information
- Be friendly, empathetic, and concise
- When suggesting resources, explain WHY they're relevant

Guidelines:
- For study spots: Consider location, noise level, group size, and current hours
- For dining: Consider time of day, dietary restrictions, and location
- For resources: Match the user's need (academic, mental health, financial, etc.)
- For transportation: Provide specific bus routes and schedules when available
- Always suggest campus-specific resources over generic advice

If a user asks something you can't answer with available tools, acknowledge it and suggest they contact the relevant office directly.

Format your responses naturally, as if talking to a friend who needs help navigating campus."""

    async def chat_with_tools(
        self,
        user_message: str,
        tools_schema: List[Dict[str, Any]],
        tool_registry: Any,
        history: list[dict[str, str]] | None = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message with tool support.

        Args:
            user_message: The user's message
            tools_schema: List of function declarations (dicts) for Gemini
            tool_registry: ToolRegistry instance to execute tools

        Returns:
            Dictionary with reply, sources, tool_calls, and suggested_questions
        """

        # Wrap the raw JSON function declarations into a Tool object
        tools = types.Tool(
            function_declarations=[
                types.FunctionDeclaration(**fd) for fd in tools_schema
            ]
        )

        # Configure tools + system prompt
        config = types.GenerateContentConfig(
            tools=[tools],
            system_instruction=self.system_prompt,
        )

        # Conversation contents for this turn (include short history if provided)
        contents: List[types.Content] = []

        # Map prior turns into Gemini content objects
        if history:
            for item in history:
                role = (item.get("role") or "").lower()
                text = item.get("content") or ""
                if not text:
                    continue
                # Gemini uses "user" and "model" roles
                if role == "assistant":
                    contents.append(
                        types.Content(role="model", parts=[types.Part(text=text)])
                    )
                else:
                    contents.append(
                        types.Content(role="user", parts=[types.Part(text=text)])
                    )

        # Append current user message
        contents.append(
            types.Content(role="user", parts=[types.Part(text=user_message)])
        )

        tool_calls: List[Dict[str, Any]] = []
        sources: List[str] = []
        final_reply: str = ""

        max_iterations = 3

        for _ in range(max_iterations):
            # Call the model (sync call inside async; fine for now)
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=config,
            )

            # If the model gave no candidates, bail out
            if not response.candidates:
                break

            candidate = response.candidates[0]
            parts = candidate.content.parts if candidate.content else []

            # Collect any function calls in this response
            this_turn_calls = []
            for part in parts:
                function_call = getattr(part, "function_call", None)
                if function_call:
                    this_turn_calls.append(function_call)

            # No function calls → treat as final text answer
            if not this_turn_calls:
                final_reply = response.text or ""
                break

            # There *are* function calls: execute them and send results back
            function_response_parts: List[types.Part] = []

            for fc in this_turn_calls:
                name = fc.name
                args = dict(fc.args or {})

                tool_calls.append({"name": name, "arguments": args})

                # Execute your local tool
                result = tool_registry.call_tool(name, args)
                sources.append(f"Tool: {name}")

                # Wrap tool result in functionResponse part
                function_response_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response=result,
                    )
                )

            # Append the model's function-call message and our function responses
            contents.append(candidate.content)
            contents.append(
                types.Content(
                    role="user",
                    parts=function_response_parts,
                )
            )

            # Loop again so the model can turn tool outputs into a natural-language reply

        # Fallback if the loop exited without a final text
        if not final_reply:
            try:
                final_reply = (
                    response.text
                    or "I am here to help! Could you rephrase your question?"
                )
            except Exception:
                final_reply = "I am here to help! Could you rephrase your question?"

        suggested_questions = self._generate_suggested_questions(
            user_message, tool_calls
        )

        return {
            "reply": final_reply,
            "sources": sources or None,
            "tool_calls": tool_calls or None,
            "suggested_questions": suggested_questions,
        }

    def _generate_suggested_questions(
        self,
        user_message: str,
        tool_calls: List[Dict[str, Any]],
    ) -> List[str]:
        """Generate contextual suggested questions"""
        suggestions: List[str] = []

        if any(tc.get("name") == "get_study_spots" for tc in tool_calls):
            suggestions.extend(
                [
                    "What are good group study spaces?",
                    "Where can I find quiet study spots?",
                ]
            )

        if any(tc.get("name") == "get_dining_options" for tc in tool_calls):
            suggestions.extend(
                [
                    "What dining halls are open late?",
                    "Where can I find vegetarian options?",
                ]
            )

        if any(tc.get("name") == "get_support_resources" for tc in tool_calls):
            suggestions.extend(
                [
                    "How do I contact academic support?",
                    "What mental health resources are available?",
                ]
            )

        if not suggestions:
            suggestions = [
                "Find a quiet study spot",
                "What is open for food right now?",
                "Mental health support resources",
            ]

        return suggestions[:3]
