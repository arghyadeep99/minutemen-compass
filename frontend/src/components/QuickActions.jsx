function QuickActions({ onActionClick }) {
  const actions = [
    'Study spots',
    'Dining now',
    'Mental health support',
    'Bus schedule',
    'Academic support',
    'Campus resources'
  ]

  return (
    <div className="p-4 bg-gray-100 border-b border-gray-200">
      <p className="text-sm text-gray-600 mb-2">Quick actions:</p>
      <div className="flex flex-wrap gap-2">
        {actions.map((action) => (
          <button
            key={action}
            onClick={() => onActionClick(action)}
            className="px-3 py-1 bg-white text-umass-maroon border border-umass-maroon rounded-full text-sm hover:bg-umass-maroon hover:text-white transition-colors"
          >
            {action}
          </button>
        ))}
      </div>
    </div>
  )
}

export default QuickActions

