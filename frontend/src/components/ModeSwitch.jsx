import React from 'react';
import { Monitor, Cloud } from 'lucide-react';

export default function ModeSwitch({ mode, onModeChange, disabled }) {
  return (
    <div className="flex items-center gap-4 p-3 bg-gray-100 rounded-lg">
      <span className="text-sm font-medium text-gray-700">Mode:</span>
      
      <div className="flex rounded-md shadow-sm">
        <button
          onClick={() => onModeChange('local')}
          disabled={disabled}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-l-md border transition-colors ${
            mode === 'local'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <Monitor className="w-4 h-4" />
          Local
        </button>
        <button
          onClick={() => onModeChange('cloud')}
          disabled={disabled}
          className={`flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-r-md border-t border-b border-r transition-colors ${
            mode === 'cloud'
              ? 'bg-blue-600 text-white border-blue-600'
              : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
          } ${disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <Cloud className="w-4 h-4" />
          Cloud
        </button>
      </div>
      
      <span className="text-xs text-gray-500">
        {mode === 'local' ? 'ChromaDB + Gemini' : 'Supabase + OpenRouter'}
      </span>
    </div>
  );
}
