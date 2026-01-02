import { createContext, useContext, useState, useCallback } from 'react';

const translations = {
  en: {
    // Header
    appName: 'CV Screener',
    appTagline: 'RAG-Powered Analysis',
    addCvs: 'Add CVs',
    
    // Mode Switch
    localMode: 'Local',
    cloudMode: 'Cloud',
    
    // Welcome
    welcomeTitle: "Hi! I'm your CV assistant",
    welcomeSubtitle: "I can help you analyze and compare the CVs you've uploaded. Ask me anything.",
    
    // Suggested Questions
    suggestions: [
      'Who has the most Python experience?',
      'Which candidates have a university degree?',
      'Compare the top 3 candidates',
      'Who has worked at startups?',
    ],
    
    // Chat
    assistant: 'Assistant',
    you: 'You',
    analyzingCvs: 'Analyzing CVs...',
    typeMessage: 'Ask about the CVs...',
    pressEnter: 'Press Enter to send',
    sources: 'Sources',
    relevance: 'Relevance',
    
    // Reasoning
    thinking: 'Thinking',
    reasoning: 'Reasoning',
    embeddingQuery: 'Embedding query...',
    searchingDocs: 'Searching relevant documents...',
    foundChunks: 'Found {n} relevant chunks',
    generatingResponse: 'Generating response...',
    completed: 'Completed',
    
    // Upload
    uploadCvs: 'Upload CVs',
    dragDrop: 'Drag and drop PDF files here',
    orClick: 'or click to select',
    selectedFiles: 'Selected files',
    file: 'file',
    files: 'files',
    upload: 'Upload',
    uploading: 'Uploading...',
    
    // Processing
    processingCvs: 'Processing CVs...',
    processingOf: 'Processing {current} of {total} files',
    progress: 'Progress',
    uploadingFiles: 'Uploading files',
    extractingText: 'Extracting text from PDFs',
    chunkingContent: 'Chunking content',
    generatingEmbeddings: 'Generating embeddings',
    storingVector: 'Storing in vector database',
    
    // Errors
    processingFailed: 'Processing failed',
    noRelevantInfo: "I couldn't find any relevant information in the CVs to answer your question.",
    
    // Tips
    onlyPdf: 'Only PDF',
    multipleFiles: 'Multiple files',
    fastProcess: 'Fast process',
  },
  es: {
    // Header
    appName: 'CV Screener',
    appTagline: 'Análisis con RAG',
    addCvs: 'Añadir CVs',
    
    // Mode Switch
    localMode: 'Local',
    cloudMode: 'Nube',
    
    // Welcome
    welcomeTitle: '¡Hola! Soy tu asistente de CVs',
    welcomeSubtitle: 'Puedo ayudarte a analizar y comparar los CVs que has subido. Pregúntame lo que necesites.',
    
    // Suggested Questions
    suggestions: [
      '¿Quién tiene más experiencia en Python?',
      '¿Qué candidatos tienen título universitario?',
      'Compara los 3 mejores candidatos',
      '¿Quién ha trabajado en startups?',
    ],
    
    // Chat
    assistant: 'Asistente',
    you: 'Tú',
    analyzingCvs: 'Analizando CVs...',
    typeMessage: 'Pregunta sobre los CVs...',
    pressEnter: 'Presiona Enter para enviar',
    sources: 'Fuentes',
    relevance: 'Relevancia',
    
    // Reasoning
    thinking: 'Pensando',
    reasoning: 'Razonamiento',
    embeddingQuery: 'Procesando consulta...',
    searchingDocs: 'Buscando documentos relevantes...',
    foundChunks: 'Encontrados {n} fragmentos relevantes',
    generatingResponse: 'Generando respuesta...',
    completed: 'Completado',
    
    // Upload
    uploadCvs: 'Subir CVs',
    dragDrop: 'Arrastra y suelta archivos PDF aquí',
    orClick: 'o haz clic para seleccionar',
    selectedFiles: 'Archivos seleccionados',
    file: 'archivo',
    files: 'archivos',
    upload: 'Subir',
    uploading: 'Subiendo...',
    
    // Processing
    processingCvs: 'Procesando CVs...',
    processingOf: 'Procesando {current} de {total} archivos',
    progress: 'Progreso',
    uploadingFiles: 'Subiendo archivos',
    extractingText: 'Extrayendo texto de PDFs',
    chunkingContent: 'Fragmentando contenido',
    generatingEmbeddings: 'Generando embeddings',
    storingVector: 'Almacenando en base de datos vectorial',
    
    // Errors
    processingFailed: 'Procesamiento fallido',
    noRelevantInfo: 'No encontré información relevante en los CVs para responder tu pregunta.',
    
    // Tips
    onlyPdf: 'Solo PDF',
    multipleFiles: 'Múltiples archivos',
    fastProcess: 'Proceso rápido',
  },
};

const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    const saved = localStorage.getItem('cv-screener-language');
    return saved || 'es';
  });

  const toggleLanguage = useCallback(() => {
    setLanguage(prev => {
      const newLang = prev === 'en' ? 'es' : 'en';
      localStorage.setItem('cv-screener-language', newLang);
      return newLang;
    });
  }, []);

  const setLang = useCallback((lang) => {
    setLanguage(lang);
    localStorage.setItem('cv-screener-language', lang);
  }, []);

  const t = useCallback((key, params = {}) => {
    let text = translations[language][key] || translations['en'][key] || key;
    Object.entries(params).forEach(([k, v]) => {
      text = text.replace(`{${k}}`, v);
    });
    return text;
  }, [language]);

  return (
    <LanguageContext.Provider value={{ language, setLanguage: setLang, toggleLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}

export default LanguageContext;
