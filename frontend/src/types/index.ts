/**
 * TypeScript type definitions for CV Screener
 */

// ============================================
// CV Types
// ============================================

export interface CV {
  id: string;
  filename: string;
  chunk_count: number;
  indexed_at: string;
  metadata?: Record<string, unknown>;
}

export interface CVInfo {
  cv_id: string;
  filename: string;
  chunk_count?: number;
}

// ============================================
// Message Types
// ============================================

export interface Source {
  cv_id: string;
  filename: string;
  relevance?: number;
  chunk_index?: number;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  timestamp?: Date;
  isError?: boolean;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
}

// ============================================
// API Response Types
// ============================================

export interface Metrics {
  understanding_ms?: number;
  embedding_ms: number;
  search_ms: number;
  llm_ms: number;
  total_ms: number;
  confidence_score?: number;
}

export interface QueryUnderstanding {
  understood_query?: string;
  query_type?: string;
  requirements?: string[];
}

export interface ChatResponse {
  response: string;
  sources: Source[];
  metrics: Metrics;
  confidence_score?: number;
  guardrail_passed?: boolean;
  query_understanding?: QueryUnderstanding;
  conversation_id?: string;
}

export interface UploadStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'completed_with_errors' | 'failed';
  total_files: number;
  processed_files: number;
  errors: string[];
  cvs?: CVInfo[];
  error_message?: string;
  current_file?: string;
  current_phase?: string;
}

// ============================================
// Session Types
// ============================================

export interface Session {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  cvs?: CVInfo[];
  messages?: ChatMessage[];
}

export interface SessionListItem {
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  cv_count: number;
}

// ============================================
// RAG Pipeline Types
// ============================================

export interface RAGPipelineConfig {
  understanding: string;  // Model for step 1: Query Understanding
  generation: string;     // Model for step 2: Response Generation
}

export interface Model {
  id: string;
  name: string;
  description?: string;
  context_length: number;
  pricing?: {
    prompt: string;
    completion: string;
  };
  pricing_raw?: {
    prompt: number;
    completion: number;
  };
  is_free?: boolean;
  is_reasoning?: boolean;
}

export interface ModelsResponse {
  models: Model[];
  total: number;
}

// ============================================
// Upload Types
// ============================================

export interface UploadProgress {
  files: string[];
  current: number;
  total: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  logs: string[];
  percent?: number;
}

export interface DeleteProgress {
  current: number;
  total: number;
  status: 'deleting' | 'completed' | 'error';
  logs: string[];
  percent?: number;
}

// ============================================
// Theme and Mode Types
// ============================================

export type Theme = 'light' | 'dark';
export type AppMode = 'local' | 'cloud';

// ============================================
// Component Props Types
// ============================================

export interface RAGPipelineSettingsProps {
  isOpen: boolean;
  onClose: () => void;
  onSave?: (settings: RAGPipelineConfig) => void;
}

export interface ModelSelectorProps {
  value?: string;
  onChange?: (modelId: string) => void;
  className?: string;
}

export interface SourceBadgeProps {
  source: Source;
  onClick?: (cvId: string, filename: string) => void;
}

// ============================================
// API Function Types
// ============================================

export interface CVListResponse {
  total: number;
  cvs: CV[];
}

export interface DeleteResponse {
  success: boolean;
  message?: string;
}

export interface CreateSessionResponse {
  id: string;
  name: string;
  created_at: string;
}

// ============================================
// Streaming & Pipeline Types
// ============================================

export type QueryType =
  | 'single_candidate'
  | 'comparison'
  | 'ranking'
  | 'talent_pool'
  | 'skills_search'
  | 'experience_filter'
  | 'gap_analysis'
  | 'red_flags'
  | 'general';

export interface PipelineStep {
  step: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  duration_ms?: number;
  message?: string;
}

export interface PipelineSettings {
  understanding: string;
  reranking: string;
  reranking_enabled: boolean;
  generation: string;
  verification: string;
  verification_enabled: boolean;
}

export interface StreamingState {
  currentStep: string;
  steps: Record<string, PipelineStep>;
  queryUnderstanding: QueryUnderstanding | null;
  candidates: CandidatePreview[];
  partialAnswer: string | null;
}

export interface CandidatePreview {
  cv_id: string;
  filename: string;
  relevance_score?: number;
}

// ============================================
// Structured Output Types
// ============================================

export interface StructuredOutput {
  query_type: QueryType;
  structure_name: string;
  modules: ModuleOutput[];
  metadata?: OutputMetadata;
}

export interface ModuleOutput {
  module_name: string;
  data: Record<string, unknown>;
  confidence?: number;
}

export interface OutputMetadata {
  total_candidates?: number;
  analysis_depth?: string;
  generated_at?: string;
}

// ============================================
// Token & Cost Types
// ============================================

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost?: number;
}

export interface StageMetric {
  stage: string;
  duration_ms: number;
  success: boolean;
  tokens?: TokenUsage;
}

export interface PipelineMetrics {
  total_duration_ms: number;
  stages: StageMetric[];
  tokens_used?: TokenUsage;
  cache_hit?: boolean;
}

// ============================================
// Reasoning Step Types
// ============================================

export interface ReasoningStep {
  text: string;
  status: 'pending' | 'active' | 'done';
}

// ============================================
// Chat Hook Types
// ============================================

export interface UseChatOptions {
  mode?: AppMode;
}

export interface UseChatReturn {
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

// ============================================
// Upload Hook Types
// ============================================

export interface UseUploadOptions {
  sessionId: string;
  mode?: AppMode;
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export interface UseUploadReturn {
  upload: (files: File[]) => Promise<void>;
  isUploading: boolean;
  progress: UploadProgress | null;
  error: string | null;
  reset: () => void;
}
