import { FileText } from 'lucide-react';

const SourceBadge = ({ filename, score, cvId, onViewCV }) => {
  const handleClick = () => {
    if (onViewCV && cvId) {
      onViewCV();
    }
  };

  return (
    <button
      onClick={handleClick}
      className={`inline-flex items-center gap-1 px-2 py-1 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 rounded-full text-xs transition-colors ${cvId ? 'hover:bg-blue-100 dark:hover:bg-blue-900/50 hover:text-blue-700 dark:hover:text-blue-300 cursor-pointer' : ''}`}
      title={cvId ? `Click to view CV • Relevance: ${(score * 100).toFixed(0)}%` : `Relevance: ${(score * 100).toFixed(0)}%`}
    >
      <FileText className="w-3 h-3" />
      {filename.replace('.pdf', '')}
    </button>
  );
};

export default SourceBadge;
