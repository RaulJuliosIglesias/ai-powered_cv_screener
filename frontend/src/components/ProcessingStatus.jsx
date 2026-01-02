import { CheckCircle, Loader2, Circle, AlertCircle } from 'lucide-react';

const ProcessingStatus = ({ status, onCancel }) => {
  if (!status) return null;

  const { total_files, processed_files, progress_percent, files, status: jobStatus } = status;

  const getStatusIcon = (fileStatus) => {
    switch (fileStatus) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'processing':
        return <Loader2 className="w-4 h-4 text-primary-500 animate-spin" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      default:
        return <Circle className="w-4 h-4 text-gray-300" />;
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">
          {jobStatus === 'completed' ? 'Processing Complete' : 'Processing CVs...'}
        </h2>

        <div className="mb-6">
          <div className="flex items-center justify-between text-sm text-gray-600 mb-2">
            <span>{processed_files}/{total_files} CVs indexed</span>
            <span>{Math.round(progress_percent)}%</span>
          </div>
          <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
            <div
              className={`h-full transition-all duration-300 ${
                jobStatus === 'failed' ? 'bg-red-500' : 'bg-primary-600'
              }`}
              style={{ width: `${progress_percent}%` }}
            />
          </div>
        </div>

        <div className="space-y-2 max-h-64 overflow-y-auto">
          {files?.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-3 p-2 rounded-lg hover:bg-gray-50"
            >
              {getStatusIcon(file.status)}
              <span className="text-sm text-gray-700 truncate flex-1">{file.filename}</span>
              {file.error && (
                <span className="text-xs text-red-500 truncate max-w-xs">{file.error}</span>
              )}
            </div>
          ))}
        </div>

        {jobStatus === 'processing' && (
          <p className="mt-4 text-sm text-gray-500 text-center">
            Extracting text and creating embeddings...
          </p>
        )}

        {jobStatus === 'completed' && (
          <p className="mt-4 text-sm text-green-600 text-center font-medium">
            All CVs have been processed successfully!
          </p>
        )}
      </div>
    </div>
  );
};

export default ProcessingStatus;
