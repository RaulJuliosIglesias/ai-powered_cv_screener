import axios, { AxiosProgressEvent } from 'axios';
import type {
  CV,
  CVInfo,
  ChatResponse,
  Session,
  SessionListItem,
  UploadStatus,
  RAGPipelineConfig,
  ModelsResponse,
  DeleteResponse,
} from '@/types';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ============================================
// UPLOAD API FUNCTIONS
// ============================================

export const uploadFiles = async (
  files: File[],
  mode: string = 'local',
  onProgress?: (percent: number) => void
): Promise<UploadStatus> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post<UploadStatus>(`/upload?mode=${mode}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent: AxiosProgressEvent) => {
      if (onProgress && progressEvent.total) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    },
  });

  return response.data;
};

export const getProcessingStatus = async (
  jobId: string,
  mode: string = 'local'
): Promise<UploadStatus> => {
  const response = await api.get<UploadStatus>(`/status/${jobId}?mode=${mode}`);
  return response.data;
};

// ============================================
// CV API FUNCTIONS
// ============================================

export const getCVList = async (
  mode: string = 'local'
): Promise<{ total: number; cvs: CV[] }> => {
  const response = await api.get<{ total: number; cvs: CV[] }>(`/cvs?mode=${mode}`);
  return response.data;
};

export const deleteCV = async (
  cvId: string,
  mode: string = 'local'
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(`/cvs/${cvId}?mode=${mode}`);
  return response.data;
};

export const deleteCVById = async (
  cvId: string,
  mode: string = 'local'
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(`/cvs/${cvId}?mode=${mode}`);
  return response.data;
};

export const deleteAllCVs = async (
  mode: string = 'local'
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(`/cvs?mode=${mode}`);
  return response.data;
};

// ============================================
// CHAT API FUNCTIONS
// ============================================

export const sendMessage = async (
  message: string,
  mode: string = 'local',
  conversationId: string | null = null
): Promise<ChatResponse> => {
  const response = await api.post<ChatResponse>(`/chat?mode=${mode}`, {
    message,
    conversation_id: conversationId,
  });
  return response.data;
};

// ============================================
// STATS & UTILITY API FUNCTIONS
// ============================================

interface StatsResponse {
  total_cvs: number;
  total_chunks: number;
  storage_type: string;
}

export const getStats = async (mode: string = 'local'): Promise<StatsResponse> => {
  const response = await api.get<StatsResponse>(`/stats?mode=${mode}`);
  return response.data;
};

interface WelcomeResponse {
  message: string;
  cv_count: number;
}

export const getWelcomeMessage = async (
  mode: string = 'local'
): Promise<WelcomeResponse> => {
  const response = await api.get<WelcomeResponse>(`/welcome?mode=${mode}`);
  return response.data;
};

interface HealthResponse {
  status: string;
  mode: string;
}

export const healthCheck = async (): Promise<HealthResponse> => {
  const response = await api.get<HealthResponse>('/health');
  return response.data;
};

// ============================================
// MODELS API FUNCTIONS
// ============================================

export const getModels = async (): Promise<ModelsResponse> => {
  const response = await api.get<ModelsResponse>('/models');
  return response.data;
};

export const setModel = async (
  modelId: string
): Promise<{ success: boolean; model: string }> => {
  const response = await api.post<{ success: boolean; model: string }>(
    `/models/${encodeURIComponent(modelId)}`
  );
  return response.data;
};

// ============================================
// SESSION API FUNCTIONS
// ============================================

export const getSessions = async (
  mode: string = 'local'
): Promise<SessionListItem[]> => {
  const response = await api.get<SessionListItem[]>(`/sessions?mode=${mode}`);
  return response.data;
};

export const createSession = async (
  name: string,
  description: string = '',
  mode: string = 'local'
): Promise<Session> => {
  const response = await api.post<Session>(`/sessions?mode=${mode}`, {
    name,
    description,
  });
  return response.data;
};

export const getSession = async (
  sessionId: string,
  mode: string = 'local'
): Promise<Session> => {
  const response = await api.get<Session>(`/sessions/${sessionId}?mode=${mode}`);
  return response.data;
};

export const updateSession = async (
  sessionId: string,
  data: Partial<Session>,
  mode: string = 'local'
): Promise<Session> => {
  const response = await api.put<Session>(
    `/sessions/${sessionId}?mode=${mode}`,
    data
  );
  return response.data;
};

export const deleteSession = async (
  sessionId: string,
  mode: string = 'local'
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(
    `/sessions/${sessionId}?mode=${mode}`
  );
  return response.data;
};

// ============================================
// SESSION CV API FUNCTIONS
// ============================================

export const uploadCVsToSession = async (
  sessionId: string,
  files: File[],
  mode: string = 'local',
  onProgress?: (percent: number) => void
): Promise<UploadStatus> => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post<UploadStatus>(
    `/sessions/${sessionId}/cvs?mode=${mode}`,
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent: AxiosProgressEvent) => {
        if (onProgress && progressEvent.total) {
          const progress = Math.round(
            (progressEvent.loaded * 100) / progressEvent.total
          );
          onProgress(progress);
        }
      },
    }
  );
  return response.data;
};

export const getSessionUploadStatus = async (
  sessionId: string,
  jobId: string
): Promise<UploadStatus> => {
  const response = await api.get<UploadStatus>(
    `/sessions/${sessionId}/cvs/status/${jobId}`
  );
  return response.data;
};

export const removeCVFromSession = async (
  sessionId: string,
  cvId: string,
  mode: string = 'local'
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(
    `/sessions/${sessionId}/cvs/${cvId}?mode=${mode}`
  );
  return response.data;
};

export const clearSessionCVs = async (
  sessionId: string,
  mode: string = 'local'
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(
    `/sessions/${sessionId}/cvs?mode=${mode}`
  );
  return response.data;
};

export const deleteAllCVsFromDatabase = async (
  mode: string = 'local'
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(
    `/sessions/database/all-cvs?mode=${mode}`
  );
  return response.data;
};

// ============================================
// SESSION CHAT API FUNCTIONS
// ============================================

export const sendSessionMessage = async (
  sessionId: string,
  message: string,
  mode: string = 'local',
  pipelineSettings: RAGPipelineConfig | null = null
): Promise<ChatResponse> => {
  const payload: {
    message: string;
    understanding_model?: string;
    generation_model?: string;
  } = { message };

  if (pipelineSettings) {
    payload.understanding_model = pipelineSettings.understanding;
    payload.generation_model = pipelineSettings.generation;
  }

  const response = await api.post<ChatResponse>(
    `/sessions/${sessionId}/chat?mode=${mode}`,
    payload
  );
  return response.data;
};

export const clearSessionChat = async (
  sessionId: string
): Promise<DeleteResponse> => {
  const response = await api.delete<DeleteResponse>(`/sessions/${sessionId}/chat`);
  return response.data;
};

export const getSessionSuggestions = async (
  sessionId: string,
  mode: string = 'local'
): Promise<string[]> => {
  const response = await api.get<string[]>(
    `/sessions/${sessionId}/suggestions?mode=${mode}`
  );
  return response.data;
};

export default api;
