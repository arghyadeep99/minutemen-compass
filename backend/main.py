"""
UMass Campus Agent - FastAPI Backend
Main application entry point with chat endpoint and tool integrations
"""
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import json
import os
from datetime import datetime
import sqlite3
from pathlib import Path

from langgraph_agent import LangGraphAgent
from tools import ToolRegistry
from safety_checker import SafetyChecker

app = FastAPI(title="UMass Campus Agent API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
langgraph_agent = LangGraphAgent()
tool_registry = ToolRegistry()
safety_checker = SafetyChecker()

# Initialize database
DB_PATH = Path("data/logs.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def init_db():
    """Initialize SQLite database for logging"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            user_query TEXT NOT NULL,
            category TEXT,
            is_flagged INTEGER DEFAULT 0,
            response TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    reply: str
    sources: Optional[List[str]] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    suggested_questions: Optional[List[str]] = None

def log_query(user_query: str, category: str, is_flagged: bool, response: str = ""):
    """Log user queries to database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO logs (timestamp, user_query, category, is_flagged, response)
        VALUES (?, ?, ?, ?, ?)
    """, (datetime.now().isoformat(), user_query, category, 1 if is_flagged else 0, response))
    conn.commit()
    conn.close()

@app.get("/")
def root():
    return {"message": "UMass Campus Agent API", "status": "running"}

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint that processes user messages through LangGraph agent
    with tool support and safety checks
    """
    user_message = request.message.strip()
    
    if not user_message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    # Safety check
    safety_result = safety_checker.check(user_message)
    if safety_result["is_unsafe"]:
        log_query(user_message, "unsafe", True, safety_result["response"])
        return ChatResponse(
            reply=safety_result["response"],
            sources=["Campus Safety Resources"],
            suggested_questions=[
                "What mental health resources are available?",
                "How do I report a concern?",
                "Where can I get academic support?"
            ]
        )
    
    # Get tool schemas (kept for compatibility)
    tools_schema = tool_registry.get_tools_schema()
    
    # Call LangGraph agent with tools
    try:
        # Use session_id from request, or generate one if not provided
        session_id = request.session_id or f"session_{datetime.now().timestamp()}"
        
        response = await langgraph_agent.chat_with_tools(
            user_message=user_message,
            tools_schema=tools_schema,
            tool_registry=tool_registry,
            session_id=session_id
        )
        
        # Determine category
        category = "general"
        if any(keyword in user_message.lower() for keyword in ["study", "quiet", "spot", "space"]):
            category = "study_spots"
        elif any(keyword in user_message.lower() for keyword in ["food", "dining", "eat", "meal"]):
            category = "dining"
        elif any(keyword in user_message.lower() for keyword in ["help", "support", "resource", "counseling"]):
            category = "resources"
        elif any(keyword in user_message.lower() for keyword in ["bus", "pvta", "transport"]):
            category = "transport"
        
        log_query(user_message, category, False, response["reply"])
        
        return ChatResponse(
            reply=response["reply"],
            sources=response.get("sources"),
            tool_calls=response.get("tool_calls"),
            suggested_questions=response.get("suggested_questions")
        )
    
    except Exception as e:
        log_query(user_message, "error", False, str(e))
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/api/study-spots")
def get_study_spots(
    location: Optional[str] = None,
    noise_preference: Optional[str] = None,
    group_size: Optional[str] = None
):
    """Direct API endpoint for study spots"""
    result = tool_registry.call_tool(
        "get_study_spots",
        {
            "location": location,
            "noise_preference": noise_preference,
            "group_size": group_size
        }
    )
    return result

@app.get("/api/dining")
def get_dining(
    time_now: Optional[str] = None,
    dietary_pref: Optional[str] = None
):
    """Direct API endpoint for dining options"""
    result = tool_registry.call_tool(
        "get_dining_options",
        {
            "time_now": time_now,
            "dietary_pref": dietary_pref
        }
    )
    return result

@app.get("/api/resources")
def get_resources(topic: Optional[str] = None):
    """Direct API endpoint for campus resources"""
    result = tool_registry.call_tool(
        "get_support_resources",
        {
            "topic": topic
        }
    )
    return result

@app.get("/api/bus")
def get_bus(
    origin: Optional[str] = None,
    destination: Optional[str] = None
):
    """Direct API endpoint for bus information"""
    result = tool_registry.call_tool(
        "get_bus_schedule",
        {
            "origin": origin,
            "destination": destination
        }
    )
    return result

@app.get("/api/logs")
def get_logs(limit: int = 50):
    """Admin endpoint to view logs (for debugging)"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT timestamp, user_query, category, is_flagged
        FROM logs
        ORDER BY timestamp DESC
        LIMIT ?
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [
        {
            "timestamp": row[0],
            "query": row[1],
            "category": row[2],
            "is_flagged": bool(row[3])
        }
        for row in rows
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

