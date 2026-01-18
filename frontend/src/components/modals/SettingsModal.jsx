import { memo, useState, useEffect } from 'react';
import { X, Settings, Sparkles, ChevronDown, Check } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

const CHEAP_MODELS = [
  { id: 'google/gemini-2.0-flash-exp:free', name: 'Gemini 2.0 Flash (Free)', price: 'Free', recommended: true },
  { id: 'meta-llama/llama-3.3-70b-instruct:free', name: 'Llama 3.3 70B (Free)', price: 'Free' },
  { id: 'google/gemma-3-27b-it:free', name: 'Gemma 3 27B (Free)', price: 'Free' },
  { id: 'deepseek/deepseek-r1-0528:free', name: 'DeepSeek R1 (Free)', price: 'Free' },
  { id: 'qwen/qwen3-coder:free', name: 'Qwen3 Coder 480B (Free)', price: 'Free' },
  { id: 'openai/gpt-oss-120b:free', name: 'GPT-OSS 120B (Free)', price: 'Free' },
  { id: 'nvidia/nemotron-3-nano-30b-a3b:free', name: 'Nemotron 3 Nano 30B (Free)', price: 'Free' },
  { id: 'allenai/olmo-3.1-32b-think:free', name: 'Olmo 3.1 32B Think (Free)', price: 'Free' },
];

const DEFAULT_SETTINGS = {
  autoNamingEnabled: true,
  autoNamingModel: 'google/gemini-2.0-flash-exp:free',
};

const STORAGE_KEY = 'cv_screener_settings';

export const getSettings = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return { ...DEFAULT_SETTINGS, ...JSON.parse(saved) };
    }
  } catch (e) {
    console.error('Failed to load settings:', e);
  }
  return DEFAULT_SETTINGS;
};

export const saveSettings = (settings) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (e) {
    console.error('Failed to save settings:', e);
  }
};

const SettingsModal = memo(({ isOpen, onClose, onSave }) => {
  const { language } = useLanguage();
  const [settings, setSettings] = useState(getSettings());
  const [showModelDropdown, setShowModelDropdown] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setSettings(getSettings());
    }
  }, [isOpen]);

  const handleSave = () => {
    saveSettings(settings);
    if (onSave) onSave(settings);
    onClose();
  };

  const selectedModel = CHEAP_MODELS.find(m => m.id === settings.autoNamingModel) || CHEAP_MODELS[0];

  if (!isOpen) return null;

  return (
    <div 
      className="modal-overlay overlay-enter fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" 
      onClick={onClose}
      role="dialog" 
      aria-modal="true" 
      aria-labelledby="settings-title"
    >
      <div 
        className="modal-content modal-enter w-full max-w-lg bg-white dark:bg-slate-800 rounded-2xl shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="p-6 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-gradient-to-br from-slate-600 to-slate-800 dark:from-slate-500 dark:to-slate-700 rounded-xl">
              <Settings className="w-5 h-5 text-white" aria-hidden="true" />
            </div>
            <h2 id="settings-title" className="text-xl font-semibold text-slate-900 dark:text-white">
              {language === 'es' ? 'Configuración' : 'Settings'}
            </h2>
          </div>
          <button 
            onClick={onClose} 
            className="p-2 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
            aria-label={language === 'es' ? 'Cerrar' : 'Close'}
          >
            <X className="w-5 h-5 text-slate-500" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
          {/* Auto-Naming Section */}
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-500" />
              <h3 className="font-semibold text-slate-900 dark:text-white">
                {language === 'es' ? 'Nombre Automático de Chats' : 'Auto Chat Naming'}
              </h3>
            </div>
            
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {language === 'es' 
                ? 'Cuando subes CVs a un chat, la IA analizará su contenido y generará un nombre descriptivo automáticamente (ej: "Software Development 0102").' 
                : 'When you upload CVs to a chat, AI will analyze their content and automatically generate a descriptive name (e.g., "Software Development 0102").'}
            </p>

            {/* Enable/Disable Toggle */}
            <div className="flex items-center justify-between p-4 bg-slate-50 dark:bg-slate-900 rounded-xl">
              <div>
                <p className="font-medium text-slate-900 dark:text-white">
                  {language === 'es' ? 'Activar auto-naming' : 'Enable auto-naming'}
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  {language === 'es' ? 'Genera nombres basados en el contenido de los CVs' : 'Generate names based on CV content'}
                </p>
              </div>
              <button
                onClick={() => setSettings(s => ({ ...s, autoNamingEnabled: !s.autoNamingEnabled }))}
                className={`relative w-12 h-6 rounded-full transition-colors ${
                  settings.autoNamingEnabled 
                    ? 'bg-purple-500' 
                    : 'bg-slate-300 dark:bg-slate-600'
                }`}
              >
                <div className={`absolute top-1 w-4 h-4 bg-white rounded-full transition-transform ${
                  settings.autoNamingEnabled ? 'left-7' : 'left-1'
                }`} />
              </button>
            </div>

            {/* Model Selector */}
            {settings.autoNamingEnabled && (
              <div className="space-y-2">
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                  {language === 'es' ? 'Modelo de IA (OpenRouter)' : 'AI Model (OpenRouter)'}
                </label>
                <div className="relative">
                  <button
                    onClick={() => setShowModelDropdown(!showModelDropdown)}
                    className="w-full flex items-center justify-between p-3 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl hover:border-purple-400 dark:hover:border-purple-500 transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 bg-purple-100 dark:bg-purple-900/30 rounded-lg flex items-center justify-center">
                        <Sparkles className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                      </div>
                      <div className="text-left">
                        <p className="font-medium text-slate-900 dark:text-white text-sm">{selectedModel.name}</p>
                        <p className="text-xs text-emerald-600 dark:text-emerald-400">{selectedModel.price}</p>
                      </div>
                    </div>
                    <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${showModelDropdown ? 'rotate-180' : ''}`} />
                  </button>

                  {showModelDropdown && (
                    <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-lg z-10 max-h-64 overflow-y-auto">
                      {CHEAP_MODELS.map(model => (
                        <button
                          key={model.id}
                          onClick={() => {
                            setSettings(s => ({ ...s, autoNamingModel: model.id }));
                            setShowModelDropdown(false);
                          }}
                          className={`w-full flex items-center justify-between p-3 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors ${
                            model.id === settings.autoNamingModel ? 'bg-purple-50 dark:bg-purple-900/20' : ''
                          }`}
                        >
                          <div className="flex items-center gap-3">
                            <div className="w-8 h-8 bg-slate-100 dark:bg-slate-800 rounded-lg flex items-center justify-center">
                              <Sparkles className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                            </div>
                            <div className="text-left">
                              <p className="font-medium text-slate-900 dark:text-white text-sm">{model.name}</p>
                              <p className="text-xs text-emerald-600 dark:text-emerald-400">{model.price}</p>
                            </div>
                          </div>
                          {model.id === settings.autoNamingModel && (
                            <Check className="w-5 h-5 text-purple-500" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-xs text-slate-400">
                  {language === 'es' 
                    ? 'Modelos baratos o gratuitos recomendados para esta tarea simple.' 
                    : 'Cheap or free models recommended for this simple task.'}
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-slate-200 dark:border-slate-700 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700 rounded-xl transition-colors"
          >
            {language === 'es' ? 'Cancelar' : 'Cancel'}
          </button>
          <button
            onClick={handleSave}
            className="px-6 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-xl transition-colors font-medium"
          >
            {language === 'es' ? 'Guardar' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
});

SettingsModal.displayName = 'SettingsModal';

export default SettingsModal;
