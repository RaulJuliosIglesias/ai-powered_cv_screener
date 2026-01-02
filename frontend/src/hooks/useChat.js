import { useState, useCallback, useRef } from 'react';
import { sendMessage } from '../services/api';

export function useChat(mode = 'local') {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [conversationId, setConversationId] = useState(null);
  const [lastMetrics, setLastMetrics] = useState(null);
  const [reasoningSteps, setReasoningSteps] = useState([]);
  const [showReasoning, setShowReasoning] = useState(true);

  const simulateReasoningSteps = useCallback((language = 'es') => {
    const steps = language === 'es' ? [
      { text: 'Procesando consulta...', status: 'pending' },
      { text: 'Buscando documentos relevantes...', status: 'pending' },
      { text: 'Analizando fragmentos encontrados...', status: 'pending' },
      { text: 'Generando respuesta...', status: 'pending' },
    ] : [
      { text: 'Embedding query...', status: 'pending' },
      { text: 'Searching relevant documents...', status: 'pending' },
      { text: 'Analyzing found chunks...', status: 'pending' },
      { text: 'Generating response...', status: 'pending' },
    ];

    setReasoningSteps(steps);

    // Simulate step progression
    const delays = [300, 800, 1500, 2500];
    delays.forEach((delay, index) => {
      setTimeout(() => {
        setReasoningSteps(prev => prev.map((step, i) => ({
          ...step,
          status: i < index ? 'done' : i === index ? 'active' : 'pending'
        })));
      }, delay);
    });
  }, []);

  const send = useCallback(async (message, language = 'es') => {
    if (!message.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    
    // Start reasoning animation if enabled
    if (showReasoning) {
      simulateReasoningSteps(language);
    }

    try {
      const response = await sendMessage(message, mode, conversationId);
      
      // Mark all steps as done
      setReasoningSteps(prev => prev.map(step => ({ ...step, status: 'done' })));
      
      const assistantMessage = {
        id: Date.now() + 1,
        role: 'assistant',
        content: response.response,
        sources: response.sources || [],
        metrics: response.metrics,
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setConversationId(response.conversation_id);
      setLastMetrics(response.metrics);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send message');
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
      setReasoningSteps([]);
    }
  }, [mode, conversationId, isLoading, showReasoning, simulateReasoningSteps]);

  const addMessage = useCallback((message) => {
    setMessages(prev => [...prev, {
      id: Date.now(),
      timestamp: new Date().toISOString(),
      ...message,
    }]);
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setConversationId(null);
    setError(null);
    setLastMetrics(null);
    setReasoningSteps([]);
  }, []);

  const retry = useCallback(async () => {
    const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
    if (lastUserMessage) {
      setMessages(prev => prev.filter(m => m.id !== lastUserMessage.id));
      await send(lastUserMessage.content);
    }
  }, [messages, send]);

  const toggleReasoning = useCallback(() => {
    setShowReasoning(prev => !prev);
  }, []);

  return {
    messages,
    isLoading,
    error,
    conversationId,
    lastMetrics,
    reasoningSteps,
    showReasoning,
    send,
    addMessage,
    clearMessages,
    retry,
    toggleReasoning,
  };
}
