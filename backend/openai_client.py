"""
OpenAI API Client for handling chat interactions with tool support
"""
import os
import json
from typing import Dict, List, Any

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class OpenAIClient:
    """Client for interacting with OpenAI Chat Completions API"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please create a .env file with your API key."
            )

        # Create an OpenAI client (reads API key here)
        self.client = OpenAI(api_key=api_key)

        # Default model can be overridden with OPENAI_MODEL
        self.model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

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
        Process a chat message with tool support using OpenAI function calling.

        Args:
            user_message: The user's message
            tools_schema: Flat list of function declarations (name/description/parameters)
            tool_registry: ToolRegistry instance to execute tools

        Returns:
            Dictionary with reply, sources, tool_calls, and suggested_questions
        """
        # Convert flat function declarations into OpenAI tools format
        tools = [
            {
                "type": "function",
                "function": fd,
            }
            for fd in tools_schema
        ]

        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        # Include short prior history (user and assistant turns)
        if history:
            for item in history:
                role = (item.get("role") or "").lower()
                content = item.get("content") or ""
                if not content:
                    continue
                if role not in ("user", "assistant"):
                    # Only include user/assistant to keep context concise
                    continue
                messages.append({"role": role, "content": content})

        # Current user message last
        messages.append({"role": "user", "content": user_message})

        tool_calls: List[Dict[str, Any]] = []
        sources: List[str] = []
        final_reply: str = ""

        max_iterations = 3

        for _ in range(max_iterations):
            completion = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                temperature=0.2,
            )

            choice = completion.choices[0]
            message = choice.message

            # If there are tool calls, execute them and provide tool responses
            if getattr(message, "tool_calls", None):
                # Append assistant's tool call message
                # Ensure tool_calls are serializable
                serialized_tool_calls = []
                for tc in message.tool_calls:
                    serialized_tool_calls.append(
                        {
                            "id": tc.id,
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            },
                        }
                    )
                messages.append(
                    {
                        "role": "assistant",
                        "content": message.content or "",
                        "tool_calls": serialized_tool_calls,
                    }
                )

                # Execute each tool call and append tool results
                for tc in message.tool_calls:
                    name = tc.function.name
                    # OpenAI returns arguments as a JSON string
                    try:
                        args = (
                            json.loads(tc.function.arguments)
                            if isinstance(tc.function.arguments, str)
                            else dict(tc.function.arguments or {})
                        )
                    except Exception:
                        args = {}

                    tool_calls.append({"name": name, "arguments": args})

                    result = tool_registry.call_tool(name, args)
                    sources.append(f"Tool: {name}")

                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "content": json.dumps(result),
                        }
                    )
                # Continue loop so model can synthesize a final answer
                continue

            # No tool calls → take text as final
            final_reply = message.content or ""
            break

        # Fallback if the loop exited without a final text
        if not final_reply:
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
        """Generate contextual suggested questions (mirrors Gemini behavior)"""
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


