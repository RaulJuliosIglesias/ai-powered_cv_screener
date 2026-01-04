import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Clean and fix content from LLM artifacts
 */
const cleanContent = (text) => {
  if (!text) return text;
  
  // Remove "code Copy code" artifacts
  let cleaned = text
    .replace(/^code\s*$/gm, '')
    .replace(/code\s*Copy\s*code/gi, '')
    .replace(/Copy\s*code/gi, '')
    .trim();
  
  // Fix malformed bold markdown: "** text**" -> "**text**"
  // BUT preserve CV links format: **[Name](cv:id)**
  // Fix "** text" -> "**text" ONLY if not followed by [
  cleaned = cleaned.replace(/\*\*\s+(?!\[)/g, '**');
  // Fix "text **" -> "text**" ONLY if not preceded by )
  cleaned = cleaned.replace(/(?<!\))\s+\*\*/g, '**');
  
  return cleaned;
};

/**
 * DirectAnswerSection - Always displays, never fails
 * Renders the direct answer with CV links working
 */
const DirectAnswerSection = ({ content, cvLinkRenderer }) => {
  if (!content) {
    return (
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
        <p className="text-sm text-gray-600 dark:text-gray-400">
          No direct answer available.
        </p>
      </div>
    );
  }

  const cleanedContent = cleanContent(content);

  return (
    <div className="mb-4">
      <div className="prose prose-sm max-w-none dark:prose-invert">
        <ReactMarkdown
          remarkPlugins={[remarkGfm]}
          components={{
            a: cvLinkRenderer,
            p: ({ children }) => (
              <p className="mb-2 leading-relaxed text-gray-700 dark:text-gray-300">
                {children}
              </p>
            ),
            strong: ({ children }) => (
              <strong className="font-semibold text-gray-900 dark:text-white">
                {children}
              </strong>
            ),
            // Hide code blocks that are just artifacts
            code: ({ children }) => {
              const text = String(children).trim();
              if (!text || text === 'code' || text === 'Copy code') return null;
              return <code className="px-1 py-0.5 bg-gray-100 dark:bg-gray-800 rounded text-sm">{children}</code>;
            },
          }}
        >
          {cleanedContent}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default DirectAnswerSection;
