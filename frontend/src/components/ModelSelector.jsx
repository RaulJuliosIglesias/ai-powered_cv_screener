import { useState, useEffect, useMemo } from 'react';
import { ChevronDown, Cpu, Check, Search, DollarSign, ArrowUpDown, Brain, Sparkles, Filter } from 'lucide-react';
import { getModels, setModel } from '../services/api';
import { useLanguage } from '../contexts/LanguageContext';

const SORT_OPTIONS = [
  { id: 'name', label: { es: 'Nombre A-Z', en: 'Name A-Z' } },
  { id: 'name_desc', label: { es: 'Nombre Z-A', en: 'Name Z-A' } },
  { id: 'price_asc', label: { es: 'Precio: menor a mayor', en: 'Price: low to high' } },
  { id: 'price_desc', label: { es: 'Precio: mayor a menor', en: 'Price: high to low' } },
  { id: 'context_desc', label: { es: 'Mayor contexto', en: 'Largest context' } },
  { id: 'context_asc', label: { es: 'Menor contexto', en: 'Smallest context' } },
  { id: 'newest', label: { es: 'Más recientes', en: 'Newest first' } },
  { id: 'oldest', label: { es: 'Más antiguos', en: 'Oldest first' } },
];

const FILTER_OPTIONS = [
  { id: 'all', label: { es: 'Todos', en: 'All' } },
  { id: 'free', label: { es: 'Gratis', en: 'Free' } },
  { id: 'reasoning', label: { es: 'Razonamiento', en: 'Reasoning' } },
];

const ModelSelector = ({ onModelChange }) => {
  const [models, setModels] = useState([]);
  const [currentModel, setCurrentModel] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [filterBy, setFilterBy] = useState('all');
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
  
  const filteredAndSortedModels = useMemo(() => {
    let result = models.filter(m => 
      m.name.toLowerCase().includes(search.toLowerCase()) || 
      m.id.toLowerCase().includes(search.toLowerCase())
    );
    
    // Apply filter
    if (filterBy === 'free') {
      result = result.filter(m => m.is_free);
    } else if (filterBy === 'reasoning') {
      result = result.filter(m => m.is_reasoning);
    }
    
    // Apply sort
    result.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'name_desc':
          return b.name.localeCompare(a.name);
        case 'price_asc':
          return (a.pricing_raw?.prompt || 0) - (b.pricing_raw?.prompt || 0);
        case 'price_desc':
          return (b.pricing_raw?.prompt || 0) - (a.pricing_raw?.prompt || 0);
        case 'context_desc':
          return (b.context_length || 0) - (a.context_length || 0);
        case 'context_asc':
          return (a.context_length || 0) - (b.context_length || 0);
        case 'newest':
          return (b.created || 0) - (a.created || 0);
        case 'oldest':
          return (a.created || 0) - (b.created || 0);
        default:
          return 0;
      }
    });
    
    return result;
  }, [models, search, sortBy, filterBy]);

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
          <div className="absolute top-full right-0 mt-1 w-[480px] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-xl z-20 overflow-hidden">
            {/* Search */}
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
            </div>
            
            {/* Filters and Sort */}
            <div className="p-3 border-b border-gray-100 dark:border-gray-700 flex gap-2 flex-wrap">
              {/* Filter buttons */}
              <div className="flex items-center gap-1">
                <Filter className="w-3.5 h-3.5 text-gray-400 mr-1" />
                {FILTER_OPTIONS.map(opt => (
                  <button
                    key={opt.id}
                    onClick={() => setFilterBy(opt.id)}
                    className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                      filterBy === opt.id 
                        ? 'bg-blue-500 text-white' 
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {opt.id === 'reasoning' && <Brain className="w-3 h-3 inline mr-1" />}
                    {opt.id === 'free' && <Sparkles className="w-3 h-3 inline mr-1" />}
                    {opt.label[language] || opt.label.en}
                  </button>
                ))}
              </div>
              
              {/* Sort dropdown */}
              <div className="flex items-center gap-1 ml-auto">
                <ArrowUpDown className="w-3.5 h-3.5 text-gray-400" />
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="text-xs bg-gray-100 dark:bg-gray-700 border-0 rounded-lg px-2 py-1 text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-blue-500"
                >
                  {SORT_OPTIONS.map(opt => (
                    <option key={opt.id} value={opt.id}>{opt.label[language] || opt.label.en}</option>
                  ))}
                </select>
              </div>
            </div>
            
            {/* Results count */}
            <div className="px-3 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {filteredAndSortedModels.length} {language === 'es' ? 'modelos' : 'models'}
                {filterBy !== 'all' && ` (${FILTER_OPTIONS.find(f => f.id === filterBy)?.label[language] || filterBy})`}
              </p>
            </div>
            
            {/* Model list */}
            <div className="max-h-72 overflow-y-auto">
              {filteredAndSortedModels.map((model) => (
                <button
                  key={model.id}
                  onClick={() => handleSelectModel(model.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors border-b border-gray-50 dark:border-gray-700/50 ${
                    model.id === currentModel ? 'bg-blue-50 dark:bg-blue-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                  }`}
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className={`text-sm font-medium truncate ${model.id === currentModel ? 'text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'}`}>{model.name}</p>
                      {model.is_reasoning && <Brain className="w-3.5 h-3.5 text-purple-500 flex-shrink-0" title="Reasoning model" />}
                      {model.is_free && <Sparkles className="w-3.5 h-3.5 text-green-500 flex-shrink-0" title="Free" />}
                    </div>
                    <p className="text-xs text-gray-400 truncate">{model.id}</p>
                  </div>
                  <div className="text-right flex-shrink-0 space-y-0.5">
                    {model.pricing && (
                      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 justify-end">
                        <DollarSign className="w-3 h-3" />
                        <span>{model.is_free ? 'Free' : model.pricing.prompt}</span>
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
