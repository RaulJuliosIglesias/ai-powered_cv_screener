import React, { useState, memo } from 'react';
import { FileText, ChevronDown, ChevronUp, ExternalLink, Eye, Copy, Check, Search, User } from 'lucide-react';
import { useLanguage } from '../../contexts/LanguageContext';

/**
 * ChunkPreview - Shows a single chunk with expandable content
 */
const ChunkPreview = memo(({ chunk, index, onViewCV, highlightTerms = [] }) => {
  const { language } = useLanguage();
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  
  const content = chunk.content || chunk.text || '';
  const metadata = chunk.metadata || {};
  const score = chunk.score || chunk.similarity;
  
  // Highlight search terms in content
  const highlightContent = (text) => {
    if (!highlightTerms.length) return text;
    
    let result = text;
    highlightTerms.forEach(term => {
      const regex = new RegExp(`(${term})`, 'gi');
      result = result.replace(regex, '**$1**');
    });
    return result;
  };
  
  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  const previewLength = 150;
  const preview = content.length > previewLength 
    ? content.substring(0, previewLength) + '...' 
    : content;
  
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden bg-white dark:bg-gray-800">
      {/* Header */}
      <div 
        className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-700/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-2 flex-1 min-w-0">
          <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 rounded-full flex items-center justify-center text-xs font-medium text-blue-600 dark:text-blue-400">
            {index + 1}
          </span>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              {metadata.candidate_name && (
                <span className="text-sm font-medium text-gray-800 dark:text-white truncate">
                  {metadata.candidate_name}
                </span>
              )}
              {metadata.section_type && (
                <span className="px-1.5 py-0.5 text-[10px] bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded">
                  {metadata.section_type}
                </span>
              )}
            </div>
            {metadata.filename && (
              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                {metadata.filename}
              </p>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          {score !== undefined && (
            <span className={`px-2 py-0.5 text-xs rounded-full font-medium ${
              score >= 0.8 ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' :
              score >= 0.6 ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300' :
              'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
            }`}>
              {Math.round(score * 100)}%
            </span>
          )}
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </div>
      
      {/* Content Preview / Full Content */}
      <div className="px-3 py-2">
        {isExpanded ? (
          <>
            <pre className="text-xs text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono bg-gray-50 dark:bg-gray-900/50 p-3 rounded max-h-64 overflow-y-auto">
              {content}
            </pre>
            
            {/* Actions */}
            <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-100 dark:border-gray-700">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
              >
                {copied ? <Check className="w-3 h-3 text-emerald-500" /> : <Copy className="w-3 h-3" />}
                {copied ? (language === 'es' ? 'Copiado' : 'Copied') : (language === 'es' ? 'Copiar' : 'Copy')}
              </button>
              
              {metadata.cv_id && onViewCV && (
                <button
                  onClick={() => onViewCV(metadata.cv_id, metadata.filename)}
                  className="flex items-center gap-1 px-2 py-1 text-xs text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded transition-colors"
                >
                  <Eye className="w-3 h-3" />
                  {language === 'es' ? 'Ver CV' : 'View CV'}
                </button>
              )}
            </div>
          </>
        ) : (
          <p className="text-xs text-gray-600 dark:text-gray-400 line-clamp-2">
            {preview}
          </p>
        )}
      </div>
    </div>
  );
});

ChunkPreview.displayName = 'ChunkPreview';

/**
 * SourcesPanel - V8 Enhanced sources display
 * Shows all chunks used to generate a response with expandable previews
 */
const SourcesPanel = ({ 
  sources = [], 
  chunks = [],
  onViewCV,
  searchTerms = [],
  className = ''
}) => {
  const { language } = useLanguage();
  const [isExpanded, setIsExpanded] = useState(false);
  const [filter, setFilter] = useState('');
  
  // Combine sources and chunks (some responses have one or the other)
  const allSources = chunks.length > 0 ? chunks : sources;
  
  if (!allSources || allSources.length === 0) {
    return null;
  }
  
  // Group by CV/candidate
  const groupedByCV = {};
  allSources.forEach(source => {
    const cvId = source.cv_id || source.metadata?.cv_id || 'unknown';
    if (!groupedByCV[cvId]) {
      groupedByCV[cvId] = {
        cvId,
        filename: source.filename || source.metadata?.filename || 'Unknown',
        candidateName: source.candidate_name || source.metadata?.candidate_name,
        chunks: []
      };
    }
    groupedByCV[cvId].chunks.push(source);
  });
  
  const cvGroups = Object.values(groupedByCV);
  
  // Filter chunks if search is active
  const filteredChunks = filter 
    ? allSources.filter(s => {
        const content = (s.content || s.text || '').toLowerCase();
        const name = (s.metadata?.candidate_name || '').toLowerCase();
        return content.includes(filter.toLowerCase()) || name.includes(filter.toLowerCase());
      })
    : allSources;
  
  return (
    <div className={`mt-4 ${className}`}>
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
      >
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-200">
            {language === 'es' ? 'Fuentes utilizadas' : 'Sources used'}
          </span>
          <span className="px-2 py-0.5 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
            {allSources.length} {language === 'es' ? 'fragmentos' : 'chunks'}
          </span>
          <span className="px-2 py-0.5 text-xs bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 rounded-full">
            {cvGroups.length} CVs
          </span>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>
      
      {/* Expanded Content */}
      {isExpanded && (
        <div className="mt-2 space-y-3 animate-slide-in-up">
          {/* Search filter */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder={language === 'es' ? 'Filtrar fragmentos...' : 'Filter chunks...'}
              className="w-full pl-9 pr-3 py-2 text-sm bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          
          {/* CV Groups Summary */}
          <div className="flex flex-wrap gap-2">
            {cvGroups.map(group => (
              <div 
                key={group.cvId}
                className="flex items-center gap-1.5 px-2 py-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
              >
                <User className="w-3 h-3 text-gray-400" />
                <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
                  {group.candidateName || group.filename.replace('.pdf', '')}
                </span>
                <span className="text-xs text-gray-500">
                  ({group.chunks.length})
                </span>
              </div>
            ))}
          </div>
          
          {/* Chunks List */}
          <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
            {filteredChunks.map((chunk, index) => (
              <ChunkPreview
                key={chunk.id || index}
                chunk={chunk}
                index={index}
                onViewCV={onViewCV}
                highlightTerms={searchTerms}
              />
            ))}
            
            {filter && filteredChunks.length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                {language === 'es' ? 'No se encontraron fragmentos' : 'No chunks found'}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default memo(SourcesPanel);
