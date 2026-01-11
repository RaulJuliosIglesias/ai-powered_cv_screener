import { useState, useCallback, useEffect } from 'react';
import type { AppMode } from '@/types';

const STORAGE_KEY = 'cv-screener-mode';

interface UseModeReturn {
  mode: AppMode;
  setMode: (newMode: AppMode) => void;
  toggleMode: () => void;
  isLocal: boolean;
  isCloud: boolean;
}

export default function useMode(): UseModeReturn {
  const [mode, setMode] = useState<AppMode>(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === 'local' || saved === 'cloud') {
        return saved;
      }
    }
    return 'local';
  });
  
  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, mode);
  }, [mode]);
  
  const toggleMode = useCallback(() => {
    setMode(prev => prev === 'local' ? 'cloud' : 'local');
  }, []);
  
  const setModeValue = useCallback((newMode: AppMode) => {
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
