import { FileText } from 'lucide-react';

const SourceBadge = ({ filename, score }) => {
  return (
    <span
      className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 rounded-full text-xs hover:bg-gray-200 transition-colors"
      title={`Relevance: ${(score * 100).toFixed(0)}%`}
    >
      <FileText className="w-3 h-3" />
      {filename.replace('.pdf', '')}
    </span>
  );
};

export default SourceBadge;
