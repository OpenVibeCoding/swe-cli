import { Link, useLocation } from 'react-router-dom';
import { MagnifyingGlassIcon, Cog6ToothIcon } from '@heroicons/react/24/outline';
import { Button } from '../ui/Button';

export function AppNavBar() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/chat') {
      return location.pathname === '/chat' || location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="fixed top-0 left-0 right-0 h-14 bg-white border-b border-gray-200 z-50 shadow-sm">
      <div className="h-full max-w-[1400px] mx-auto px-6 flex items-center justify-between">
        {/* Left: Brand and Navigation */}
        <div className="flex items-center gap-6">
          {/* Brand/Logo */}
          <Link to="/chat" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-purple-500 to-blue-600 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
              </svg>
            </div>
            <span className="text-base font-semibold text-gray-900">SWE-CLI</span>
          </Link>

          {/* Navigation Links */}
          <div className="flex items-center gap-2">
            <Link
              to="/chat"
              className={`px-1.5 pb-1.5 text-sm font-medium border-b-2 transition-colors ${
                isActive('/chat')
                  ? 'text-gray-900 border-gray-900'
                  : 'text-gray-600 border-transparent hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              Chat
            </Link>
            <Link
              to="/codewiki"
              className={`px-1.5 pb-1.5 text-sm font-medium border-b-2 transition-colors ${
                isActive('/codewiki')
                  ? 'text-gray-900 border-gray-900'
                  : 'text-gray-600 border-transparent hover:text-gray-900 hover:border-gray-300'
              }`}
            >
              CodeWiki
            </Link>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <Button
            variant="subtle"
            size="sm"
            title="Search"
            aria-label="Search"
            className="p-2 h-auto"
          >
            <MagnifyingGlassIcon className="w-5 h-5 text-gray-600" />
          </Button>
          <Button
            variant="subtle"
            size="sm"
            title="Settings"
            aria-label="Settings"
            className="p-2 h-auto"
          >
            <Cog6ToothIcon className="w-5 h-5 text-gray-600" />
          </Button>
        </div>
      </div>
    </nav>
  );
}
