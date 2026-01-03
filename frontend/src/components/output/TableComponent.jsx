import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Copy, Check } from 'lucide-react';

/**
 * TableComponent - Robust table renderer
 * Accepts parsed table_data structure from backend
 * Never fails - shows nothing if no table
 */
const TableComponent = ({ tableData, cvLinkRenderer }) => {
  const [copied, setCopied] = useState(false);

  if (!tableData || !tableData.headers || !tableData.rows || tableData.rows.length === 0) {
    return null; // No table to show
  }

  const { headers, rows } = tableData;

  const copyTable = () => {
    // Create plain text version
    let text = headers.join('\t') + '\n';
    rows.forEach(row => {
      // Strip markdown formatting for plain text
      const cleanRow = row.map(cell => 
        cell.replace(/\*\*/g, '').replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      );
      text += cleanRow.join('\t') + '\n';
    });
    
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="my-4">
      <div className="mb-2 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          Analysis
        </h3>
        <button
          onClick={copyTable}
          className="flex items-center gap-1.5 px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 rounded transition-colors"
        >
          {copied ? (
            <>
              <Check className="w-3.5 h-3.5" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              Copy table
            </>
          )}
        </button>
      </div>

      <div className="rounded-lg overflow-hidden border border-gray-200 dark:border-gray-700 shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-100 dark:bg-gray-800">
              <tr>
                {headers.map((header, idx) => (
                  <th
                    key={idx}
                    className="px-4 py-3 text-left text-xs font-bold text-gray-700 dark:text-gray-200 uppercase tracking-wider border-b-2 border-gray-300 dark:border-gray-600"
                  >
                    {header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              {rows.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  {row.map((cell, cellIdx) => (
                    <td
                      key={cellIdx}
                      className="px-4 py-3 text-sm text-gray-700 dark:text-gray-300 whitespace-normal"
                    >
                      {/* Render markdown in cells (for CV links) */}
                      <ReactMarkdown
                        components={{
                          a: cvLinkRenderer,
                          p: ({ children }) => <span>{children}</span>,
                          strong: ({ children }) => (
                            <strong className="font-semibold text-gray-900 dark:text-white">
                              {children}
                            </strong>
                          ),
                        }}
                      >
                        {cell}
                      </ReactMarkdown>
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default TableComponent;
