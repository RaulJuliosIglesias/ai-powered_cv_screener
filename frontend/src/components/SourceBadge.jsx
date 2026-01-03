import { FileText, ExternalLink } from 'lucide-react';

const SourceBadge = ({ filename, score, cvId, onViewCV }) => {
  const handleClick = () => {
    if (cvId) {
      // Open PDF directly from API
      const baseUrl = window.location.origin.replace(':6001', ':8003');
      const pdfUrl = `${baseUrl}/api/cvs/${cvId}/pdf`;
      window.open(pdfUrl, '_blank');
    }
  };

  const scorePercent = score ? (score * 100).toFixed(0) : null;

  return (
    <button
      onClick={handleClick}
      disabled={!cvId}
      className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
        cvId 
          ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 border border-blue-200 dark:border-blue-800 hover:bg-blue-100 dark:hover:bg-blue-900/50 hover:shadow-sm cursor-pointer' 
          : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
      }`}
      title={cvId ? `Ver CV: ${filename} • Relevancia: ${scorePercent}%` : `Relevancia: ${scorePercent}%`}
    >
      <FileText className="w-3.5 h-3.5" />
      <span className="max-w-[120px] truncate">{filename.replace('.pdf', '')}</span>
      {scorePercent && (
        <span className="px-1.5 py-0.5 bg-blue-200/50 dark:bg-blue-800/50 rounded text-[10px]">
          {scorePercent}%
        </span>
      )}
      {cvId && <ExternalLink className="w-3 h-3 opacity-60" />}
    </button>
  );
};

export default SourceBadge;
