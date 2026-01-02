import { FileText, ChevronDown, ChevronUp } from 'lucide-react';
import { useState } from 'react';

const CVList = ({ cvs = [], isLoading = false }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const displayLimit = 8;
  const displayedCVs = isExpanded ? cvs : cvs.slice(0, displayLimit);

  if (isLoading) {
    return (
      <div className="bg-white border-r border-gray-200 w-64 flex-shrink-0 p-4">
        <div className="animate-pulse">
          <div className="h-6 bg-gray-200 rounded w-32 mb-4"></div>
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-8 bg-gray-100 rounded mb-2"></div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border-r border-gray-200 w-64 flex-shrink-0 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h2 className="font-semibold text-gray-900">
          INDEXED CVs ({cvs.length})
        </h2>
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {cvs.length === 0 ? (
          <p className="text-sm text-gray-500 p-2">No CVs indexed yet</p>
        ) : (
          <>
            {displayedCVs.map((cv) => (
              <div
                key={cv.id}
                className="flex items-center gap-2 p-2 rounded-lg hover:bg-gray-50 cursor-default"
                title={cv.filename}
              >
                <FileText className="w-4 h-4 text-red-500 flex-shrink-0" />
                <span className="text-sm text-gray-700 truncate">
                  {cv.filename.replace('.pdf', '')}
                </span>
              </div>
            ))}

            {cvs.length > displayLimit && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="w-full mt-2 p-2 text-sm text-primary-600 hover:bg-primary-50 rounded-lg flex items-center justify-center gap-1"
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="w-4 h-4" />
                    Show less
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    Show all ({cvs.length - displayLimit} more)
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
