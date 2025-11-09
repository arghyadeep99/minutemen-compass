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
        self.model = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.7,
            api_key=api_key
        )

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
            func=lambda origin=None, destination=None: 
                tool_registry.get_bus_schedule(origin, destination),
            name="get_bus_schedule",
            description="Get PVTA bus schedule information between campus locations",
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
            conversation_history = self.memory.get_conversation_history(session_id, max_messages=20)
            # Check if system message is already in history
            has_system_in_history = any(
                isinstance(msg, SystemMessage) for msg in conversation_history
            )
        
        # Create initial state with conversation history + new user message
        initial_messages = list(conversation_history) + [HumanMessage(content=user_message)]
        initial_state = {
            "messages": initial_messages
        }
        
        # Run the graph
        final_state = await self.graph.ainvoke(initial_state)
        
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

        if not suggestions:
            suggestions = [
                "Find a quiet study spot",
                "What is open for food right now?",
                "Mental health support resources",
            ]

        return suggestions[:3]

