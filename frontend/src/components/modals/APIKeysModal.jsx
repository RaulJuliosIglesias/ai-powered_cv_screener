import { memo, useState, useEffect } from 'react';
import { X, Key, Eye, EyeOff, AlertCircle, CheckCircle2, ExternalLink, Sparkles, Cpu, Shield, Loader2 } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

const STORAGE_KEY = 'cv_screener_settings';

export const getAPIKeys = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const settings = JSON.parse(saved);
      return {
        openRouterApiKey: settings.openRouterApiKey || '',
        huggingFaceApiKey: settings.huggingFaceApiKey || '',
      };
    }
  } catch (e) {
    console.error('Failed to get API keys:', e);
  }
  return { openRouterApiKey: '', huggingFaceApiKey: '' };
};

export const saveAPIKeys = (keys) => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    const current = saved ? JSON.parse(saved) : {};
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      ...current,
      ...keys,
    }));
  } catch (e) {
    console.error('Failed to save API keys:', e);
  }
};

export const hasRequiredAPIKeys = () => {
  const keys = getAPIKeys();
  return !!(keys.openRouterApiKey && keys.openRouterApiKey.length > 10);
};

const APIKeysModal = memo(({ isOpen, onClose, onSave, isRequired = false }) => {
  const { language } = useLanguage();
  const [keys, setKeys] = useState(getAPIKeys());
  const [showOpenRouter, setShowOpenRouter] = useState(false);
  const [showHuggingFace, setShowHuggingFace] = useState(false);
  const [openRouterStatus, setOpenRouterStatus] = useState(null);
  const [huggingFaceStatus, setHuggingFaceStatus] = useState(null);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setKeys(getAPIKeys());
      setOpenRouterStatus(null);
      setHuggingFaceStatus(null);
      setShowOpenRouter(false);
      setShowHuggingFace(false);
    }
  }, [isOpen]);

  const validateOpenRouterKey = async (apiKey) => {
    if (!apiKey || apiKey.length < 10) {
      setOpenRouterStatus(null);
      return;
    }
    setOpenRouterStatus('checking');
    try {
      const response = await fetch('/api/validate-api-key', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-OpenRouter-Key': apiKey,
        },
      });
      setOpenRouterStatus(response.ok ? 'valid' : 'invalid');
    } catch (e) {
      setOpenRouterStatus('invalid');
    }
  };

  const validateHuggingFaceKey = async (apiKey) => {
    if (!apiKey || apiKey.length < 10) {
      setHuggingFaceStatus(null);
      return;
    }
    setHuggingFaceStatus('checking');
    try {
      const response = await fetch('https://huggingface.co/api/whoami-v2', {
        headers: {
          'Authorization': `Bearer ${apiKey}`,
        },
      });
      setHuggingFaceStatus(response.ok ? 'valid' : 'invalid');
    } catch (e) {
      setHuggingFaceStatus('invalid');
    }
  };

  const handleOpenRouterChange = (value) => {
    setKeys(k => ({ ...k, openRouterApiKey: value }));
    if (value.length >= 10) {
      const timer = setTimeout(() => validateOpenRouterKey(value), 500);
      return () => clearTimeout(timer);
    } else {
      setOpenRouterStatus(null);
    }
  };

  const handleHuggingFaceChange = (value) => {
    setKeys(k => ({ ...k, huggingFaceApiKey: value }));
    if (value.length >= 10) {
      const timer = setTimeout(() => validateHuggingFaceKey(value), 500);
      return () => clearTimeout(timer);
    } else {
      setHuggingFaceStatus(null);
    }
  };

  const handleSave = async () => {
    if (!keys.openRouterApiKey || keys.openRouterApiKey.length < 10) {
      setOpenRouterStatus('invalid');
      return;
    }
    
    setIsSaving(true);
    saveAPIKeys(keys);
    
    setTimeout(() => {
      setIsSaving(false);
      if (onSave) onSave(keys);
      onClose();
    }, 500);
  };

  const canClose = !isRequired || hasRequiredAPIKeys();

  if (!isOpen) return null;

  return (
    <div 
      className="modal-overlay overlay-enter fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4" 
      onClick={canClose ? onClose : undefined}
      role="dialog" 
      aria-modal="true" 
      aria-labelledby="apikeys-title"
    >
      <div 
        className="modal-content modal-enter w-full max-w-xl bg-white dark:bg-slate-800 rounded-2xl shadow-2xl overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header with gradient */}
        <div className="relative bg-gradient-to-r from-blue-600 via-purple-600 to-pink-500 p-6">
          <div className="absolute inset-0 bg-black/10" />
          <div className="relative flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-white/20 backdrop-blur-sm rounded-xl">
                <Key className="w-6 h-6 text-white" aria-hidden="true" />
              </div>
              <div>
                <h2 id="apikeys-title" className="text-xl font-bold text-white">
                  {language === 'es' ? 'Configurar API Keys' : 'Configure API Keys'}
                </h2>
                <p className="text-sm text-white/80">
                  {language === 'es' ? 'Necesario para usar la plataforma' : 'Required to use the platform'}
                </p>
              </div>
            </div>
            {canClose && (
              <button 
                onClick={onClose} 
                className="p-2 hover:bg-white/20 rounded-lg transition-colors"
                aria-label={language === 'es' ? 'Cerrar' : 'Close'}
              >
                <X className="w-5 h-5 text-white" />
              </button>
            )}
          </div>
        </div>

        {/* Required Notice */}
        {isRequired && !hasRequiredAPIKeys() && (
          <div className="mx-6 mt-4 p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-amber-700 dark:text-amber-300">
              {language === 'es' 
                ? 'Debes configurar al menos la API key de OpenRouter para usar el chat. Es gratis y solo toma un minuto.' 
                : 'You must configure at least the OpenRouter API key to use the chat. It\'s free and takes just a minute.'}
            </p>
          </div>
        )}
        
        {/* Content */}
        <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
          {/* OpenRouter Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                  <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-white">
                    OpenRouter API Key
                    <span className="ml-2 text-xs font-normal text-red-500">*</span>
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {language === 'es' ? 'Requerido - Para modelos de IA' : 'Required - For AI models'}
                  </p>
                </div>
              </div>
              <a
                href="https://openrouter.ai/keys"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-lg text-xs font-medium hover:bg-purple-200 dark:hover:bg-purple-900/50 transition-colors"
              >
                {language === 'es' ? 'Obtener API Key' : 'Get API Key'}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            
            <div className="relative">
              <input
                type={showOpenRouter ? 'text' : 'password'}
                value={keys.openRouterApiKey || ''}
                onChange={(e) => handleOpenRouterChange(e.target.value)}
                placeholder="sk-or-v1-..."
                className={`w-full p-3 pr-24 bg-slate-50 dark:bg-slate-900 border rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all text-slate-900 dark:text-white placeholder-slate-400 ${
                  openRouterStatus === 'invalid' ? 'border-red-300 dark:border-red-700' : 'border-slate-200 dark:border-slate-700'
                }`}
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {openRouterStatus === 'checking' && (
                  <Loader2 className="w-5 h-5 text-purple-500 animate-spin" />
                )}
                {openRouterStatus === 'valid' && (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                )}
                {openRouterStatus === 'invalid' && (
                  <AlertCircle className="w-5 h-5 text-red-500" />
                )}
                <button
                  type="button"
                  onClick={() => setShowOpenRouter(!showOpenRouter)}
                  className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  {showOpenRouter ? (
                    <EyeOff className="w-4 h-4 text-slate-400" />
                  ) : (
                    <Eye className="w-4 h-4 text-slate-400" />
                  )}
                </button>
              </div>
            </div>
            
            {openRouterStatus === 'valid' && (
              <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                {language === 'es' ? 'API key válida y funcionando' : 'API key valid and working'}
              </p>
            )}
            {openRouterStatus === 'invalid' && (
              <p className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                {language === 'es' ? 'API key inválida - verifica que sea correcta' : 'Invalid API key - please verify it\'s correct'}
              </p>
            )}
          </div>

          <div className="border-t border-slate-200 dark:border-slate-700" />

          {/* HuggingFace Section */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
                  <Cpu className="w-4 h-4 text-yellow-600 dark:text-yellow-400" />
                </div>
                <div>
                  <h3 className="font-semibold text-slate-900 dark:text-white">
                    HuggingFace API Key
                    <span className="ml-2 text-xs font-normal text-slate-400">{language === 'es' ? '(opcional)' : '(optional)'}</span>
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    {language === 'es' ? 'Para funciones avanzadas de NLP' : 'For advanced NLP features'}
                  </p>
                </div>
              </div>
              <a
                href="https://huggingface.co/settings/tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded-lg text-xs font-medium hover:bg-yellow-200 dark:hover:bg-yellow-900/50 transition-colors"
              >
                {language === 'es' ? 'Obtener API Key' : 'Get API Key'}
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            
            <div className="relative">
              <input
                type={showHuggingFace ? 'text' : 'password'}
                value={keys.huggingFaceApiKey || ''}
                onChange={(e) => handleHuggingFaceChange(e.target.value)}
                placeholder="hf_..."
                className={`w-full p-3 pr-24 bg-slate-50 dark:bg-slate-900 border rounded-xl focus:ring-2 focus:ring-yellow-500 focus:border-transparent transition-all text-slate-900 dark:text-white placeholder-slate-400 ${
                  huggingFaceStatus === 'invalid' ? 'border-red-300 dark:border-red-700' : 'border-slate-200 dark:border-slate-700'
                }`}
              />
              <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                {huggingFaceStatus === 'checking' && (
                  <Loader2 className="w-5 h-5 text-yellow-500 animate-spin" />
                )}
                {huggingFaceStatus === 'valid' && (
                  <CheckCircle2 className="w-5 h-5 text-green-500" />
                )}
                {huggingFaceStatus === 'invalid' && (
                  <AlertCircle className="w-5 h-5 text-red-500" />
                )}
                <button
                  type="button"
                  onClick={() => setShowHuggingFace(!showHuggingFace)}
                  className="p-1.5 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-lg transition-colors"
                >
                  {showHuggingFace ? (
                    <EyeOff className="w-4 h-4 text-slate-400" />
                  ) : (
                    <Eye className="w-4 h-4 text-slate-400" />
                  )}
                </button>
              </div>
            </div>
            
            {huggingFaceStatus === 'valid' && (
              <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                {language === 'es' ? 'API key válida y funcionando' : 'API key valid and working'}
              </p>
            )}
            {huggingFaceStatus === 'invalid' && (
              <p className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1">
                <AlertCircle className="w-3 h-3" />
                {language === 'es' ? 'API key inválida - verifica que sea correcta' : 'Invalid API key - please verify it\'s correct'}
              </p>
            )}
          </div>

          {/* Security Note */}
          <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-xl flex items-start gap-3">
            <Shield className="w-5 h-5 text-slate-400 flex-shrink-0 mt-0.5" />
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {language === 'es' 
                ? 'Tus API keys se guardan localmente en tu navegador y nunca se envían a nuestros servidores. Solo se usan para comunicarse directamente con OpenRouter y HuggingFace.' 
                : 'Your API keys are stored locally in your browser and are never sent to our servers. They are only used to communicate directly with OpenRouter and HuggingFace.'}
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900/50 flex justify-end gap-3">
          {canClose && (
            <button
              onClick={onClose}
              className="px-4 py-2.5 text-slate-700 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 rounded-xl transition-colors font-medium"
            >
              {language === 'es' ? 'Cancelar' : 'Cancel'}
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={isSaving || !keys.openRouterApiKey || keys.openRouterApiKey.length < 10}
            className="px-6 py-2.5 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-slate-400 disabled:to-slate-500 disabled:cursor-not-allowed text-white rounded-xl transition-all font-medium flex items-center gap-2 shadow-lg shadow-purple-500/25"
          >
            {isSaving ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                {language === 'es' ? 'Guardando...' : 'Saving...'}
              </>
            ) : (
              <>
                <CheckCircle2 className="w-4 h-4" />
                {language === 'es' ? 'Guardar y Continuar' : 'Save & Continue'}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
});

APIKeysModal.displayName = 'APIKeysModal';

export default APIKeysModal;
