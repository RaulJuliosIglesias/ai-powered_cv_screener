import React, { useState } from 'react';
import { Download, FileText, Table, ChevronDown, Loader } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

/**
 * ExportButton - V8 Feature
 * Dropdown button for exporting session analysis as PDF or CSV
 */
const ExportButton = ({ sessionId, mode, disabled = false, className = '' }) => {
  const { language } = useLanguage();
  const [isOpen, setIsOpen] = useState(false);
  const [isExporting, setIsExporting] = useState(null); // 'pdf' | 'csv' | null

  const handleExport = async (format) => {
    if (!sessionId || isExporting) return;
    
    setIsExporting(format);
    setIsOpen(false);
    
    try {
      const url = `/api/export/${sessionId}/${format}?mode=${mode}`;
      
      // Create a temporary link to trigger download
      const response = await fetch(url);
      
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Export failed');
      }
      
      // Get filename from Content-Disposition header
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `export.${format}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?([^"]+)"?/);
        if (match) filename = match[1];
      }
      
      // Create blob and download
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(downloadUrl);
      
    } catch (error) {
      console.error('Export error:', error);
      alert(language === 'es' 
        ? `Error al exportar: ${error.message}` 
        : `Export error: ${error.message}`
      );
    } finally {
      setIsExporting(null);
    }
  };

  const formats = [
    {
      id: 'csv',
      icon: Table,
      label: language === 'es' ? 'Exportar CSV' : 'Export CSV',
      description: language === 'es' ? 'Para Excel/Sheets' : 'For Excel/Sheets'
    },
    {
      id: 'pdf',
      icon: FileText,
      label: language === 'es' ? 'Exportar PDF' : 'Export PDF',
      description: language === 'es' ? 'Informe profesional' : 'Professional report'
    }
  ];

  return (
    <div className={`relative inline-block ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        disabled={disabled || isExporting}
        className={`
          flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium
          transition-all duration-200
          ${disabled || isExporting
            ? 'bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed'
            : 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 hover:bg-blue-100 dark:hover:bg-blue-900/50'
          }
        `}
      >
        {isExporting ? (
          <Loader className="w-4 h-4 animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )}
        <span>{language === 'es' ? 'Exportar' : 'Export'}</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {/* Dropdown */}
      {isOpen && !disabled && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 z-10" 
            onClick={() => setIsOpen(false)}
          />
          
          {/* Menu */}
          <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 z-20 overflow-hidden">
            {formats.map((format) => {
              const Icon = format.icon;
              const isCurrentExporting = isExporting === format.id;
              
              return (
                <button
                  key={format.id}
                  onClick={() => handleExport(format.id)}
                  disabled={isCurrentExporting}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors text-left"
                >
                  <div className={`p-2 rounded-lg ${
                    format.id === 'pdf' 
                      ? 'bg-red-100 dark:bg-red-900/30' 
                      : 'bg-green-100 dark:bg-green-900/30'
                  }`}>
                    {isCurrentExporting ? (
                      <Loader className="w-4 h-4 animate-spin text-gray-500" />
                    ) : (
                      <Icon className={`w-4 h-4 ${
                        format.id === 'pdf' 
                          ? 'text-red-600 dark:text-red-400' 
                          : 'text-green-600 dark:text-green-400'
                      }`} />
                    )}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-gray-800 dark:text-white">
                      {format.label}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {format.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
};

export default ExportButton;
