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

// Tool result summarization functions (based on StyleFormatter from terminal UI)
function formatToolResult(toolName: string, toolArgs: any, result: any): string[] {
  if (result?.success === false) {
    const errorMsg = result?.error || 'Unknown error';
    if (errorMsg.toLowerCase().includes('interrupted')) {
      return ['User interrupted'];
    }
    return [`Error: ${errorMsg}`];
  }

  if (toolName === 'read_file') {
    return formatReadFileResult(toolArgs, result);
  } else if (toolName === 'write_file') {
    return formatWriteFileResult(toolArgs, result);
  } else if (toolName === 'edit_file') {
    return formatEditFileResult(toolArgs, result);
  } else if (toolName === 'search' || toolName === 'search_code') {
    return formatSearchResult(toolArgs, result);
  } else if (toolName === 'run_command' || toolName === 'bash_execute') {
    return formatShellResult(toolArgs, result);
  } else if (toolName === 'list_files') {
    return formatListFilesResult(toolArgs, result);
  } else if (toolName === 'fetch_url') {
    return formatFetchUrlResult(toolArgs, result);
  } else {
    return formatGenericResult(toolArgs, result);
  }
}

function formatReadFileResult(_toolArgs: any, result: any): string[] {
  const output = result?.output || result?.content || '';
  const sizeBytes = output.length;
  const sizeKb = sizeBytes / 1024;
  const lines = output ? output.split('\n').length : 0;

  const sizeDisplay = sizeKb >= 1 ? `${sizeKb.toFixed(1)} KB` : `${sizeBytes} B`;
  return [`Read ${lines} lines • ${sizeDisplay}`];
}

function formatWriteFileResult(toolArgs: any, _result: any): string[] {
  const filePath = toolArgs?.file_path || toolArgs?.path || 'unknown';
  const content = toolArgs?.content || '';
  const sizeBytes = content.length;
  const sizeKb = sizeBytes / 1024;
  const lines = content ? content.split('\n').length : 0;

  const fileName = filePath.split('/').pop() || filePath;
  const sizeDisplay = sizeKb >= 1 ? `${sizeKb.toFixed(1)} KB` : `${sizeBytes} B`;
  return [`Created ${fileName} • ${sizeDisplay} • ${lines} lines`];
}

function formatEditFileResult(toolArgs: any, _result: any): string[] {
  const filePath = toolArgs?.file_path || toolArgs?.path || 'unknown';
  const fileName = filePath.split('/').pop() || filePath;
  return [`Updated ${fileName}`];
}

function formatSearchResult(_toolArgs: any, result: any): string[] {
  const matches = result?.matches || [];
  const output = result?.output || '';

  if (matches.length > 0) {
    const summary = matches.slice(0, 3).map((match: any) => {
      const line = typeof match === 'string' ? match : match.line || match.content || '';
      const preview = line.length > 50 ? line.slice(0, 47) + '...' : line;
      return preview;
    });

    if (matches.length > 3) {
      summary.push(`... and ${matches.length - 3} more`);
    }
    return summary;
  }

  if (output) {
    const lines = output.split('\n');
    return lines.slice(0, 3);
  }

  return ['No matches found'];
}

function formatShellResult(toolArgs: any, result: any): string[] {
  const command = toolArgs?.command || '';
  const stdout = result?.stdout || result?.output || '';
  const stderr = result?.stderr || '';
  const exitCode = result?.exit_code;

  if (exitCode !== undefined && exitCode !== 0 && exitCode !== null) {
    return stderr ? [stderr.split('\n')[0]] : [`Exit code ${exitCode}`];
  }

  const normalizedCmd = command.toLowerCase();
  const normalizedStdout = stdout.toLowerCase();

  // Special git command handling
  if (normalizedCmd.includes('git ')) {
    if (normalizedCmd.includes('push')) return ['Changes pushed to remote'];
    if (normalizedCmd.includes('commit')) return ['Changes committed'];
    if (normalizedCmd.includes('pull')) return ['Changes pulled from remote'];
    return ['Git command completed'];
  }

  // Special npm command handling
  if (normalizedCmd.includes('npm install')) {
    if (normalizedStdout.includes('added') && normalizedStdout.includes('package')) {
      return ['Packages installed successfully'];
    }
    return ['npm install completed'];
  }

  if (stdout) {
    const lines = stdout.split('\n').filter((line: string) => line.trim());
    if (lines.length === 1 && lines[0].length < 80) {
      return [lines[0]];
    }
    const firstLine = lines[0];
    const preview = firstLine.length > 70 ? firstLine.slice(0, 70) + '...' : firstLine;
    return [`${preview} (${lines.length} lines)`];
  }

  if (stderr) {
    return [stderr.split('\n')[0]];
  }

  return ['Command completed with no output'];
}

function formatListFilesResult(_toolArgs: any, result: any): string[] {
  const entries = result?.entries;
  if (entries && Array.isArray(entries)) {
    return [`${entries.length} entries`];
  }

  const output = result?.output || '';
  if (!output) {
    return ['No files found'];
  }

  const lines = output.split('\n').filter((line: string) => line.trim());
  return lines.length > 0 ? [`${lines.length} items`] : ['No files found'];
}

function formatFetchUrlResult(_toolArgs: any, result: any): string[] {
  const status = result?.status_code || result?.status;
  const output = result?.output || '';

  if (status) {
    return [`Status ${status} • ${output.length} bytes`];
  }

  return [`${output.length} bytes received`];
}

function formatGenericResult(_toolArgs: any, result: any): string[] {
  const output = result?.output || '';

  if (typeof output === 'string') {
    const lines = output.split('\n').filter((line: string) => line.trim());
    if (lines.length === 0) return [];
    return lines.slice(0, 3).concat(lines.length > 3 ? ['…'] : []);
  }

  if (Array.isArray(output)) {
    const summary = output.slice(0, 3).map((item: any) => String(item));
    if (output.length > 3) {
      summary.push('…');
    }
    return summary;
  }

  if (output && typeof output === 'object') {
    return ['Object received'];
  }

  return output ? [String(output)] : [];
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
        <div className="font-mono text-sm text-gray-700">
          <span className="text-gray-500">⏺ </span>
          <span className="text-gray-800">{verb}</span>
          <span className="text-gray-600">
            {summary ? `(${summary})` : label ? `(${label})` : ''}
          </span>
          {(message.tool_args && Object.keys(message.tool_args).length > 0) ||
            (message.tool_calls && message.tool_calls.length > 0) ? (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="ml-2 text-gray-500 hover:text-gray-700 text-xs"
              title="View details"
            >
              {isExpanded ? '▼' : '▶'}
            </button>
          ) : null}
        </div>

        {isExpanded && message.tool_args && (
          <div className="ml-6 mt-1 text-xs">
            <div className="text-gray-500 mb-1">Parameters:</div>
            <pre className="text-gray-700 font-mono bg-gray-100 rounded p-2 border border-gray-300 overflow-x-auto">
              {JSON.stringify(message.tool_args, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  }

  if (message.role === 'tool_result') {
    const toolName = message.tool_name || '';
    const toolArgs = message.tool_args || {};
    const toolResult = message.tool_result || {};

    // Handle legacy string-based results
    let resultData = toolResult;
    if (typeof toolResult === 'string') {
      // Try to parse JSON if it looks like JSON
      try {
        resultData = JSON.parse(toolResult);
      } catch {
        // For string results, create a simple structure
        resultData = {
          output: toolResult,
          success: !toolResult.includes('::tool_error::') && !toolResult.includes('::interrupted::')
        };
      }
    }

    // Check for error/interrupt in result data
    const isError = resultData?.success === false ||
                   (typeof toolResult === 'string' && toolResult.includes('::tool_error::'));
    const isInterrupted = typeof toolResult === 'string' && toolResult.includes('::interrupted::');

    // Get summarized result lines
    let summaryLines: string[] = [];
    try {
      summaryLines = formatToolResult(toolName, toolArgs, resultData);
    } catch {
      // Fallback to simple display
      if (typeof toolResult === 'string') {
        const cleaned = toolResult.replace(/::tool_error::|::interrupted::/g, '').trim();
        summaryLines = cleaned.split('\n').slice(0, 3).filter((line: string) => line.trim());
        if (cleaned.split('\n').length > 3) {
          summaryLines.push('…');
        }
      } else {
        summaryLines = ['Tool completed'];
      }
    }

    // Check if we have a large result that could be expanded
    const fullOutput = typeof toolResult === 'string' ? toolResult :
                      (resultData?.output || JSON.stringify(resultData, null, 2));
    const hasExpandableContent = fullOutput && fullOutput.length > 200;

    return (
      <div className="animate-slide-up my-1 px-6">
        {summaryLines.map((line: string, index: number) => (
          <div key={index} className="font-mono text-sm">
            <span className="text-gray-500">⎿ </span>
            <span className={
              isInterrupted ? 'text-red-600 font-bold' :
              isError ? 'text-red-500' :
              'text-gray-600'
            }>
              {line}
            </span>
          </div>
        ))}

        {/* Expand button for long results */}
        {hasExpandableContent && !isExpanded && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="ml-6 text-xs text-gray-500 hover:text-gray-700"
          >
            Show full output
          </button>
        )}

        {hasExpandableContent && isExpanded && (
          <button
            onClick={() => setIsExpanded(false)}
            className="ml-6 text-xs text-gray-500 hover:text-gray-700"
          >
            Show less
          </button>
        )}

        {/* Full content when expanded */}
        {hasExpandableContent && isExpanded && (
          <div className="ml-6 mt-1">
            <pre className="text-xs text-gray-700 font-mono bg-gray-100 rounded p-2 border border-gray-300 overflow-x-auto max-h-96">
              {typeof fullOutput === 'string' ? fullOutput : JSON.stringify(fullOutput, null, 2)}
            </pre>
          </div>
        )}
      </div>
    );
  }

  return null;
}
