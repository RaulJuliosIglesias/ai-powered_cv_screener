import { useState, useRef, memo, useCallback } from 'react';
import { Copy, Check } from 'lucide-react';
import { useLanguage } from '../contexts/LanguageContext';

export const MemoizedTable = memo(({ children, ...props }) => {
  const tableRef = useRef(null);
  const [copied, setCopied] = useState(false);
  const { language } = useLanguage();

  const copyTable = useCallback(() => {
    if (tableRef.current) {
      const rows = tableRef.current.querySelectorAll('tr');
      let text = '';
      rows.forEach(row => {
        const cells = row.querySelectorAll('th, td');
        text += Array.from(cells).map(c => c.textContent).join('\t') + '\n';
      });
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, []);

  return (
    <div className="my-4 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-100 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-600">
        <span className="text-xs font-medium text-muted">
          {language === 'es' ? 'Tabla' : 'Table'}
        </span>
        <button 
          onClick={copyTable} 
          className="flex items-center gap-1.5 text-xs text-muted hover:text-primary transition-colors focus-ring rounded px-2 py-1"
          aria-label={copied ? (language === 'es' ? 'Copiado' : 'Copied') : (language === 'es' ? 'Copiar tabla' : 'Copy table')}
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" aria-hidden="true" /> 
              {language === 'es' ? '¡Copiado!' : 'Copied!'}
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" aria-hidden="true" /> 
              {language === 'es' ? 'Copiar tabla' : 'Copy table'}
            </>
          )}
        </button>
      </div>
      <div className="overflow-x-auto">
        <table ref={tableRef} className="w-full text-sm" {...props}>
          {children}
        </table>
      </div>
    </div>
  );
});

MemoizedTable.displayName = 'MemoizedTable';

export const MemoizedCodeBlock = memo(({ inline, className, children, ...props }) => {
  const [copied, setCopied] = useState(false);
  const { language } = useLanguage();
  const codeText = String(children).replace(/\n$/, '');

  const copyCode = useCallback(() => {
    navigator.clipboard.writeText(codeText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [codeText]);

  if (inline) {
    return (
      <code 
        className="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-700 rounded text-pink-600 dark:text-pink-400 text-sm" 
        {...props}
      >
        {children}
      </code>
    );
  }

  return (
    <div className="my-3 rounded-lg overflow-hidden border border-slate-200 dark:border-slate-600 bg-slate-900">
      <div className="flex items-center justify-between px-3 py-2 bg-slate-800 border-b border-slate-700">
        <span className="text-xs text-slate-400">
          {className?.replace('language-', '') || 'code'}
        </span>
        <button 
          onClick={copyCode} 
          className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-white transition-colors focus-ring rounded px-2 py-1"
          aria-label={copied ? (language === 'es' ? 'Copiado' : 'Copied') : (language === 'es' ? 'Copiar código' : 'Copy code')}
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" aria-hidden="true" /> 
              {language === 'es' ? '¡Copiado!' : 'Copied!'}
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" aria-hidden="true" /> 
              {language === 'es' ? 'Copiar código' : 'Copy code'}
            </>
          )}
        </button>
      </div>
      <pre className="p-4 overflow-x-auto text-sm text-slate-100">
        <code {...props}>{children}</code>
      </pre>
    </div>
  );
});

MemoizedCodeBlock.displayName = 'MemoizedCodeBlock';

export default MemoizedTable;
