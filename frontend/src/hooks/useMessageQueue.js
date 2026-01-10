import { useState, useCallback, useEffect, useRef } from 'react';

export function useMessageQueue(onSendMessage, isProcessing) {
  const [queue, setQueue] = useState([]);
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

  const addToQueue = useCallback((message) => {
    if (message.trim()) {
      setQueue(prev => [...prev, message.trim()]);
    }
  }, []);

  const removeFromQueue = useCallback((index) => {
    setQueue(prev => prev.filter((_, i) => i !== index));
  }, []);

  const clearQueue = useCallback(() => {
    setQueue([]);
  }, []);

  const moveInQueue = useCallback((fromIndex, toIndex) => {
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
