import { useState, useEffect } from 'react';
import { ChevronDown, Cpu, Check } from 'lucide-react';
import { getModels, setModel } from '../services/api';
import { useLanguage } from '../contexts/LanguageContext';

const ModelSelector = ({ onModelChange }) => {
  const [models, setModels] = useState([]);
  const [currentModel, setCurrentModel] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const { language } = useLanguage();

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const data = await getModels();
      setModels(data.models || []);
      setCurrentModel(data.current || '');
    } catch (error) {
      console.error('Failed to load models:', error);
    }
  };

  const handleSelectModel = async (modelId) => {
    setIsLoading(true);
    try {
      await setModel(modelId);
      setCurrentModel(modelId);
      if (onModelChange) {
        onModelChange(modelId);
      }
    } catch (error) {
      console.error('Failed to set model:', error);
    } finally {
      setIsLoading(false);
      setIsOpen(false);
    }
  };

  const currentModelInfo = models.find(m => m.id === currentModel);

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={isLoading}
        className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-blue-300 dark:hover:border-blue-600 transition-colors text-sm"
      >
        <Cpu className="w-4 h-4 text-blue-500" />
        <span className="text-gray-700 dark:text-gray-300 max-w-[150px] truncate">
          {currentModelInfo?.name || (language === 'es' ? 'Seleccionar modelo' : 'Select model')}
        </span>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full left-0 mt-1 w-72 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-20 overflow-hidden">
            <div className="p-2 border-b border-gray-100 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400 px-2">
                {language === 'es' ? 'Modelo LLM para consultas' : 'LLM Model for queries'}
              </p>
            </div>
            <div className="max-h-64 overflow-y-auto p-1">
              {models.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleSelectModel(model.id)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                    model.id === currentModel
                      ? 'bg-blue-50 dark:bg-blue-900/30'
                      : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium truncate ${
                      model.id === currentModel
                        ? 'text-blue-600 dark:text-blue-400'
                        : 'text-gray-700 dark:text-gray-300'
                    }`}>
                      {model.name}
                    </p>
                    <p className="text-xs text-gray-400 dark:text-gray-500">
                      {model.provider}
                    </p>
                  </div>
                  {model.id === currentModel && (
                    <Check className="w-4 h-4 text-blue-500 flex-shrink-0" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ModelSelector;
