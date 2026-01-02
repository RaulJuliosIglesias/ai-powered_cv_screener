import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

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

export default api;
