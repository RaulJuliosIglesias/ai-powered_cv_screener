import { memo } from 'react';
import { X, Sparkles, Github, Linkedin, ExternalLink } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

const AboutModal = memo(({ isOpen, onClose }) => {
  const { language } = useLanguage();

  if (!isOpen) return null;

  return (
    <div 
      className="modal-overlay overlay-enter" 
      onClick={onClose}
      role="dialog" 
      aria-modal="true" 
      aria-labelledby="about-title"
    >
      <div 
        className="modal-content modal-enter w-full max-w-md"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-purple-500 to-blue-600 rounded-xl">
              <Sparkles className="w-5 h-5 text-white" aria-hidden="true" />
            </div>
            <h2 id="about-title" className="text-xl font-semibold text-primary">
              {language === 'es' ? 'Acerca de' : 'About'}
            </h2>
          </div>
          <button 
            onClick={onClose} 
            className="btn-icon focus-ring"
            aria-label={language === 'es' ? 'Cerrar' : 'Close'}
          >
            <X className="w-5 h-5 text-muted" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-5">
          {/* App Info */}
          <div className="text-center">
            <h3 className="text-lg font-bold text-primary">AI CV Screener</h3>
            <div className="flex items-center justify-center gap-2 mt-2">
              <span className="px-2 py-1 bg-slate-100 dark:bg-slate-700 rounded text-sm font-medium text-secondary">
                v1.0.0
              </span>
              <span className="px-2 py-1 bg-gradient-to-r from-purple-500 to-emerald-500 text-white text-sm font-bold rounded">
                RAG V5
              </span>
            </div>
            <p className="text-sm text-muted mt-3">
              {language === 'es' 
                ? 'Sistema inteligente de análisis de CVs con RAG Pipeline avanzado' 
                : 'Intelligent CV analysis system with advanced RAG Pipeline'}
            </p>
          </div>

          <div className="border-t border-slate-200 dark:border-slate-700" />

          {/* Creator */}
          <div>
            <p className="text-xs text-muted uppercase tracking-wide mb-2">
              {language === 'es' ? 'Creado por' : 'Created by'}
            </p>
            <p className="font-semibold text-primary">Raúl Iglesias Julios</p>
          </div>

          {/* Social Links */}
          <div className="flex flex-col gap-2">
            <a
              href="https://github.com/RaulJuliosIglesias"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-colors group focus-ring"
            >
              <Github className="w-5 h-5 text-slate-700 dark:text-slate-300" aria-hidden="true" />
              <span className="flex-1 text-sm font-medium text-secondary">GitHub</span>
              <ExternalLink className="w-4 h-4 text-muted group-hover:text-blue-500" aria-hidden="true" />
            </a>
            <a
              href="https://www.linkedin.com/in/rauliglesiasjulios/"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-700/50 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-colors group focus-ring"
            >
              <Linkedin className="w-5 h-5 text-blue-600" aria-hidden="true" />
              <span className="flex-1 text-sm font-medium text-secondary">LinkedIn</span>
              <ExternalLink className="w-4 h-4 text-muted group-hover:text-blue-500" aria-hidden="true" />
            </a>
          </div>

          {/* Copyright */}
          <p className="text-xs text-center text-muted">
            © 2026 - {language === 'es' ? 'Todos los derechos reservados' : 'All rights reserved'}
          </p>
        </div>
      </div>
    </div>
  );
});

AboutModal.displayName = 'AboutModal';

export default AboutModal;
