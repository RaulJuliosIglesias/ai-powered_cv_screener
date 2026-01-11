import { useState, useCallback, useRef } from 'react';
import { uploadFiles, getProcessingStatus, uploadCVsToSession, getSessionUploadStatus } from '../services/api';
import type { AppMode, UploadStatus } from '@/types';

const POLL_INTERVAL = 300;

interface ProgressModal {
  files: string[];
  current: number;
  total: number;
  percent: number;
  status: 'uploading' | 'processing' | 'completed' | 'error';
  logs: string[];
}

interface UseUploadReturn {
  files: File[];
  isUploading: boolean;
  isProcessing: boolean;
  uploadProgress: number;
  processingStatus: UploadStatus | null;
  progressModal: ProgressModal | null;
  error: string | null;
  addFiles: (newFiles: File[]) => void;
  removeFile: (index: number) => void;
  clearFiles: () => void;
  upload: () => Promise<void>;
  uploadToSession: (sessionId: string, filesToUpload?: File[], language?: string) => Promise<void>;
  closeProgressModal: () => void;
  reset: () => void;
}

export const useUpload = (onComplete?: () => void, mode: AppMode = 'local'): UseUploadReturn => {
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [processingStatus, setProcessingStatus] = useState<UploadStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [progressModal, setProgressModal] = useState<ProgressModal | null>(null);
  const modeRef = useRef(mode);
  modeRef.current = mode;

  const addFiles = useCallback((newFiles: File[]) => {
    const pdfFiles = newFiles.filter((file) => file.type === 'application/pdf');
    setFiles((prev) => [...prev, ...pdfFiles]);
    setError(null);
  }, []);

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const clearFiles = useCallback(() => {
    setFiles([]);
    setError(null);
  }, []);

  const pollStatus = useCallback(async (jobId: string) => {
    try {
      const status = await getProcessingStatus(jobId, modeRef.current);
      setProcessingStatus(status);

      if (status.status === 'completed' || status.status === 'completed_with_errors' || status.status === 'failed') {
        setIsProcessing(false);
        if (status.status === 'completed' || status.status === 'completed_with_errors') {
          if (onComplete) onComplete();
        } else {
          setError(status.error_message || 'Processing failed');
        }
        return;
      }

      setTimeout(() => pollStatus(jobId), POLL_INTERVAL);
    } catch {
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
      const response = await uploadFiles(files, modeRef.current, (progress: number) => {
        setUploadProgress(progress);
      });

      setIsUploading(false);
      setIsProcessing(true);
      setUploadProgress(0);
      setFiles([]);

      pollStatus(response.job_id);
    } catch (err: unknown) {
      setIsUploading(false);
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setError(errorMessage);
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

  const uploadToSession = useCallback(async (sessionId: string, filesToUpload?: File[], language: string = 'en') => {
    const targetFiles = filesToUpload || files;
    if (targetFiles.length === 0 || !sessionId) return;

    const fileNames = targetFiles.map(f => f.name);
    
    setProgressModal({
      files: fileNames,
      current: 0,
      total: targetFiles.length,
      percent: 0,
      status: 'uploading',
      logs: [language === 'es' ? `Subiendo ${targetFiles.length} archivo(s)...` : `Uploading ${targetFiles.length} file(s)...`]
    });

    setIsUploading(true);
    setError(null);

    try {
      const res = await uploadCVsToSession(sessionId, targetFiles, modeRef.current, (uploadPercent: number) => {
        const realPercent = Math.round(uploadPercent * 0.5);
        setProgressModal(prev => prev ? { ...prev, percent: realPercent } : null);
      });

      let lastProcessed = 0;
      let lastPhase = '';
      const phaseNames: Record<string, string> = {
        extracting: language === 'es' ? 'Extrayendo texto' : 'Extracting text',
        saving: language === 'es' ? 'Guardando PDF' : 'Saving PDF',
        chunking: language === 'es' ? 'Dividiendo en chunks' : 'Chunking',
        embedding: language === 'es' ? 'Creando embeddings' : 'Creating embeddings',
        indexing: language === 'es' ? 'Indexando' : 'Indexing',
        done: language === 'es' ? 'Completado' : 'Done'
      };

      const poll = async () => {
        try {
          const status = await getSessionUploadStatus(sessionId, res.job_id);
          const processed = status.processed_files || 0;
          const currentFile = status.current_file;
          const currentPhase = status.current_phase;

          const phaseProgress: Record<string, number> = { extracting: 10, saving: 20, chunking: 40, embedding: 80, indexing: 95, done: 100 };
          const fileProgress = processed / targetFiles.length;
          const currentFileProgress = currentPhase ? (phaseProgress[currentPhase] || 0) / 100 / targetFiles.length : 0;
          const totalProgress = 50 + ((fileProgress + currentFileProgress) * 50);

          if (status.status === 'processing') {
            setProgressModal(prev => {
              if (!prev) return null;
              const newLogs = [...prev.logs];
              
              if (currentFile && currentPhase && currentPhase !== lastPhase) {
                const phaseName = phaseNames[currentPhase] || currentPhase;
                const shortName = currentFile.length > 25 ? currentFile.slice(0, 22) + '...' : currentFile;
                newLogs.push(`${phaseName}: ${shortName}`);
                lastPhase = currentPhase;
              }
              
              if (processed > lastProcessed) {
                const completedFile = fileNames[processed - 1] || `CV ${processed}`;
                const shortName = completedFile.length > 25 ? completedFile.slice(0, 22) + '...' : completedFile;
                newLogs.push(language === 'es' ? `✓ Completado: ${shortName}` : `✓ Done: ${shortName}`);
                lastProcessed = processed;
              }
              
              return {
                ...prev,
                current: processed,
                percent: Math.min(99, Math.round(totalProgress)),
                status: 'processing',
                logs: newLogs.slice(-6)
              };
            });
            setTimeout(poll, POLL_INTERVAL);
          } else {
            setProgressModal(prev => prev ? {
              ...prev,
              status: 'completed',
              current: targetFiles.length,
              percent: 100,
              logs: [...(prev.logs || []).slice(-5), language === 'es' ? '✓ ¡Todo completado!' : '✓ All completed!']
            } : null);
            setTimeout(() => setProgressModal(null), 1200);
            setIsUploading(false);
            setFiles([]);
            if (onComplete) onComplete();
          }
        } catch {
          setError('Failed to check processing status');
          setIsUploading(false);
          setProgressModal(null);
        }
      };

      setProgressModal(prev => prev ? {
        ...prev,
        percent: 50,
        status: 'processing',
        logs: [...(prev.logs || []), language === 'es' ? 'Procesando archivos...' : 'Processing files...']
      } : null);
      poll();
    } catch (err: unknown) {
      setIsUploading(false);
      const errorMessage = err instanceof Error ? err.message : 'Upload failed';
      setProgressModal(prev => prev ? { ...prev, status: 'error', logs: [...(prev.logs || []), `Error: ${errorMessage}`] } : null);
      setTimeout(() => setProgressModal(null), 3000);
      setError(errorMessage);
    }
  }, [files, onComplete]);

  const closeProgressModal = useCallback(() => {
    setProgressModal(null);
  }, []);

  return {
    files,
    isUploading,
    isProcessing,
    uploadProgress,
    processingStatus,
    progressModal,
    error,
    addFiles,
    removeFile,
    clearFiles,
    upload,
    uploadToSession,
    closeProgressModal,
    reset,
  };
};
