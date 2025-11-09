function MessageList({ messages }) {
  return (
    <div className="space-y-4">
      {messages.map((message, index) => (
        <div
          key={index}
          className={`flex ${
            message.role === 'user' ? 'justify-end' : 'justify-start'
          }`}
        >
          <div
            className={`max-w-[80%] rounded-lg px-4 py-2 ${
              message.role === 'user'
                ? 'bg-umass-maroon text-white'
                : 'bg-white text-gray-800 border border-gray-200'
            }`}
          >
            <p className="whitespace-pre-wrap">{message.content}</p>
            
            {message.sources && message.sources.length > 0 && (
              <div className="mt-2 pt-2 border-t border-gray-300">
                <p className="text-xs text-gray-500">
                  Sources: {message.sources.join(', ')}
                </p>
              </div>
            )}
            
            {message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
              <div className="mt-3 pt-2 border-t border-gray-300">
                <p className="text-xs font-semibold mb-1">Suggested questions:</p>
                <div className="flex flex-wrap gap-1">
                  {message.suggestedQuestions.map((q, i) => (
                    <span
                      key={i}
                      className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded"
                    >
                      {q}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

export default MessageList

