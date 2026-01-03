import { useState, useEffect, useMemo } from 'react';
import { X, Settings, Search, Check, Brain, Sparkles, DollarSign, ArrowUpDown, Filter, Zap, MessageSquare, Save, RotateCcw, ShieldCheck, Shuffle, ToggleLeft, ToggleRight } from 'lucide-react';
import { getModels } from '../services/api';
import { useLanguage } from '../contexts/LanguageContext';

const STORAGE_KEY = 'rag_pipeline_settings';

const SORT_OPTIONS = [
  { id: 'name', label: { es: 'Nombre A-Z', en: 'Name A-Z' } },
  { id: 'price_asc', label: { es: 'Precio: menor a mayor', en: 'Price: low to high' } },
  { id: 'price_desc', label: { es: 'Precio: mayor a menor', en: 'Price: high to low' } },
  { id: 'context_desc', label: { es: 'Mayor contexto', en: 'Largest context' } },
];

const FILTER_OPTIONS = [
  { id: 'all', label: { es: 'Todos', en: 'All' } },
  { id: 'free', label: { es: 'Gratis', en: 'Free' } },
  { id: 'reasoning', label: { es: 'Razonamiento', en: 'Reasoning' } },
];

const PIPELINE_STEPS = [
  {
    id: 'understanding',
    icon: Zap,
    color: 'amber',
    title: { es: 'Paso 1: Entendimiento de Query', en: 'Step 1: Query Understanding' },
    description: { 
      es: 'Modelo rápido que analiza y reformula tu pregunta para mejor comprensión', 
      en: 'Fast model that analyzes and reformulates your question for better understanding' 
    },
    defaultModel: 'google/gemini-2.0-flash-001',
    recommended: { es: 'Recomendado: Modelo rápido y económico', en: 'Recommended: Fast and cheap model' },
    optional: false
  },
  {
    id: 'reranking',
    icon: Shuffle,
    color: 'purple',
    title: { es: 'Paso 2: Re-ranking', en: 'Step 2: Re-ranking' },
    description: { 
      es: 'Reordena resultados de búsqueda por relevancia semántica usando LLM', 
      en: 'Reorders search results by semantic relevance using LLM' 
    },
    defaultModel: 'google/gemini-2.0-flash-001',
    recommended: { es: 'Opcional: Mejora relevancia de resultados', en: 'Optional: Improves result relevance' },
    optional: true
  },
  {
    id: 'generation',
    icon: MessageSquare,
    color: 'blue',
    title: { es: 'Paso 3: Generación de Respuesta', en: 'Step 3: Response Generation' },
    description: { 
      es: 'Modelo principal que genera la respuesta final basada en los CVs', 
      en: 'Main model that generates the final response based on CVs' 
    },
    defaultModel: 'google/gemini-2.0-flash-001',
    recommended: { es: 'Recomendado: Modelo potente para análisis', en: 'Recommended: Powerful model for analysis' },
    optional: false
  },
  {
    id: 'verification',
    icon: ShieldCheck,
    color: 'green',
    title: { es: 'Paso 4: Verificación LLM', en: 'Step 4: LLM Verification' },
    description: { 
      es: 'Verifica que la respuesta esté fundamentada en el contexto de los CVs', 
      en: 'Verifies the response is grounded in the CV context' 
    },
    defaultModel: 'google/gemini-2.0-flash-001',
    recommended: { es: 'Opcional: Detecta información no verificable', en: 'Optional: Detects unverifiable information' },
    optional: true
  }
];

export const getRAGPipelineSettings = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      // Ensure all fields exist with defaults
      return {
        understanding: parsed.understanding || PIPELINE_STEPS[0].defaultModel,
        reranking: parsed.reranking || PIPELINE_STEPS[1].defaultModel,
        reranking_enabled: parsed.reranking_enabled !== undefined ? parsed.reranking_enabled : true,
        generation: parsed.generation || PIPELINE_STEPS[2].defaultModel,
        verification: parsed.verification || PIPELINE_STEPS[3].defaultModel,
        verification_enabled: parsed.verification_enabled !== undefined ? parsed.verification_enabled : true
      };
    }
  } catch (e) {
    console.error('Error loading RAG pipeline settings:', e);
  }
  return {
    understanding: PIPELINE_STEPS[0].defaultModel,
    reranking: PIPELINE_STEPS[1].defaultModel,
    reranking_enabled: true,
    generation: PIPELINE_STEPS[2].defaultModel,
    verification: PIPELINE_STEPS[3].defaultModel,
    verification_enabled: true
  };
};

export const saveRAGPipelineSettings = (settings) => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
    return true;
  } catch (e) {
    console.error('Error saving RAG pipeline settings:', e);
    return false;
  }
};

const RAGPipelineSettings = ({ isOpen, onClose, onSave }) => {
  const [models, setModels] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [settings, setSettings] = useState(getRAGPipelineSettings());
  const [activeStep, setActiveStep] = useState('understanding');
  const [search, setSearch] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [filterBy, setFilterBy] = useState('all');
  const { language } = useLanguage();

  useEffect(() => {
    if (isOpen) {
      loadModels();
      setSettings(getRAGPipelineSettings());
    }
  }, [isOpen]);

  const loadModels = async () => {
    setIsLoading(true);
    try {
      const data = await getModels();
      setModels(data.models || []);
    } catch (error) {
      console.error('Failed to load models:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const filteredAndSortedModels = useMemo(() => {
    let result = models.filter(m => 
      m.name.toLowerCase().includes(search.toLowerCase()) || 
      m.id.toLowerCase().includes(search.toLowerCase())
    );
    
    if (filterBy === 'free') {
      result = result.filter(m => m.is_free);
    } else if (filterBy === 'reasoning') {
      result = result.filter(m => m.is_reasoning);
    }
    
    result.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'price_asc':
          return (a.pricing_raw?.prompt || 0) - (b.pricing_raw?.prompt || 0);
        case 'price_desc':
          return (b.pricing_raw?.prompt || 0) - (a.pricing_raw?.prompt || 0);
        case 'context_desc':
          return (b.context_length || 0) - (a.context_length || 0);
        default:
          return 0;
      }
    });
    
    return result;
  }, [models, search, sortBy, filterBy]);

  const handleSelectModel = (modelId) => {
    setSettings(prev => ({ ...prev, [activeStep]: modelId }));
  };

  const handleSave = () => {
    saveRAGPipelineSettings(settings);
    if (onSave) onSave(settings);
    onClose();
  };

  const handleReset = () => {
    const defaults = {
      understanding: PIPELINE_STEPS[0].defaultModel,
      reranking: PIPELINE_STEPS[1].defaultModel,
      reranking_enabled: true,
      generation: PIPELINE_STEPS[2].defaultModel,
      verification: PIPELINE_STEPS[3].defaultModel,
      verification_enabled: true
    };
    setSettings(defaults);
  };

  const handleToggleStep = (stepId) => {
    const enabledKey = `${stepId}_enabled`;
    setSettings(prev => ({ ...prev, [enabledKey]: !prev[enabledKey] }));
  };

  const isStepEnabled = (stepId) => {
    const step = PIPELINE_STEPS.find(s => s.id === stepId);
    if (!step?.optional) return true;
    return settings[`${stepId}_enabled`] !== false;
  };

  const getModelInfo = (modelId) => models.find(m => m.id === modelId);

  if (!isOpen) return null;

  const activeStepInfo = PIPELINE_STEPS.find(s => s.id === activeStep);
  const colorClasses = {
    amber: {
      bg: 'bg-amber-100 dark:bg-amber-900/30',
      border: 'border-amber-300 dark:border-amber-600',
      text: 'text-amber-700 dark:text-amber-300',
      icon: 'text-amber-500'
    },
    blue: {
      bg: 'bg-blue-100 dark:bg-blue-900/30',
      border: 'border-blue-300 dark:border-blue-600',
      text: 'text-blue-700 dark:text-blue-300',
      icon: 'text-blue-500'
    },
    purple: {
      bg: 'bg-purple-100 dark:bg-purple-900/30',
      border: 'border-purple-300 dark:border-purple-600',
      text: 'text-purple-700 dark:text-purple-300',
      icon: 'text-purple-500'
    },
    green: {
      bg: 'bg-green-100 dark:bg-green-900/30',
      border: 'border-green-300 dark:border-green-600',
      text: 'text-green-700 dark:text-green-300',
      icon: 'text-green-500'
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} />
      
      {/* Modal */}
      <div className="relative w-full max-w-4xl bg-white dark:bg-gray-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-blue-500 rounded-xl flex items-center justify-center">
              <Settings className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                {language === 'es' ? 'Configuración del Pipeline RAG' : 'RAG Pipeline Settings'}
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {language === 'es' ? 'Configura los modelos para cada etapa del análisis' : 'Configure models for each analysis stage'}
              </p>
            </div>
          </div>
          <button 
            onClick={onClose}
            className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        <div className="flex h-[500px]">
          {/* Left Panel - Pipeline Steps */}
          <div className="w-80 border-r border-gray-200 dark:border-gray-700 p-4 space-y-3 overflow-y-auto">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
              {language === 'es' ? 'Etapas del Pipeline' : 'Pipeline Stages'}
            </p>
            
            {PIPELINE_STEPS.map((step) => {
              const StepIcon = step.icon;
              const colors = colorClasses[step.color];
              const selectedModel = getModelInfo(settings[step.id]);
              const isActive = activeStep === step.id;
              const stepEnabled = isStepEnabled(step.id);
              
              return (
                <div key={step.id} className="relative">
                  <button
                    onClick={() => setActiveStep(step.id)}
                    className={`w-full text-left p-4 rounded-xl border-2 transition-all ${
                      !stepEnabled ? 'opacity-50' : ''
                    } ${
                      isActive 
                        ? `${colors.bg} ${colors.border}` 
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                  >
                    <div className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-lg ${colors.bg} flex items-center justify-center flex-shrink-0`}>
                        <StepIcon className={`w-4 h-4 ${colors.icon}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className={`text-sm font-medium ${isActive ? colors.text : 'text-gray-700 dark:text-gray-300'}`}>
                            {step.title[language] || step.title.en}
                          </p>
                          {step.optional && (
                            <span
                              role="switch"
                              aria-checked={stepEnabled}
                              onClick={(e) => { e.stopPropagation(); handleToggleStep(step.id); }}
                              className="p-1 hover:bg-gray-200 dark:hover:bg-gray-600 rounded transition-colors cursor-pointer"
                              title={stepEnabled ? 'Disable' : 'Enable'}
                            >
                              {stepEnabled ? (
                                <ToggleRight className="w-5 h-5 text-green-500" />
                              ) : (
                                <ToggleLeft className="w-5 h-5 text-gray-400" />
                              )}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 line-clamp-2">
                          {step.description[language] || step.description.en}
                        </p>
                        {selectedModel && stepEnabled && (
                          <div className="mt-2 flex items-center gap-1.5">
                            <Check className="w-3 h-3 text-green-500" />
                            <span className="text-xs font-medium text-gray-600 dark:text-gray-300 truncate">
                              {selectedModel.name}
                            </span>
                          </div>
                        )}
                        {!stepEnabled && (
                          <div className="mt-2 flex items-center gap-1.5">
                            <span className="text-xs text-gray-400">
                              {language === 'es' ? 'Desactivado' : 'Disabled'}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                </div>
              );
            })}

            {/* Info box */}
            <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-900/50 rounded-lg border border-gray-200 dark:border-gray-700">
              <p className="text-xs text-gray-600 dark:text-gray-400">
                💡 {language === 'es' 
                  ? 'Estos modelos se usarán por defecto en todos tus chats.' 
                  : 'These models will be used by default in all your chats.'}
              </p>
            </div>
          </div>

          {/* Right Panel - Model Selection */}
          <div className="flex-1 flex flex-col">
            {/* Active step header */}
            <div className={`p-4 ${colorClasses[activeStepInfo.color].bg} border-b border-gray-200 dark:border-gray-700`}>
              <div className="flex items-center gap-2">
                <activeStepInfo.icon className={`w-5 h-5 ${colorClasses[activeStepInfo.color].icon}`} />
                <span className={`font-medium ${colorClasses[activeStepInfo.color].text}`}>
                  {activeStepInfo.title[language] || activeStepInfo.title.en}
                </span>
              </div>
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {activeStepInfo.recommended[language] || activeStepInfo.recommended.en}
              </p>
            </div>

            {/* Search and filters */}
            <div className="p-3 border-b border-gray-100 dark:border-gray-700 space-y-2">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder={language === 'es' ? 'Buscar modelos...' : 'Search models...'}
                  className="w-full pl-9 pr-3 py-2 bg-gray-100 dark:bg-gray-700 border-0 rounded-lg text-sm text-gray-900 dark:text-white placeholder-gray-400 focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <div className="flex gap-2 flex-wrap">
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
            </div>

            {/* Results count */}
            <div className="px-3 py-2 bg-gray-50 dark:bg-gray-900/50 border-b border-gray-100 dark:border-gray-700">
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {filteredAndSortedModels.length} {language === 'es' ? 'modelos' : 'models'}
              </p>
            </div>

            {/* Model list */}
            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center h-32">
                  <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                </div>
              ) : (
                filteredAndSortedModels.map((model) => {
                  const isSelected = settings[activeStep] === model.id;
                  return (
                    <button
                      key={model.id}
                      onClick={() => handleSelectModel(model.id)}
                      className={`w-full flex items-center gap-3 px-4 py-3 text-left transition-colors border-b border-gray-50 dark:border-gray-700/50 ${
                        isSelected ? 'bg-blue-50 dark:bg-blue-900/30' : 'hover:bg-gray-50 dark:hover:bg-gray-700/50'
                      }`}
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className={`text-sm font-medium truncate ${isSelected ? 'text-blue-600 dark:text-blue-400' : 'text-gray-700 dark:text-gray-300'}`}>
                            {model.name}
                          </p>
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
                      {isSelected && <Check className="w-4 h-4 text-blue-500 flex-shrink-0" />}
                    </button>
                  );
                })
              )}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/50">
          <button
            onClick={handleReset}
            className="flex items-center gap-2 px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
          >
            <RotateCcw className="w-4 h-4" />
            {language === 'es' ? 'Restablecer' : 'Reset'}
          </button>
          
          <div className="flex items-center gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200 transition-colors"
            >
              {language === 'es' ? 'Cancelar' : 'Cancel'}
            </button>
            <button
              onClick={handleSave}
              className="flex items-center gap-2 px-5 py-2 bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white rounded-lg font-medium text-sm transition-colors"
            >
              <Save className="w-4 h-4" />
              {language === 'es' ? 'Guardar configuración' : 'Save settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RAGPipelineSettings;
