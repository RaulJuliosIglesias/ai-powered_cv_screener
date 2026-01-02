import { useState, useCallback, useEffect } from 'react';

const STORAGE_KEY = 'cv-screener-mode';

export default function useMode() {
  const [mode, setMode] = useState(() => {
    // Try to restore from localStorage
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'local' || saved === 'cloud') {
        return saved;
      }
    }
    return 'local'; // Default mode
  });
  
  // Persist mode changes to localStorage
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);
  
  const toggleMode = useCallback(() => {
    setMode(prev => prev === 'local' ? 'cloud' : 'local');
  }, []);
  
  const setModeValue = useCallback((newMode) => {
    if (newMode === 'local' || newMode === 'cloud') {
      setMode(newMode);
    }
  }, []);
  
  return {
    mode,
    setMode: setModeValue,
    toggleMode,
    isLocal: mode === 'local',
    isCloud: mode === 'cloud',
  };
}
