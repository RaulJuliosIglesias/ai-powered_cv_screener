import { useState, useCallback } from 'react';
import { uploadFiles, getProcessingStatus } from '../services/api';

const POLL_INTERVAL = 1000;

export const useUpload = (onComplete) => {
  const [files, setFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState(null);
  const [error, setError] = useState(null);

  const addFiles = useCallback((newFiles) => {
    const pdfFiles = newFiles.filter((file) => file.type === 'application/pdf');
    setFiles((prev) => [...prev, ...pdfFiles]);
    setError(null);
  }, []);

  const removeFile = useCallback((index) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
    setError(null);
  }, []);

  const pollStatus = useCallback(async (jobId) => {
    try {
      const status = await getProcessingStatus(jobId);
      setProcessingStatus(status);

      if (status.status === 'completed' || status.status === 'failed') {
        setIsProcessing(false);
        if (status.status === 'completed') {
          if (onComplete) onComplete();
        } else {
          setError(status.error_message || 'Processing failed');
        }
        return;
      }

      setTimeout(() => pollStatus(jobId), POLL_INTERVAL);
    } catch (err) {
      setError('Failed to check processing status');
      setIsProcessing(false);
    }
  }, [onComplete]);

  const upload = useCallback(async () => {
    if (files.length === 0) {
      setError('No files selected');
      return;
    }

    setIsUploading(true);
    setError(null);

    try {
      const response = await uploadFiles(files, (progress) => {
        setUploadProgress(progress);
      });

      setIsUploading(false);
      setIsProcessing(true);
      setUploadProgress(0);
      setFiles([]);

      pollStatus(response.job_id);
    } catch (err) {
      setIsUploading(false);
      setError(err.response?.data?.detail || 'Upload failed');
    }
  }, [files, pollStatus]);

  const reset = useCallback(() => {
    setFiles([]);
    setIsUploading(false);
    setIsProcessing(false);
    setUploadProgress(0);
    setProcessingStatus(null);
    setError(null);
  }, []);

  return {
    files,
    isUploading,
    isProcessing,
    uploadProgress,
    processingStatus,
    error,
    addFiles,
    removeFile,
    clearFiles,
    upload,
    reset,
  };
};
