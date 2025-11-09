import { APP_NAME, APP_DESCRIPTION, APP_TAG } from '../constants'

function Header() {
  return (
    <header className="bg-umass-maroon text-white shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <h1 className="text-2xl font-bold">{APP_NAME}</h1>
            <span className="text-sm bg-umass-gold text-umass-maroon px-2 py-1 rounded">
              {APP_TAG}
            </span>
          </div>
          <p className="text-sm text-gray-200">
            {APP_DESCRIPTION}
          </p>
        </div>
      </div>
    </header>
  )
}

export default Header

