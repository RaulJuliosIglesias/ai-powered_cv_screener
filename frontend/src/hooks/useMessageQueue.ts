import { useState, useCallback, useEffect, useRef } from 'react';

interface UseMessageQueueReturn {
  queue: string[];
  queueLength: number;
  addToQueue: (message: string) => void;
  removeFromQueue: (index: number) => void;
  clearQueue: () => void;
  moveInQueue: (fromIndex: number, toIndex: number) => void;
}

export function useMessageQueue(
  onSendMessage: (message: string) => void,
  isProcessing: boolean
): UseMessageQueueReturn {
  const [queue, setQueue] = useState<string[]>([]);
  const isProcessingRef = useRef(isProcessing);

  useEffect(() => {
    isProcessingRef.current = isProcessing;
  }, [isProcessing]);

  useEffect(() => {
    if (!isProcessing && queue.length > 0) {
      const [nextMessage, ...rest] = queue;
      setQueue(rest);
      onSendMessage(nextMessage);
    }
  }, [isProcessing, queue, onSendMessage]);

  const addToQueue = useCallback((message: string) => {
    if (message.trim()) {
      setQueue(prev => [...prev, message.trim()]);
    }
  }, []);

  const removeFromQueue = useCallback((index: number) => {
    setQueue(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearQueue = useCallback(() => {
    setQueue([]);
  }, []);

  const moveInQueue = useCallback((fromIndex: number, toIndex: number) => {
    setQueue(prev => {
      const newQueue = [...prev];
      const [removed] = newQueue.splice(fromIndex, 1);
      newQueue.splice(toIndex, 0, removed);
      return newQueue;
    });
  }, []);

  return {
    queue,
    queueLength: queue.length,
    addToQueue,
    removeFromQueue,
    clearQueue,
    moveInQueue,
  };
}
