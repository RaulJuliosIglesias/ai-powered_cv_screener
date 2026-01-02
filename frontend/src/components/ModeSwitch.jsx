import React from 'react';
import { Monitor, Cloud, Zap, Globe } from 'lucide-react';

export default function ModeSwitch({ mode, onModeChange, disabled }) {
  return (
    <div className="flex items-center gap-4">
      <div className="flex rounded-xl bg-gray-100 dark:bg-gray-800 p-1">
        <button
          onClick={() => onModeChange('local')}
          disabled={disabled}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-all ${
            mode === 'local'
              ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <Monitor className="w-4 h-4" />
          <span>Local</span>
          <Zap className="w-3 h-3 text-yellow-500" />
        </button>
        <button
          onClick={() => onModeChange('cloud')}
          disabled={disabled}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-lg transition-all ${
            mode === 'cloud'
              ? 'bg-white dark:bg-gray-700 text-blue-600 dark:text-blue-400 shadow-sm'
              : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <Cloud className="w-4 h-4" />
          <span>Cloud</span>
          <Globe className="w-3 h-3 text-green-500" />
        </button>
      </div>
      
      <div className="hidden sm:flex items-center gap-2 px-3 py-1.5 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
        <span className="text-xs text-gray-400">Stack:</span>
        <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
          {mode === 'local' ? 'ChromaDB + Gemini' : 'Supabase + OpenRouter'}
        </span>
      </div>
    </div>
  );
}
