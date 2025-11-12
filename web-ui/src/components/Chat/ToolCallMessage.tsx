import { useState } from 'react';
import type { Message } from '../../types';

interface ToolCallMessageProps {
  message: Message;
}

// Terminal-style tool display utilities
function getToolDisplayParts(toolName: string): { verb: string; label: string } {
  const toolMap: Record<string, { verb: string; label: string }> = {
    'read_file': { verb: 'Read', label: 'file' },
    'write_file': { verb: 'Write', label: 'file' },
    'edit_file': { verb: 'Edit', label: 'file' },
    'delete_file': { verb: 'Delete', label: 'file' },
    'list_files': { verb: 'List', label: 'files' },
    'list_directory': { verb: 'List', label: 'directory' },
    'search_code': { verb: 'Search', label: 'code' },
    'search': { verb: 'Search', label: 'project' },
    'run_command': { verb: 'Run', label: 'command' },
    'bash_execute': { verb: 'Run', label: 'command' },
    'fetch_url': { verb: 'Fetch', label: 'url' },
    'open_browser': { verb: 'Open', label: 'browser' },
    'capture_screenshot': { verb: 'Capture', label: 'screenshot' },
    'analyze_image': { verb: 'Analyze', label: 'image' },
    'git_commit': { verb: 'Commit', label: 'changes' },
  };

  if (toolName.startsWith('mcp__')) {
    const parts = toolName.split('__', 2);
    if (parts.length === 3) {
      return { verb: 'MCP', label: `${parts[1]}/${parts[2]}` };
    }
    if (parts.length === 2) {
      return { verb: 'MCP', label: parts[1] };
    }
    return { verb: 'MCP', label: 'tool' };
  }

  return toolMap[toolName] || { verb: 'Call', label: 'tool' };
}

function summarizeToolArgs(toolName: string, toolArgs: any): string {
  if (!toolArgs || typeof toolArgs !== 'object') return '';

  const primaryKeys: Record<string, string[]> = {
    'read_file': ['file_path', 'path'],
    'write_file': ['file_path', 'path'],
    'edit_file': ['file_path', 'path'],
    'delete_file': ['file_path', 'path'],
    'list_files': ['path', 'directory'],
    'list_directory': ['path', 'directory'],
    'search_code': ['pattern', 'query'],
    'search': ['query'],
    'run_command': ['command'],
    'bash_execute': ['command'],
    'fetch_url': ['url'],
    'open_browser': ['url'],
    'capture_screenshot': ['target', 'path'],
    'capture_web_screenshot': ['url'],
    'analyze_image': ['image_path', 'file_path'],
    'git_commit': ['message'],
  };

  const keys = primaryKeys[toolName] || Object.keys(toolArgs);
  for (const key of keys) {
    if (toolArgs[key] && typeof toolArgs[key] === 'string') {
      return toolArgs[key];
    }
  }
  return '';
}

export function ToolCallMessage({ message }: ToolCallMessageProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (message.role === 'tool_call') {
    const toolName = message.tool_name ||
                     (message.tool_calls && message.tool_calls[0]?.name) ||
                     (message as any)?.name || '';

    const { verb, label } = getToolDisplayParts(toolName);
    const summary = summarizeToolArgs(toolName, message.tool_args ||
                                             (message.tool_calls && message.tool_calls[0]?.parameters));

    return (
      <div className="animate-slide-up my-1 px-6">
        <div className="font-mono text-sm text-gray-300">
          <span className="text-gray-400">⏺ </span>
          <span className="text-white">{verb}</span>
          <span className="text-gray-500">
            {summary ? `(${summary})` : label ? `(${label})` : ''}
          </span>
          {(message.tool_args && Object.keys(message.tool_args).length > 0) ||
            (message.tool_calls && message.tool_calls.length > 0) ? (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="ml-2 text-gray-500 hover:text-gray-300 text-xs"
              title="View details"
            >
              {isExpanded ? '▼' : '▶'}
            </button>
          ) : null}
        </div>

        {isExpanded && message.tool_args && (
          <div className="ml-6 mt-1 text-xs">
            <div className="text-gray-500 mb-1">Parameters:</div>
            <pre className="text-gray-400 font-mono bg-gray-900 rounded p-2 border border-gray-700 overflow-x-auto">
              {JSON.stringify(message.tool_args, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (message.role === 'tool_result') {
    const resultContent = message.tool_result || message.content || '';

    // Check for error sentinel
    const isError = resultContent.includes('::tool_error::');
    const isInterrupted = resultContent.includes('::interrupted::');

    // Clean up special markers
    let cleanContent = resultContent;
    if (isError) {
      cleanContent = resultContent.replace('::tool_error::', '').trim();
    } else if (isInterrupted) {
      cleanContent = resultContent.replace('::interrupted::', '').trim();
    }

    // Parse the content into lines
    const lines = cleanContent.split('\n').filter((line: string) => line.trim());

    return (
      <div className="animate-slide-up my-1 px-6">
        {lines.map((line: string, index: number) => (
          <div key={index} className="font-mono text-sm">
            <span className="text-gray-400">⎿ </span>
            <span className={
              isInterrupted ? 'text-red-500 font-bold' :
              isError ? 'text-red-400' :
              'text-gray-400'
            }>
              {line}
            </span>
          </div>
        ))}

        {/* Expand button for long results */}
        {!isExpanded && resultContent.length > 500 && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-6 text-xs text-gray-500 hover:text-gray-300"
          >
            Show full output
          </button>
        )}

        {isExpanded && (
          <button
            onClick={() => setIsExpanded(false)}
            className="ml-6 text-xs text-gray-500 hover:text-gray-300"
          >
            Show less
          </button>
        )}

        {/* Full content when expanded */}
        {isExpanded && (
          <div className="ml-6 mt-1">
            <pre className="text-xs text-gray-400 font-mono bg-gray-900 rounded p-2 border border-gray-700 overflow-x-auto max-h-96">
              {cleanContent}
            </pre>
          </div>
        )}
      </div>
    );
  }

  return null;
}
