import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadFiles = async (files, mode = 'local', onProgress) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post(`/upload?mode=${mode}`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        onProgress(percentCompleted);
      }
    },
  });

  return response.data;
};

export const getProcessingStatus = async (jobId, mode = 'local') => {
  const response = await api.get(`/status/${jobId}?mode=${mode}`);
  return response.data;
};

export const getCVList = async (mode = 'local') => {
  const response = await api.get(`/cvs?mode=${mode}`);
  return response.data;
};

export const deleteCV = async (cvId, mode = 'local') => {
  const response = await api.delete(`/cvs/${cvId}?mode=${mode}`);
  return response.data;
};

export const sendMessage = async (message, mode = 'local', conversationId = null) => {
  const response = await api.post(`/chat?mode=${mode}`, {
    message,
    conversation_id: conversationId,
  });
  return response.data;
};

export const getStats = async (mode = 'local') => {
  const response = await api.get(`/stats?mode=${mode}`);
  return response.data;
};

export const getWelcomeMessage = async (mode = 'local') => {
  const response = await api.get(`/welcome?mode=${mode}`);
  return response.data;
};

export const healthCheck = async () => {
  const response = await api.get('/health');
  return response.data;
};

export const getModels = async () => {
  const response = await api.get('/models');
  return response.data;
};

export const setModel = async (modelId) => {
  const response = await api.post(`/models/${encodeURIComponent(modelId)}`);
  return response.data;
};

export const deleteCVById = async (cvId, mode = 'local') => {
  const response = await api.delete(`/cvs/${cvId}?mode=${mode}`);
  return response.data;
};

export const deleteAllCVs = async (mode = 'local') => {
  const response = await api.delete(`/cvs?mode=${mode}`);
  return response.data;
};

// ============================================
// SESSION API FUNCTIONS
// ============================================

export const getSessions = async (mode = 'local') => {
  const response = await api.get(`/sessions?mode=${mode}`);
  return response.data;
};

export const createSession = async (name, description = '', mode = 'local') => {
  const response = await api.post(`/sessions?mode=${mode}`, { name, description });
  return response.data;
};

export const getSession = async (sessionId, mode = 'local') => {
  const response = await api.get(`/sessions/${sessionId}?mode=${mode}`);
  return response.data;
};

export const updateSession = async (sessionId, data, mode = 'local') => {
  const response = await api.put(`/sessions/${sessionId}?mode=${mode}`, data);
  return response.data;};

export const deleteSession = async (sessionId, mode = 'local') => {
  const response = await api.delete(`/sessions/${sessionId}?mode=${mode}`);
  return response.data;
};

export const uploadCVsToSession = async (sessionId, files, mode = 'local', onProgress) => {
  const formData = new FormData();
  files.forEach((file) => {
    formData.append('files', file);
  });

  const response = await api.post(`/sessions/${sessionId}/cvs?mode=${mode}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (progressEvent) => {
      if (onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onProgress(progress);
      }
    },
  });
  return response.data;
};

export const getSessionUploadStatus = async (sessionId, jobId) => {
  const response = await api.get(`/sessions/${sessionId}/cvs/status/${jobId}`);
  return response.data;
};

export const removeCVFromSession = async (sessionId, cvId, mode = 'local') => {
  const response = await api.delete(`/sessions/${sessionId}/cvs/${cvId}?mode=${mode}`);
  return response.data;
};

export const sendSessionMessage = async (sessionId, message, mode = 'local') => {
  const response = await api.post(`/sessions/${sessionId}/chat?mode=${mode}`, { message });
  return response.data;
};

export const clearSessionChat = async (sessionId) => {
  const response = await api.delete(`/sessions/${sessionId}/chat`);
  return response.data;
};

export const getSessionSuggestions = async (sessionId, mode = 'local') => {
  const response = await api.get(`/sessions/${sessionId}/suggestions?mode=${mode}`);
  return response.data;
};

export default api;
