import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

function MessageList({ messages, onSuggestedQuestionClick }) {
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
            <div className={`prose prose-sm max-w-none ${
              message.role === 'user' 
                ? 'prose-invert' 
                : 'prose-gray'
            }`}>
              <ReactMarkdown 
                remarkPlugins={[remarkGfm]}
                components={{
                  p: ({node, ...props}) => <p className="whitespace-pre-wrap mb-2 last:mb-0" {...props}/>,
                  a: ({node, ...props}) => <a className={`${message.role === 'user' ? 'text-white' : 'text-blue-600'} hover:underline`} {...props}/>,
                  ul: ({node, ...props}) => <ul className="list-disc ml-4 mb-2" {...props}/>,
                  ol: ({node, ...props}) => <ol className="list-decimal ml-4 mb-2" {...props}/>,
                  code: ({node, inline, ...props}) => (
                    inline 
                      ? <code className={`${message.role === 'user' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-800'} px-1 py-0.5 rounded text-sm`} {...props}/>
                      : <code className={`block ${message.role === 'user' ? 'bg-white/20 text-white' : 'bg-gray-100 text-gray-800'} p-2 rounded text-sm overflow-x-auto`} {...props}/>
                  )
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
            
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
                    <button
                      key={i}
                      onClick={() => onSuggestedQuestionClick(q)}
                      className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 px-2 py-1 rounded cursor-pointer transition-colors"
                    >
                      {q}
                    </button>
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

