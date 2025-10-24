/**
 * MCP Tools Browser Modal
 *
 * Modal for browsing and searching tools provided by an MCP server.
 * Follows SRP by focusing solely on tool display and search functionality.
 */

import { useState, useMemo } from 'react';
import { XMarkIcon, MagnifyingGlassIcon, ClipboardIcon } from '@heroicons/react/24/outline';
import { CheckIcon } from '@heroicons/react/24/solid';
import type { MCPTool } from '../../types/mcp';

interface MCPToolsModalProps {
  isOpen: boolean;
  serverName: string;
  tools: MCPTool[];
  onClose: () => void;
}

export function MCPToolsModal({ isOpen, serverName, tools, onClose }: MCPToolsModalProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [expandedTool, setExpandedTool] = useState<string | null>(null);
  const [copiedTool, setCopiedTool] = useState<string | null>(null);

  // Filter tools based on search query
  const filteredTools = useMemo(() => {
    if (!searchQuery.trim()) return tools;

    const query = searchQuery.toLowerCase();
    return tools.filter(
      tool =>
        tool.name.toLowerCase().includes(query) ||
        tool.description.toLowerCase().includes(query)
    );
  }, [tools, searchQuery]);

  if (!isOpen) return null;

  const copyToolName = (toolName: string) => {
    const fullName = `mcp__${serverName}__${toolName}`;
    navigator.clipboard.writeText(fullName);
    setCopiedTool(fullName);
    setTimeout(() => setCopiedTool(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-3xl max-h-[85vh] flex flex-col overflow-hidden animate-slide-up">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-xl font-semibold text-gray-900">
              Tools from {serverName}
            </h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {filteredTools.length} {filteredTools.length === 1 ? 'tool' : 'tools'}
              {searchQuery && ` matching "${searchQuery}"`}
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <XMarkIcon className="w-5 h-5" />
          </button>
        </div>

        {/* Search Bar */}
        <div className="px-6 py-3 border-b border-gray-100">
          <div className="relative">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search tools by name or description..."
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-gray-900 focus:border-transparent"
            />
          </div>
        </div>

        {/* Tools List */}
        <div className="flex-1 overflow-y-auto p-6">
          {filteredTools.length === 0 ? (
            <EmptyState searchQuery={searchQuery} />
          ) : (
            <div className="space-y-2">
              {filteredTools.map((tool) => (
                <ToolCard
                  key={tool.name}
                  tool={tool}
                  serverName={serverName}
                  isExpanded={expandedTool === tool.name}
                  isCopied={copiedTool === `mcp__${serverName}__${tool.name}`}
                  onToggleExpand={() => setExpandedTool(expandedTool === tool.name ? null : tool.name)}
                  onCopy={copyToolName}
                />
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-gray-200 bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

interface EmptyStateProps {
  searchQuery: string;
}

function EmptyState({ searchQuery }: EmptyStateProps) {
  return (
    <div className="text-center py-12">
      <div className="text-gray-400 mb-2">
        <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.5}
            d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
          />
        </svg>
      </div>
      <p className="text-sm text-gray-600 mb-1">
        {searchQuery ? 'No tools found' : 'No tools available'}
      </p>
      {searchQuery && (
        <p className="text-xs text-gray-500">
          Try a different search term
        </p>
      )}
    </div>
  );
}

interface ToolCardProps {
  tool: MCPTool;
  serverName: string;
  isExpanded: boolean;
  isCopied: boolean;
  onToggleExpand: () => void;
  onCopy: (toolName: string) => void;
}

function ToolCard({
  tool,
  serverName,
  isExpanded,
  isCopied,
  onToggleExpand,
  onCopy,
}: ToolCardProps) {
  const fullName = `mcp__${serverName}__${tool.name}`;

  return (
    <div className="bg-white border border-gray-200 rounded-lg hover:border-gray-300 transition-colors">
      {/* Tool Header */}
      <button
        onClick={onToggleExpand}
        className="w-full px-4 py-3 flex items-center justify-between text-left"
      >
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 truncate">{tool.name}</h4>
          {!isExpanded && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">{tool.description}</p>
          )}
        </div>

        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ml-2 flex-shrink-0 ${
            isExpanded ? 'rotate-180' : ''
          }`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Tool Details (Expanded) */}
      {isExpanded && (
        <div className="px-4 pb-3 border-t border-gray-100">
          <div className="mt-3 space-y-3">
            {/* Full Tool Name */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Full Name</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 px-3 py-2 bg-gray-50 border border-gray-200 rounded text-sm font-mono text-gray-700">
                  {fullName}
                </code>
                <button
                  onClick={() => onCopy(tool.name)}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition-colors"
                  title="Copy to clipboard"
                >
                  {isCopied ? (
                    <CheckIcon className="w-4 h-4 text-green-600" />
                  ) : (
                    <ClipboardIcon className="w-4 h-4" />
                  )}
                </button>
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-xs font-medium text-gray-500 mb-1">Description</label>
              <p className="text-sm text-gray-700 leading-relaxed">{tool.description}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
