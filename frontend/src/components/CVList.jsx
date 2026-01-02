import { FileText, ChevronDown, ChevronUp, Users } from 'lucide-react';
import { useState } from 'react';

const CVList = ({ cvs = [], isLoading = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const displayLimit = 8;
  const displayedCVs = isExpanded ? cvs : cvs.slice(0, displayLimit);

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 w-72 flex-shrink-0 p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 dark:bg-gray-700 rounded w-32 mb-4"></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-12 bg-gray-100 dark:bg-gray-700 rounded-xl mb-2"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 w-72 flex-shrink-0 flex flex-col">
      <div className="p-4 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-blue-500" />
          <h2 className="font-semibold text-gray-900 dark:text-white">
            CVs Indexados
          </h2>
          <span className="ml-auto px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-medium rounded-full">
            {cvs.length}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {cvs.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">No hay CVs indexados</p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">Sube CVs para comenzar</p>
          </div>
        ) : (
          <>
            {displayedCVs.map((cv) => (
              <div
                key={cv.id}
                className="flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 cursor-default mb-1 transition-colors"
                title={cv.filename}
              >
                <div className="w-10 h-10 bg-red-100 dark:bg-red-900/30 rounded-lg flex items-center justify-center flex-shrink-0">
                  <FileText className="w-5 h-5 text-red-500" />
                </div>
                <div className="min-w-0 flex-1">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate block">
                    {cv.filename.replace('.pdf', '')}
                  </span>
                  <span className="text-xs text-gray-400">{cv.chunk_count || 0} chunks</span>
                </div>
              </div>
            ))}

            {cvs.length > displayLimit && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full mt-2 p-2.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl flex items-center justify-center gap-1 font-medium transition-colors"
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    Ver menos
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Ver todos ({cvs.length - displayLimit} más)
                  </>
                )}
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default CVList;
