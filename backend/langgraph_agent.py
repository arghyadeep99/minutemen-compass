"""
LangGraph Agent for handling chat interactions with tool support using OpenAI
"""
import os
from dotenv import load_dotenv
from typing import Dict, List, Any, TypedDict, Annotated, Sequence, Optional

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages

from conversation_memory import ConversationMemory

load_dotenv()


class AgentState(TypedDict):
    """State for the LangGraph agent"""
    messages: Annotated[Sequence[BaseMessage], add_messages]


class LangGraphAgent:
    """LangGraph agent using OpenAI for chat interactions with tool support"""

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError(
                "OPENAI_API_KEY environment variable not set. "
                "Please create a .env file with your API key."
            )

        # Initialize OpenAI model with system prompt
        # Using gpt-4o-mini (gpt-5-mini doesn't exist)
        try:
            self.model = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.7,
                api_key=api_key
            )
        except Exception as e:
            raise ValueError(
                f"Failed to initialize OpenAI client: {str(e)}. "
                "Please check your OPENAI_API_KEY and ensure it's valid."
            ) from e

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
- For transportation/bus queries: ALWAYS use the get_bus_schedule tool when users ask about:
  * Bus routes (e.g., "route 31", "bus 30", "B43")
  * Bus schedules or times
  * When the next bus arrives
  * Bus stops or locations
  * PVTA bus information
  Extract the route number from the query and use get_bus_schedule with route_number parameter
- Always suggest campus-specific resources over generic advice

IMPORTANT: When a user asks about a bus route (e.g., "route 31", "bus 30", "what is route B43"), you MUST call the get_bus_schedule tool with the route_number parameter. Do not provide generic information without checking the actual schedule.

If a user asks something you can't answer with available tools, acknowledge it and suggest they contact the relevant office directly.

Format your responses naturally, as if talking to a friend who needs help navigating campus."""

        self.graph = None
        self.tool_registry = None
        self.memory = ConversationMemory()

    def _create_tools(self, tool_registry: Any) -> List[StructuredTool]:
        """Convert tool registry methods to LangChain StructuredTool objects"""
        tools = []
        
        # Get study spots tool
        tools.append(StructuredTool.from_function(
            func=lambda location=None, noise_preference=None, group_size=None: 
                tool_registry.get_study_spots(location, noise_preference, group_size),
            name="get_study_spots",
            description="Find study spaces on campus based on location, noise preference, and group size",
        ))
        
        # Get dining options tool
        tools.append(StructuredTool.from_function(
            func=lambda time_now=None, dietary_pref=None, dining_type=None, location=None: 
                tool_registry.get_dining_options(time_now, dietary_pref, dining_type, location),
            name="get_dining_options",
            description="Find dining options on campus based on current time and dietary preferences. Use dining_type='Grab N Go' to get only Grab N Go menus, or 'Dining Hall' for regular dining halls. Use location to filter by specific dining hall (e.g., 'Franklin', 'Berkshire', 'Worcester', 'Hampshire').",
        ))
        
        # Search food items tool
        tools.append(StructuredTool.from_function(
            func=lambda food_type=None, location=None, meal_period=None: 
                tool_registry.search_food_items(food_type, location, meal_period),
            name="search_food_items",
            description="Search for specific food items or food types (e.g., sandwiches, burgers, vegetarian options, meat dishes) across dining halls. Can filter by location and meal period.",
        ))
        
        # Get dining hall info tool
        tools.append(StructuredTool.from_function(
            func=lambda dining_hall: 
                tool_registry.get_dining_hall_info(dining_hall),
            name="get_dining_hall_info",
            description="Get general information about a dining hall including hours, location, features, manager contact, and other details. Use this when users ask about dining hall hours, location, features, or general information.",
        ))
        
        # Get support resources tool
        tools.append(StructuredTool.from_function(
            func=lambda topic=None: 
                tool_registry.get_support_resources(topic),
            name="get_support_resources",
            description="Find campus support resources for various needs (academic, mental health, financial, etc.)",
        ))
        
        # Get bus schedule tool
        tools.append(StructuredTool.from_function(
            func=lambda route_number=None, origin=None, destination=None, stop=None: 
                tool_registry.get_bus_schedule(route_number, origin, destination, stop),
            name="get_bus_schedule",
            description="""Get PVTA bus schedule information for UMass Amherst. 
            
USE THIS TOOL when users ask about:
- Bus routes (e.g., "route 31", "bus 30", "what is route B43")
- Bus schedules or times
- When the next bus arrives at a stop
- Bus stops or locations
- PVTA bus information

Parameters:
- route_number: The bus route number (e.g., "30", "31", "B43", "35") - EXTRACT THIS FROM USER QUERY
- origin: Starting location (optional)
- destination: Destination location (optional)  
- stop: Specific stop name to get next bus times (optional)

IMPORTANT: If the user mentions a route number (like "31", "30", "B43"), you MUST provide the route_number parameter. The tool will download and parse the actual PDF schedule for that route.""",
        ))
        
        # Get course info tool
        tools.append(StructuredTool.from_function(
            func=lambda course_code=None, info_type=None: 
                tool_registry.get_course_info(course_code, info_type),
            name="get_course_info",
            description="Get information about courses, including course content, prerequisites, and instructor details",
        ))
        
        # Get facility info tool
        tools.append(StructuredTool.from_function(
            func=lambda facility_name=None, info_type=None: 
                tool_registry.get_facility_info(facility_name, info_type),
            name="get_facility_info",
            description="Get information about campus facilities (gyms, libraries, labs, etc.)",
        ))
        
        # Report facility issue tool
        tools.append(StructuredTool.from_function(
            func=lambda facility_name=None, issue_type=None, description=None: 
                tool_registry.report_facility_issue(facility_name, issue_type, description),
            name="report_facility_issue",
            description="Report a facility issue (broken equipment, maintenance, etc.)",
        ))
        
        return tools

    def _clean_conversation_history(self, messages: List[BaseMessage]) -> List[BaseMessage]:
        """
        Clean conversation history to ensure valid message sequence.
        Removes orphaned ToolMessages that don't have a preceding AIMessage with tool_calls.
        OpenAI API requires that ToolMessages must follow an AIMessage with tool_calls.
        """
        if not messages:
            return []
        
        cleaned = []
        
        for i, msg in enumerate(messages):
            # If it's a ToolMessage, check if there's a preceding AIMessage with tool_calls
            if isinstance(msg, ToolMessage):
                # Look backwards through cleaned messages to find preceding AIMessage
                found_valid_predecessor = False
                
                for j in range(len(cleaned) - 1, -1, -1):
                    prev_msg = cleaned[j]
                    
                    # Check if previous message is an AIMessage with tool_calls
                    if isinstance(prev_msg, AIMessage):
                        # Check if it has tool_calls
                        tool_calls = getattr(prev_msg, 'tool_calls', None)
                        if tool_calls and len(tool_calls) > 0:
                            # Verify the tool_call_id matches one of the tool_calls
                            tool_call_id = getattr(msg, 'tool_call_id', '')
                            if tool_call_id:
                                # Check if any tool_call has a matching id
                                for tc in tool_calls:
                                    tc_id = None
                                    if isinstance(tc, dict):
                                        tc_id = tc.get('id') or tc.get('tool_call_id')
                                    elif hasattr(tc, 'id'):
                                        tc_id = tc.id
                                    elif hasattr(tc, 'tool_call_id'):
                                        tc_id = tc.tool_call_id
                                    
                                    if tc_id == tool_call_id:
                                        found_valid_predecessor = True
                                        break
                            
                            # If we found an AIMessage with tool_calls, that's good enough
                            # (even if IDs don't match, we'll include it to avoid breaking the sequence)
                            if not found_valid_predecessor:
                                found_valid_predecessor = True
                            break
                        else:
                            # AIMessage without tool_calls - stop looking
                            break
                    elif isinstance(prev_msg, (HumanMessage, SystemMessage)):
                        # Stop at human/system messages - no valid predecessor found
                        break
                
                if found_valid_predecessor:
                    cleaned.append(msg)
                # else: skip orphaned ToolMessage
            else:
                # For non-ToolMessages, add them
                cleaned.append(msg)
        
        return cleaned

    def _build_graph(self, tool_registry: Any):
        """Build the LangGraph state graph"""
        # Create tools
        tools = self._create_tools(tool_registry)
        
        # Bind tools to model
        model_with_tools = self.model.bind_tools(tools)
        
        # Create tool node
        tool_node = ToolNode(tools)
        
        # Define the agent node
        def agent_node(state: AgentState):
            messages = state["messages"]
            # Add system message as first message if not already present
            has_system = any(
                isinstance(msg, SystemMessage) for msg in messages
            )
            
            if not has_system:
                system_msg = SystemMessage(content=self.system_prompt)
                messages = [system_msg] + list(messages)
            
            response = model_with_tools.invoke(messages)
            return {"messages": [response]}
        
        # Build graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", agent_node)
        workflow.add_node("tools", tool_node)
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        def should_continue(state: AgentState) -> str:
            messages = state["messages"]
            last_message = messages[-1]
            # If there are tool calls, route to tools
            if hasattr(last_message, 'tool_calls') and last_message.tool_calls:
                return "tools"
            # Otherwise, end
            return END
        
        workflow.add_conditional_edges(
            "agent",
            should_continue,
            {
                "tools": "tools",
                END: END
            }
        )
        
        # After tools, go back to agent
        workflow.add_edge("tools", "agent")
        
        # Compile graph
        self.graph = workflow.compile()
        
        return self.graph

    async def chat_with_tools(
        self,
        user_message: str,
        tools_schema: List[Dict[str, Any]],  # Kept for compatibility, but not used
        tool_registry: Any,
        session_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a chat message with tool support.

        Args:
            user_message: The user's message
            tools_schema: List of function declarations (kept for compatibility)
            tool_registry: ToolRegistry instance to execute tools
            session_id: Optional session ID for conversation memory

        Returns:
            Dictionary with reply, sources, tool_calls, and suggested_questions
        """
        # Build graph if not already built or if tool_registry changed
        if self.graph is None or self.tool_registry != tool_registry:
            self.tool_registry = tool_registry
            self._build_graph(tool_registry)
        
        # Get conversation history if session_id is provided
        conversation_history = []
        has_system_in_history = False
        if session_id:
            raw_history = self.memory.get_conversation_history(session_id, max_messages=20)
            # Clean and validate conversation history to ensure proper message sequence
            conversation_history = self._clean_conversation_history(raw_history)
            # Check if system message is already in history
            has_system_in_history = any(
                isinstance(msg, SystemMessage) for msg in conversation_history
            )
        
        # Create initial state with conversation history + new user message
        initial_messages = list(conversation_history) + [HumanMessage(content=user_message)]
        initial_state = {
            "messages": initial_messages
        }
        
        # Run the graph with error handling
        try:
            final_state = await self.graph.ainvoke(initial_state)
        except Exception as e:
            # Capture detailed error information
            error_type = type(e).__name__
            error_message = str(e)
            
            # Check for common OpenAI API errors
            if "API key" in error_message or "authentication" in error_message.lower():
                raise ValueError(
                    f"OpenAI API Authentication Error: {error_message}. "
                    "Please check your OPENAI_API_KEY in the .env file."
                )
            elif "rate limit" in error_message.lower() or "429" in error_message:
                raise ValueError(
                    f"OpenAI API Rate Limit Error: {error_message}. "
                    "Please wait a moment and try again."
                )
            elif "insufficient_quota" in error_message.lower() or "quota" in error_message.lower():
                raise ValueError(
                    f"OpenAI API Quota Error: {error_message}. "
                    "Your OpenAI account may have insufficient credits."
                )
            elif "invalid" in error_message.lower() and "model" in error_message.lower():
                raise ValueError(
                    f"OpenAI API Model Error: {error_message}. "
                    "The model specified may not be available."
                )
            else:
                # Re-raise with more context
                raise Exception(
                    f"OpenAI API Error ({error_type}): {error_message}"
                ) from e
        
        # Extract messages
        messages = final_state["messages"]
        
        # Get only new messages (those not in conversation history)
        new_messages = messages[len(conversation_history):] if conversation_history else messages
        
        # Save new messages to memory (excluding system messages to avoid duplicates)
        if session_id:
            # Save user message
            self.memory.save_message(session_id, HumanMessage(content=user_message))
            # Save new messages from this interaction (skip system messages)
            for msg in new_messages:
                if not isinstance(msg, SystemMessage):
                    self.memory.save_message(session_id, msg)
        
        # Extract tool calls and final reply
        tool_calls: List[Dict[str, Any]] = []
        sources: List[str] = []
        final_reply: str = ""
        
        # Process messages to extract tool calls and final response
        # Look at all messages, but prioritize new ones
        for msg in reversed(messages):  # Start from the end to get most recent
            if isinstance(msg, AIMessage):
                if hasattr(msg, 'tool_calls') and msg.tool_calls:
                    for tool_call in msg.tool_calls:
                        # Handle both dict and object formats
                        if isinstance(tool_call, dict):
                            tool_name = tool_call.get("name", "")
                            tool_args = tool_call.get("args", {})
                        else:
                            # LangChain ToolCall object
                            tool_name = getattr(tool_call, "name", "")
                            # ToolCall.args can be a dict or need to be accessed differently
                            if hasattr(tool_call, "args"):
                                tool_args = tool_call.args if isinstance(tool_call.args, dict) else dict(tool_call.args)
                            elif hasattr(tool_call, "get"):
                                tool_args = tool_call.get("args", {})
                            else:
                                tool_args = {}
                        
                        tool_calls.append({
                            "name": tool_name,
                            "arguments": tool_args
                        })
                        sources.append(f"Tool: {tool_name}")
                elif msg.content:
                    if not final_reply:  # Use first AI message with content
                        final_reply = msg.content
            elif isinstance(msg, ToolMessage):
                # Tool responses are already handled
                pass
        
        # If no final reply found, use the last AI message
        if not final_reply:
            for msg in reversed(messages):
                if isinstance(msg, AIMessage) and msg.content:
                    final_reply = msg.content
                    break
        
        # Fallback
        if not final_reply:
            final_reply = "I am here to help! Could you rephrase your question?"
        
        # Generate suggested questions
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

        if any(tc.get("name") == "get_course_info" for tc in tool_calls):
            suggestions.extend(
                [
                    "What are the prerequisites for CICS 210?",
                    "Who teaches INFO 248?",
                    "What courses are offered in Spring 2026?",
                ]
            )

        if not suggestions:
            suggestions = [
                "Find a quiet study spot",
                "What is open for food right now?",
                "Mental health support resources",
            ]

        return suggestions[:3]

