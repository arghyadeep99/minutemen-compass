"""
Conversation memory management for LangGraph agent
Stores conversation history per session
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.load import dumpd, load


class ConversationMemory:
    """Manages conversation memory per session"""
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize conversation memory storage"""
        if db_path is None:
            db_path = Path("data/conversations.db")
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        
        # In-memory cache for active sessions (last 10 sessions, max 50 messages each)
        self._cache: Dict[str, List[BaseMessage]] = {}
        self._max_cache_size = 10
        self._max_messages_per_session = 50
    
    def _init_db(self):
        """Initialize SQLite database for conversation storage"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                message_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_timestamp 
            ON conversations(session_id, timestamp)
        """)
        conn.commit()
        conn.close()
    
    def get_conversation_history(
        self, 
        session_id: Optional[str], 
        max_messages: int = 20
    ) -> List[BaseMessage]:
        """
        Get conversation history for a session
        
        Args:
            session_id: Session identifier (if None, returns empty list)
            max_messages: Maximum number of messages to retrieve (most recent)
        
        Returns:
            List of BaseMessage objects
        """
        if not session_id:
            return []
        
        # Check cache first
        if session_id in self._cache:
            messages = self._cache[session_id]
            # Return last max_messages
            return messages[-max_messages:] if len(messages) > max_messages else messages
        
        # Load from database (get most recent messages)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT message_type, content, metadata
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, max_messages))
        
        rows = cursor.fetchall()
        conn.close()
        
        messages = []
        # Reverse to get chronological order (oldest first)
        for row in reversed(rows):
            msg_type, content, metadata_json = row
            metadata = json.loads(metadata_json) if metadata_json else {}
            
            # Reconstruct message based on type
            if msg_type == "human":
                messages.append(HumanMessage(content=content))
            elif msg_type == "ai":
                # Reconstruct AIMessage with tool_calls if present
                msg = AIMessage(content=content)
                if "tool_calls" in metadata:
                    msg.tool_calls = metadata["tool_calls"]
                messages.append(msg)
            elif msg_type == "system":
                messages.append(SystemMessage(content=content))
            elif msg_type == "tool":
                messages.append(ToolMessage(content=content, tool_call_id=metadata.get("tool_call_id", "")))
        
        # Cache the messages
        if len(self._cache) >= self._max_cache_size:
            # Remove oldest session from cache
            oldest_key = min(self._cache.keys(), key=lambda k: len(self._cache[k]))
            del self._cache[oldest_key]
        
        self._cache[session_id] = messages
        return messages
    
    def save_message(
        self,
        session_id: Optional[str],
        message: BaseMessage
    ):
        """
        Save a message to conversation history
        
        Args:
            session_id: Session identifier
            message: Message to save
        """
        if not session_id:
            return
        
        # Determine message type and extract content
        metadata = {}  # Initialize metadata for all message types
        
        if isinstance(message, HumanMessage):
            msg_type = "human"
            content = message.content
        elif isinstance(message, AIMessage):
            msg_type = "ai"
            content = message.content
            # Store tool_calls in metadata if present
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Convert tool_calls to serializable format
                tool_calls_serializable = []
                for tc in message.tool_calls:
                    if isinstance(tc, dict):
                        tool_calls_serializable.append(tc)
                    else:
                        tool_calls_serializable.append({
                            "name": getattr(tc, "name", ""),
                            "args": getattr(tc, "args", {})
                        })
                metadata["tool_calls"] = tool_calls_serializable
        elif isinstance(message, SystemMessage):
            msg_type = "system"
            content = message.content
        elif isinstance(message, ToolMessage):
            msg_type = "tool"
            content = message.content
            metadata["tool_call_id"] = getattr(message, "tool_call_id", "")
        else:
            # Unknown message type, skip
            return
        
        metadata_json = json.dumps(metadata) if metadata else None
        timestamp = datetime.now().isoformat()
        
        # Save to database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO conversations (session_id, message_type, content, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, msg_type, content, metadata_json, timestamp))
        conn.commit()
        conn.close()
        
        # Update cache
        if session_id not in self._cache:
            self._cache[session_id] = []
        
        self._cache[session_id].append(message)
        
        # Limit cache size per session
        if len(self._cache[session_id]) > self._max_messages_per_session:
            self._cache[session_id] = self._cache[session_id][-self._max_messages_per_session:]
    
    def save_messages(
        self,
        session_id: Optional[str],
        messages: List[BaseMessage]
    ):
        """Save multiple messages to conversation history"""
        for message in messages:
            self.save_message(session_id, message)
    
    def clear_session(self, session_id: Optional[str]):
        """Clear conversation history for a session"""
        if not session_id:
            return
        
        # Remove from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.commit()
        conn.close()
        
        # Remove from cache
        if session_id in self._cache:
            del self._cache[session_id]
    
    def cleanup_old_sessions(self, days: int = 30):
        """Remove conversation history older than specified days"""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE timestamp < ?", (cutoff_date,))
        conn.commit()
        conn.close()

