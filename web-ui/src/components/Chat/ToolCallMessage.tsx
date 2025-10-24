import { useState } from 'react';
import type { Message } from '../../types';

interface ToolCallMessageProps {
  message: Message;
}

export function ToolCallMessage({ message }: ToolCallMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (message.role === 'tool_call') {
    // Extract key parameters to show inline
    const keyParams: string[] = [];
    if (message.tool_args) {
      if (message.tool_args.file_path) keyParams.push(message.tool_args.file_path);
      if (message.tool_args.command) keyParams.push(message.tool_args.command);
      if (message.tool_args.url) keyParams.push(message.tool_args.url);
    }

    return (
      <div className="flex justify-start px-4 animate-slide-up my-3">
        <div className="max-w-[85%]">
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            {/* Compact Header */}
            <div className="px-4 py-2.5 bg-gray-50 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-md bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <svg className="w-3 h-3 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <code className="text-xs font-mono font-medium text-gray-700">
                  {message.tool_name}
                </code>
                {keyParams.length > 0 && (
                  <span className="text-xs text-gray-500 truncate max-w-xs">
                    • {keyParams[0]}
                  </span>
                )}
              </div>
              {message.tool_args && Object.keys(message.tool_args).length > 0 && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                >
                  {isExpanded ? '▼' : '▶'}
                </button>
              )}
            </div>

            {/* Expanded Arguments */}
            {isExpanded && message.tool_args && (
              <div className="px-4 py-3 border-t border-gray-100">
                <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap overflow-x-auto">
                  {JSON.stringify(message.tool_args, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (message.role === 'tool_result') {
    const isSuccess = message.content?.toLowerCase().includes('success');
    const resultPreview = typeof message.tool_result === 'string'
      ? message.tool_result.slice(0, 200)
      : JSON.stringify(message.tool_result).slice(0, 200);

    return (
      <div className="flex justify-start px-4 animate-slide-up my-3">
        <div className="max-w-[85%]">
          <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
            {/* Compact Header with Status */}
            <div className={`px-4 py-2.5 flex items-center justify-between ${
              isSuccess ? 'bg-green-50' : 'bg-red-50'
            }`}>
              <div className="flex items-center gap-2">
                <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${
                  isSuccess ? 'bg-green-100' : 'bg-red-100'
                }`}>
                  <svg className={`w-3 h-3 ${isSuccess ? 'text-green-600' : 'text-red-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    {isSuccess ? (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    ) : (
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    )}
                  </svg>
                </div>
                <code className="text-xs font-mono font-medium text-gray-700">
                  {message.tool_name}
                </code>
                <span className={`text-xs font-medium ${isSuccess ? 'text-green-700' : 'text-red-700'}`}>
                  {message.content}
                </span>
              </div>
              {message.tool_result && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-gray-500 hover:text-gray-700 transition-colors"
                >
                  {isExpanded ? '▼' : '▶'}
                </button>
              )}
            </div>

            {/* Preview or Expanded Output */}
            {!isExpanded && resultPreview && (
              <div className="px-4 py-2 bg-gray-50">
                <p className="text-xs text-gray-600 font-mono truncate">
                  {resultPreview}{resultPreview.length >= 200 ? '...' : ''}
                </p>
              </div>
            )}

            {isExpanded && message.tool_result && (
              <div className="px-4 py-3 bg-gray-50 border-t border-gray-100">
                <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap overflow-x-auto max-h-96">
                  {typeof message.tool_result === 'string'
                    ? message.tool_result
                    : JSON.stringify(message.tool_result, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
