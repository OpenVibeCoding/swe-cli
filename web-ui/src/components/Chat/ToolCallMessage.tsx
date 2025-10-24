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
      if (message.tool_args.pattern) keyParams.push(message.tool_args.pattern);
    }

    return (
      <div className="flex justify-start px-6 animate-slide-up my-2">
        <div className="max-w-[85%] w-full">
          <div className="rounded-xl border border-blue-100 bg-gradient-to-br from-blue-50/50 to-indigo-50/30 shadow-sm overflow-hidden backdrop-blur-sm">
            {/* Elegant thinking step header */}
            <div className="px-4 py-2.5 flex items-start gap-3">
              <div className="mt-0.5">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-semibold text-blue-700 uppercase tracking-wider">
                    Execute
                  </span>
                  <code className="text-xs font-mono font-bold text-gray-800 bg-white/60 px-2 py-0.5 rounded">
                    {message.tool_name}
                  </code>
                </div>
                {keyParams.length > 0 && (
                  <div className="text-xs text-gray-600 font-mono truncate">
                    {keyParams[0]}
                  </div>
                )}
              </div>
              {message.tool_args && Object.keys(message.tool_args).length > 0 && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-gray-400 hover:text-gray-600 transition-colors px-2 py-1"
                  title="View details"
                >
                  {isExpanded ? '▼' : '▶'}
                </button>
              )}
            </div>

            {/* Expanded Arguments */}
            {isExpanded && message.tool_args && (
              <div className="px-4 py-3 border-t border-blue-100 bg-white/40">
                <div className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                  Parameters
                </div>
                <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap overflow-x-auto bg-white/60 rounded p-2 border border-gray-200">
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
      <div className="flex justify-start px-6 animate-slide-up my-2">
        <div className="max-w-[85%] w-full">
          <div className={`rounded-xl border shadow-sm overflow-hidden backdrop-blur-sm ${
            isSuccess
              ? 'border-emerald-100 bg-gradient-to-br from-emerald-50/50 to-teal-50/30'
              : 'border-rose-100 bg-gradient-to-br from-rose-50/50 to-red-50/30'
          }`}>
            {/* Elegant result header */}
            <div className="px-4 py-2.5 flex items-start gap-3">
              <div className="mt-0.5">
                <div className={`w-1.5 h-1.5 rounded-full ${
                  isSuccess ? 'bg-emerald-500' : 'bg-rose-500'
                }`} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-xs font-semibold uppercase tracking-wider ${
                    isSuccess ? 'text-emerald-700' : 'text-rose-700'
                  }`}>
                    {isSuccess ? 'Complete' : 'Failed'}
                  </span>
                  <code className="text-xs font-mono font-bold text-gray-800 bg-white/60 px-2 py-0.5 rounded">
                    {message.tool_name}
                  </code>
                </div>
                {!isExpanded && resultPreview && (
                  <div className="text-xs text-gray-600 font-mono truncate">
                    {resultPreview.slice(0, 100)}{resultPreview.length > 100 ? '...' : ''}
                  </div>
                )}
              </div>
              {message.tool_result && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-gray-400 hover:text-gray-600 transition-colors px-2 py-1"
                  title="View output"
                >
                  {isExpanded ? '▼' : '▶'}
                </button>
              )}
            </div>

            {/* Expanded Output */}
            {isExpanded && message.tool_result && (
              <div className={`px-4 py-3 border-t bg-white/40 ${
                isSuccess ? 'border-emerald-100' : 'border-rose-100'
              }`}>
                <div className="text-xs font-semibold text-gray-600 uppercase tracking-wide mb-2">
                  Output
                </div>
                <pre className="text-xs text-gray-700 font-mono whitespace-pre-wrap overflow-x-auto max-h-96 bg-white/60 rounded p-2 border border-gray-200">
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
