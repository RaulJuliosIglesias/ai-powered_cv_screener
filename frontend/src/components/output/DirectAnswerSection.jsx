import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default DirectAnswerSection;
