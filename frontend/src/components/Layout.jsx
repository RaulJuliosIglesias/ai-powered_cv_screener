import { FileText, Plus, Sun, Moon, Sparkles } from 'lucide-react';

const Layout = ({ children, onAddClick, showAddButton = false, theme, onThemeToggle }) => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col transition-colors">
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-gradient-to-br from-blue-500 to-purple-600 p-2.5 rounded-xl shadow-lg shadow-blue-500/25">
              <Sparkles className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">CV Screener</h1>
              <p className="text-xs text-gray-500 dark:text-gray-400">RAG-Powered Analysis</p>
            </div>
          </div>
          
          <div className="flex items-center gap-3">
            {/* Theme Toggle */}
            <button
              onClick={onThemeToggle}
              className="p-2.5 rounded-xl bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              aria-label="Toggle theme"
            >
              {theme === 'light' ? (
                <Moon className="w-5 h-5 text-gray-600 dark:text-gray-300" />
              ) : (
                <Sun className="w-5 h-5 text-yellow-500" />
              )}
            </button>
            
            {/* Add CVs Button */}
            {showAddButton && (
              <button
                onClick={onAddClick}
                className="flex items-center gap-2 px-4 py-2.5 bg-blue-500 hover:bg-blue-600 text-white rounded-xl font-medium transition-colors shadow-lg shadow-blue-500/25"
              >
                <Plus className="w-4 h-4" />
                <span>Añadir CVs</span>
              </button>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
};

export default Layout;
