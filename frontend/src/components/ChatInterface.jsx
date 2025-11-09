import { useState, useRef, useEffect } from 'react'
import MessageList from './MessageList'
import MessageInput from './MessageInput'
import QuickActions from './QuickActions'

// Generate or retrieve session ID
function getSessionId() {
  let sessionId = localStorage.getItem('chat_session_id')
  if (!sessionId) {
    sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
    localStorage.setItem('chat_session_id', sessionId)
  }
  return sessionId
}

function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content: "Hi! I'm the UMass Campus Agent. I can help you find study spots, dining options, campus resources, bus schedules, and more. What can I help you with today?",
      timestamp: new Date()
    }
  ])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const sessionIdRef = useRef(getSessionId())

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const sendMessage = async (content) => {
    if (!content.trim() || isLoading) return

    const userMessage = {
      role: 'user',
      content: content.trim(),
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setIsLoading(true)

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: content.trim(),
          session_id: sessionIdRef.current,
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to get response')
      }

      const data = await response.json()
      
      const assistantMessage = {
        role: 'assistant',
        content: data.reply,
        sources: data.sources,
        toolCalls: data.tool_calls,
        suggestedQuestions: data.suggested_questions,
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])
    } catch (error) {
      console.error('Error:', error)
      const errorMessage = {
        role: 'assistant',
        content: "I'm sorry, I encountered an error. Please try again or check your connection.",
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleQuickAction = (action) => {
    const quickMessages = {
      'Study spots': 'Where can I find a quiet study spot near LGRC?',
      'Dining now': 'What dining options are open right now?',
      'Mental health support': 'What mental health resources are available on campus?',
      'Bus schedule': 'What is the next bus from Campus Center to Puffton?',
      'Academic support': 'What academic support resources are available?',
      'Campus resources': 'What campus resources can help me?'
    }
    
    sendMessage(quickMessages[action] || action)
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-white rounded-lg shadow-xl overflow-hidden">
        <div className="bg-gradient-to-r from-umass-maroon to-umass-maroon/90 p-4">
          <h2 className="text-white text-lg font-semibold">Chat</h2>
        </div>
        
        <QuickActions onActionClick={handleQuickAction} />
        
        <div className="h-[500px] overflow-y-auto p-4 bg-gray-50">
          <MessageList messages={messages} />
          {isLoading && (
            <div className="flex items-center space-x-2 text-gray-500">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-umass-maroon"></div>
              <span className="text-sm">Thinking...</span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        
        <MessageInput onSend={sendMessage} disabled={isLoading} />
      </div>
    </div>
  )
}

export default ChatInterface

