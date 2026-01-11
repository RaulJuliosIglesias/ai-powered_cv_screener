import { useState, useCallback, useRef } from 'react';
import { sendMessage } from '../services/api';
import type { Message, Metrics, ReasoningStep, AppMode } from '@/types';

interface UseChatReturn {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  conversationId: string | null;
  lastMetrics: Metrics | null;
  reasoningSteps: ReasoningStep[];
  showReasoning: boolean;
  send: (message: string, language?: string) => Promise<void>;
  addMessage: (message: Partial<Message>) => void;
  clearMessages: () => void;
  retry: () => Promise<void>;
  toggleReasoning: () => void;
}

export function useChat(mode: AppMode = 'local'): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [lastMetrics, setLastMetrics] = useState<Metrics | null>(null);
  const [reasoningSteps, setReasoningSteps] = useState<ReasoningStep[]>([]);
  const [showReasoning, setShowReasoning] = useState(true);

  const simulateReasoningSteps = useCallback((language: string = 'es') => {
    const steps: ReasoningStep[] = language === 'es' ? [
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

  const send = useCallback(async (message: string, language: string = 'es') => {
    if (!message.trim() || isLoading) return;

    const userMessage: Message = {
      id: String(Date.now()),
      role: 'user',
      content: message,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);
    
    if (showReasoning) {
      simulateReasoningSteps(language);
    }

    try {
      const response = await sendMessage(message, mode, conversationId);
      
      setReasoningSteps(prev => prev.map(step => ({ ...step, status: 'done' })));
      
      const assistantMessage: Message = {
        id: String(Date.now() + 1),
        role: 'assistant',
        content: response.response,
        sources: response.sources || [],
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);
      setConversationId(response.conversation_id ?? null);
      setLastMetrics(response.metrics);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to send message';
      setError(errorMessage);
      setMessages(prev => prev.filter(m => m.id !== userMessage.id));
    } finally {
      setIsLoading(false);
      setReasoningSteps([]);
    }
  }, [mode, conversationId, isLoading, showReasoning, simulateReasoningSteps]);

  const addMessage = useCallback((message: Partial<Message>) => {
    setMessages(prev => [...prev, {
      id: String(Date.now()),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      ...message,
    } as Message]);
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
