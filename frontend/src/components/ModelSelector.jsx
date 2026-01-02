import { useState, useEffect } from 'react';
import { ChevronDown, Cpu, Check, Search, DollarSign } from 'lucide-react';
import { getModels, setModel } from '../services/api';
import { useLanguage } from '../contexts/LanguageContext';

const ModelSelector = ({ onModelChange }) => {
  const [models, setModels] = useState([]);
  const [currentModel, setCurrentModel] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [search, setSearch] = useState('');
  const { language } = useLanguage();

  useEffect(() => { loadModels(); }, []);

  const loadModels = async () => {
    try {
      const data = await getModels();
      setModels(data.models || []);
      setCurrentModel(data.current || '');
    } catch (error) { console.error('Failed to load models:', error); }
  };

  const handleSelectModel = async (modelId) => {
    setIsLoading(true);
    try {
      await setModel(modelId);
      setCurrentModel(modelId);
      if (onModelChange) onModelChange(modelId);
    } catch (error) { console.error('Failed to set model:', error); }
    finally { setIsLoading(false); setIsOpen(false); }
  };

  const currentModelInfo = models.find(m => m.id === currentModel);
  const filteredModels = models.filter(m => 
    m.name.toLowerCase().includes(search.toLowerCase()) || 
    m.id.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="relative">
      <button onClick={() => setIsOpen(!isOpen)} disabled={isLoading} className="flex items-center gap-2 px-3 py-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-blue-300 dark:hover:border-blue-600 transition-colors text-sm">
        <Cpu className="w-4 h-4 text-blue-500" />
        <span className="text-gray-700 dark:text-gray-300 max-w-[180px] truncate">{currentModelInfo?.name || currentModel || 'Select model'}</span>
        <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setIsOpen(false)} />
          <div className="absolute top-full right-0 mt-1 w-96 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-20 overflow-hidden">
            <div className="p-3 border-b border-gray-100 dark:border-gray-700">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={language === 'es' ? 'Buscar modelos...' : 'Search models...'}
                  className="w-full pl-9 pr-3 py-2 bg-gray-100 dark:bg-gray-700 border-0 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500"
                  autoFocus
                />
              </div>
              <p className="text-xs text-gray-500 mt-2">{filteredModels.length} {language === 'es' ? 'modelos' : 'models'}</p>
            </div>
            <div className="max-h-80 overflow-y-auto">
              {filteredModels.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleSelectModel(model.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors border-b border-gray-50 dark:border-gray-700/50 ${
                    model.id === currentModel ? 'bg-blue-50 dark:bg-blue-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <p className={`text-sm font-medium truncate ${model.id === currentModel ? 'text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'}`}>{model.name}</p>
                    <p className="text-xs text-gray-400 truncate">{model.id}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    {model.pricing && (
                      <div className="flex items-center gap-1 text-xs text-gray-500">
                        <DollarSign className="w-3 h-3" />
                        <span>{model.pricing.prompt}</span>
                      </div>
                    )}
                    {model.context_length > 0 && (
                      <p className="text-xs text-gray-400">{Math.round(model.context_length/1000)}k ctx</p>
                    )}
                  </div>
                  {model.id === currentModel && <Check className="w-4 h-4 text-blue-500 flex-shrink-0" />}
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
