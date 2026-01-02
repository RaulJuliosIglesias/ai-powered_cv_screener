import { FileText, ChevronDown, ChevronUp, Users, Trash2, X } from 'lucide-react';
import { useState } from 'react';
import { useLanguage } from '../contexts/LanguageContext';

const CVList = ({ cvs = [], isLoading = false, onDeleteCV, onDeleteAll }) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(null);
  const [showDeleteAllConfirm, setShowDeleteAllConfirm] = useState(false);
  const { t, language } = useLanguage();
  const displayLimit = 8;
  const displayedCVs = isExpanded ? cvs : cvs.slice(0, displayLimit);

  const handleDeleteCV = async (cvId) => {
    if (onDeleteCV) {
      await onDeleteCV(cvId);
    }
    setShowDeleteConfirm(null);
  };

  const handleDeleteAll = async () => {
    if (onDeleteAll) {
      await onDeleteAll();
    }
    setShowDeleteAllConfirm(false);
  };

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
            {language === 'es' ? 'CVs Indexados' : 'Indexed CVs'}
          </h2>
          <span className="ml-auto px-2 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 text-xs font-medium rounded-full">
            {cvs.length}
          </span>
        </div>
        {cvs.length > 0 && (
          <button
            onClick={() => setShowDeleteAllConfirm(true)}
            className="mt-2 w-full flex items-center justify-center gap-1 px-3 py-1.5 text-xs text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            {language === 'es' ? 'Eliminar todos' : 'Delete all'}
          </button>
        )}
      </div>

      {/* Delete All Confirmation */}
      {showDeleteAllConfirm && (
        <div className="p-3 bg-red-50 dark:bg-red-900/20 border-b border-red-200 dark:border-red-800">
          <p className="text-xs text-red-700 dark:text-red-300 mb-2">
            {language === 'es' ? '¿Eliminar todos los CVs?' : 'Delete all CVs?'}
          </p>
          <div className="flex gap-2">
            <button
              onClick={handleDeleteAll}
              className="flex-1 px-2 py-1 text-xs bg-red-500 text-white rounded hover:bg-red-600"
            >
              {language === 'es' ? 'Sí, eliminar' : 'Yes, delete'}
            </button>
            <button
              onClick={() => setShowDeleteAllConfirm(false)}
              className="flex-1 px-2 py-1 text-xs bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              {language === 'es' ? 'Cancelar' : 'Cancel'}
            </button>
          </div>
        </div>
      )}

      <div className="flex-1 overflow-y-auto p-3">
        {cvs.length === 0 ? (
          <div className="text-center py-8">
            <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {language === 'es' ? 'No hay CVs indexados' : 'No CVs indexed'}
            </p>
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
              {language === 'es' ? 'Sube CVs para comenzar' : 'Upload CVs to start'}
            </p>
          </div>
        ) : (
          <>
            {displayedCVs.map((cv) => (
              <div
                key={cv.id}
                className="group flex items-center gap-3 p-3 rounded-xl hover:bg-gray-50 dark:hover:bg-gray-700/50 mb-1 transition-colors"
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
                {showDeleteConfirm === cv.id ? (
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleDeleteCV(cv.id)}
                      className="p-1.5 bg-red-500 text-white rounded hover:bg-red-600"
                      title={language === 'es' ? 'Confirmar' : 'Confirm'}
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                    <button
                      onClick={() => setShowDeleteConfirm(null)}
                      className="p-1.5 bg-gray-200 dark:bg-gray-600 text-gray-600 dark:text-gray-300 rounded hover:bg-gray-300 dark:hover:bg-gray-500"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setShowDeleteConfirm(cv.id)}
                    className="opacity-0 group-hover:opacity-100 p-1.5 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-all"
                    title={language === 'es' ? 'Eliminar' : 'Delete'}
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                )}
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
                    {language === 'es' ? 'Ver menos' : 'Show less'}
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-4 h-4" />
                    {language === 'es' ? `Ver todos (${cvs.length - displayLimit} más)` : `Show all (${cvs.length - displayLimit} more)`}
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
