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
}

export interface UploadStatus {
  job_id: string;
  status: 'processing' | 'completed' | 'failed';
  total_files: number;
  processed_files: number;
  errors: string[];
  cvs?: CVInfo[];
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
