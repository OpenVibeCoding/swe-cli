import { useState } from 'react';
import type { Message } from '../../types';

interface ToolCallMessageProps {
  message: Message;
}

export function ToolCallMessage({ message }: ToolCallMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (message.role === 'tool_call') {
    return (
      <div className="flex justify-start animate-slide-up">
        <div className="max-w-3xl mr-12">
          <div className="rounded-lg border border-blue-200 bg-blue-50 shadow-sm">
            {/* Header */}
            <div className="px-4 py-3 flex items-center justify-between border-b border-blue-200">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-blue-100 flex items-center justify-center">
                  <svg className="w-4 h-4 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs font-medium text-blue-600 uppercase tracking-wider">
                    Tool Call
                  </div>
                  <code className="text-sm font-mono text-blue-900">
                    {message.tool_name}
                  </code>
                </div>
              </div>
              {message.tool_args && Object.keys(message.tool_args).length > 0 && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-blue-600 hover:text-blue-700 font-medium"
                >
                  {isExpanded ? 'Hide details' : 'Show details'}
                </button>
              )}
            </div>

            {/* Description */}
            <div className="px-4 py-2">
              <p className="text-sm text-blue-900">{message.content}</p>
            </div>

            {/* Expanded Arguments */}
            {isExpanded && message.tool_args && (
              <div className="px-4 pb-3">
                <div className="bg-white rounded border border-blue-200 p-3 max-h-48 overflow-y-auto">
                  <pre className="text-xs text-gray-900 font-mono whitespace-pre-wrap">
                    {JSON.stringify(message.tool_args, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  if (message.role === 'tool_result') {
    return (
      <div className="flex justify-start animate-slide-up">
        <div className="max-w-3xl mr-12">
          <div className="rounded-lg border border-green-200 bg-green-50 shadow-sm">
            {/* Header */}
            <div className="px-4 py-3 flex items-center justify-between border-b border-green-200">
              <div className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center">
                  <svg className="w-4 h-4 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <div>
                  <div className="text-xs font-medium text-green-600 uppercase tracking-wider">
                    Tool Result
                  </div>
                  <code className="text-sm font-mono text-green-900">
                    {message.tool_name}
                  </code>
                </div>
              </div>
              {message.tool_result && (
                <button
                  onClick={() => setIsExpanded(!isExpanded)}
                  className="text-xs text-green-600 hover:text-green-700 font-medium"
                >
                  {isExpanded ? 'Hide output' : 'Show output'}
                </button>
              )}
            </div>

            {/* Summary */}
            <div className="px-4 py-2">
              <p className="text-sm text-green-900">{message.content}</p>
            </div>

            {/* Expanded Output */}
            {isExpanded && message.tool_result && (
              <div className="px-4 pb-3">
                <div className="bg-white rounded border border-green-200 p-3 max-h-64 overflow-y-auto">
                  <pre className="text-xs text-gray-900 font-mono whitespace-pre-wrap">
                    {typeof message.tool_result === 'string'
                      ? message.tool_result
                      : JSON.stringify(message.tool_result, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}
