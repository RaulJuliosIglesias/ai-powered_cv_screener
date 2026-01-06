import React, { memo } from 'react';
import { Sparkles, ArrowRight, MessageSquare, BarChart3, Search, Users } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * Animated suggestions panel that appears after assistant response
 */
const SuggestionsPanel = memo(({ 
  suggestions = [], 
  onSelectSuggestion,
  hasResponse = false,
  cvCount = 0
}) => {
  const { language } = useLanguage();
  
  // Default smart suggestions based on context
  const defaultSuggestions = cvCount > 0 ? [
    {
      id: 'compare',
      icon: BarChart3,
      labelEs: 'Comparar candidatos',
      labelEn: 'Compare candidates',
      query: language === 'es' ? 'Compara los mejores candidatos' : 'Compare the top candidates'
    },
    {
      id: 'skills',
      icon: Search,
      labelEs: 'Buscar por habilidad',
      labelEn: 'Search by skill',
      query: language === 'es' ? '¿Quién tiene experiencia en ' : 'Who has experience in '
    },
    {
      id: 'top',
      icon: Users,
      labelEs: 'Top 3 candidatos',
      labelEn: 'Top 3 candidates',
      query: language === 'es' ? 'Dame los 3 mejores candidatos para el puesto' : 'Give me the top 3 candidates for the position'
    }
  ] : [
    {
      id: 'upload',
      icon: Sparkles,
      labelEs: 'Sube CVs para empezar',
      labelEn: 'Upload CVs to start',
      query: null
    }
  ];
  
  const displaySuggestions = suggestions.length > 0 
    ? suggestions.map((s, i) => ({
        id: `custom-${i}`,
        icon: MessageSquare,
        labelEs: s,
        labelEn: s,
        query: s
      }))
    : defaultSuggestions;
  
  // Debug logging
  console.log('[SuggestionsPanel] Debug:', {
    suggestionsCount: suggestions.length,
    cvCount,
    hasResponse,
    displaySuggestionsCount: displaySuggestions.length,
    suggestions: suggestions,
    displaySuggestions: displaySuggestions.map(d => ({ id: d.id, labelEs: d.labelEs }))
  });
  
  return (
    <div className="mt-4 slide-up-fade">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="w-4 h-4 text-purple-500" />
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
          {language === 'es' ? 'Sugerencias' : 'Suggestions'}
        </span>
      </div>
      
      <div className="flex flex-wrap gap-2">
        {displaySuggestions.map((suggestion, idx) => {
          const Icon = suggestion.icon;
          const label = language === 'es' ? suggestion.labelEs : suggestion.labelEn;
          
          return (
            <button
              key={suggestion.id}
              onClick={() => suggestion.query && onSelectSuggestion?.(suggestion.query)}
              disabled={!suggestion.query}
              className={`
                group flex items-center gap-2 px-4 py-2.5 
                bg-white dark:bg-gray-800 
                border border-gray-200 dark:border-gray-700 
                rounded-xl text-sm font-medium
                transition-all duration-200
                stagger-item
                ${suggestion.query 
                  ? 'hover:bg-purple-50 dark:hover:bg-purple-900/20 hover:border-purple-300 dark:hover:border-purple-600 hover:shadow-md cursor-pointer card-lift' 
                  : 'opacity-60 cursor-not-allowed'
                }
              `}
              style={{ animationDelay: `${idx * 100}ms` }}
            >
              <Icon className={`w-4 h-4 ${suggestion.query ? 'text-purple-500' : 'text-gray-400'}`} />
              <span className="text-gray-700 dark:text-gray-200">{label}</span>
              {suggestion.query && (
                <ArrowRight className="w-3 h-3 text-gray-400 group-hover:text-purple-500 group-hover:translate-x-1 transition-all" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
});

SuggestionsPanel.displayName = 'SuggestionsPanel';

export default SuggestionsPanel;
