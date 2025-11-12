import { useState } from 'react';
import {
  DocumentTextIcon,
  ChatBubbleLeftRightIcon,
  MagnifyingGlassIcon,
  SparklesIcon,
  CodeBracketIcon,
  FolderIcon
} from '@heroicons/react/24/outline';
import './CodeWiki.css';

interface DocumentationItem {
  id: string;
  title: string;
  type: 'readme' | 'doc' | 'code' | 'folder';
  path: string;
  content?: string;
  children?: DocumentationItem[];
  lastModified: string;
}

interface DocumentationViewerProps {
  selectedRepo: string | null;
  searchQuery: string;
  onIndexingChange: (isIndexing: boolean) => void;
}

// Mock data for development
const mockDocumentation: DocumentationItem[] = [
  {
    id: '1',
    title: 'README.md',
    type: 'readme',
    path: '/README.md',
    lastModified: '2 hours ago',
    content: `# SWE-CLI

Software Engineering CLI with AI-powered coding assistance.

## Features

- **AI-Powered Development**: Get intelligent coding assistance
- **Multi-language Support**: Works with Python, JavaScript, TypeScript, and more
- **Git Integration**: Seamless version control integration
- **Interactive Debugging**: Advanced debugging capabilities

## Quick Start

\`\`\`bash
npm install -g swe-cli
swe-cli init
swe-cli chat
\`\`\`

## Documentation

- [Getting Started](./docs/getting-started.md)
- [API Reference](./docs/api.md)
- [Examples](./examples/)`
  },
  {
    id: '2',
    title: 'docs',
    type: 'folder',
    path: '/docs',
    lastModified: '1 day ago',
    children: [
      {
        id: '2-1',
        title: 'getting-started.md',
        type: 'doc',
        path: '/docs/getting-started.md',
        lastModified: '1 day ago'
      },
      {
        id: '2-2',
        title: 'api.md',
        type: 'doc',
        path: '/docs/api.md',
        lastModified: '3 days ago'
      },
      {
        id: '2-3',
        title: 'configuration.md',
        type: 'doc',
        path: '/docs/configuration.md',
        lastModified: '1 week ago'
      }
    ]
  },
  {
    id: '3',
    title: 'examples',
    type: 'folder',
    path: '/examples',
    lastModified: '2 days ago',
    children: [
      {
        id: '3-1',
        title: 'basic-chat.py',
        type: 'code',
        path: '/examples/basic-chat.py',
        lastModified: '2 days ago'
      },
      {
        id: '3-2',
        title: 'code-review.js',
        type: 'code',
        path: '/examples/code-review.js',
        lastModified: '5 days ago'
      }
    ]
  }
];

export function DocumentationViewer({ selectedRepo, searchQuery, onIndexingChange }: DocumentationViewerProps) {
  const [selectedDoc, setSelectedDoc] = useState<DocumentationItem | null>(null);
  const [chatMode, setChatMode] = useState<'browse' | 'chat'>('browse');
  const [chatMessage, setChatMessage] = useState('');
  const [isSearching, setIsSearching] = useState(false);

  // TODO: Implement search and indexing functionality
  void searchQuery;
  void onIndexingChange;
  void isSearching;
  void setIsSearching;

  if (!selectedRepo) {
    return (
      <div className="h-full flex items-center justify-center bg-gray-50">
        <div className="text-center max-w-md mx-auto p-8">
          <div className="w-20 h-20 rounded-full bg-purple-100 flex items-center justify-center mx-auto mb-6">
            <DocumentTextIcon className="w-10 h-10 text-purple-600" />
          </div>
          <h2 className="text-2xl font-bold text-gray-900 mb-4">Welcome to CodeWiki</h2>
          <p className="text-gray-600 mb-6">
            Select a repository from the sidebar to explore its documentation.
            CodeWiki provides AI-powered documentation search and chat capabilities.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <MagnifyingGlassIcon className="w-5 h-5 text-purple-600" />
                <h3 className="font-semibold text-gray-900">Smart Search</h3>
              </div>
              <p className="text-gray-600 text-xs">Find information across all documentation files</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <ChatBubbleLeftRightIcon className="w-5 h-5 text-purple-600" />
                <h3 className="font-semibold text-gray-900">AI Chat</h3>
              </div>
              <p className="text-gray-600 text-xs">Ask questions about code and documentation</p>
            </div>
            <div className="bg-white p-4 rounded-lg border border-gray-200">
              <div className="flex items-center gap-2 mb-2">
                <SparklesIcon className="w-5 h-5 text-purple-600" />
                <h3 className="font-semibold text-gray-900">Context Aware</h3>
              </div>
              <p className="text-gray-600 text-xs">Understands your codebase structure and context</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const renderDocumentationItem = (item: DocumentationItem, level = 0) => {
    const getItemIcon = () => {
      switch (item.type) {
        case 'readme':
          return <DocumentTextIcon className="w-4 h-4 text-blue-500" />;
        case 'doc':
          return <DocumentTextIcon className="w-4 h-4 text-gray-500" />;
        case 'code':
          return <CodeBracketIcon className="w-4 h-4 text-green-500" />;
        case 'folder':
          return <FolderIcon className="w-4 h-4 text-yellow-500" />;
      }
    };

    return (
      <div key={item.id}>
        <div
          className={`flex items-center gap-2 px-3 py-2 hover:bg-gray-50 rounded-lg cursor-pointer transition-colors ${
            selectedDoc?.id === item.id ? 'bg-purple-50 border-l-2 border-purple-500' : ''
          }`}
          style={{ paddingLeft: `${12 + level * 16}px` }}
          onClick={() => setSelectedDoc(item)}
        >
          {getItemIcon()}
          <span className="text-sm text-gray-900 truncate flex-1">{item.title}</span>
          <span className="text-xs text-gray-500">{item.lastModified}</span>
        </div>
        {item.children && item.children.map(child => renderDocumentationItem(child, level + 1))}
      </div>
    );
  };

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-gray-200 bg-white">
        <div className="flex items-center justify-between p-4">
          <div>
            <h1 className="text-xl font-bold text-gray-900">CodeWiki</h1>
            <p className="text-sm text-gray-600">Repository Documentation Explorer</p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setChatMode(chatMode === 'browse' ? 'chat' : 'browse')}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors flex items-center gap-2 ${
                chatMode === 'chat'
                  ? 'bg-purple-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {chatMode === 'chat' ? (
                <>
                  <DocumentTextIcon className="w-4 h-4" />
                  Browse
                </>
              ) : (
                <>
                  <ChatBubbleLeftRightIcon className="w-4 h-4" />
                  Chat
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Documentation Tree */}
        <div className="w-80 border-r border-gray-200 bg-gray-50 overflow-y-auto">
          <div className="p-4">
            <h3 className="text-sm font-semibold text-gray-900 mb-3">Documentation</h3>
            <div className="space-y-1">
              {mockDocumentation.map(item => renderDocumentationItem(item))}
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 flex flex-col bg-white">
          {selectedDoc ? (
            <>
              {/* Document Header */}
              <div className="border-b border-gray-200 p-4">
                <div className="flex items-center gap-2 mb-2">
                  {selectedDoc.type === 'readme' && <DocumentTextIcon className="w-5 h-5 text-blue-500" />}
                  {selectedDoc.type === 'doc' && <DocumentTextIcon className="w-5 h-5 text-gray-500" />}
                  {selectedDoc.type === 'code' && <CodeBracketIcon className="w-5 h-5 text-green-500" />}
                  <h2 className="text-lg font-semibold text-gray-900">{selectedDoc.title}</h2>
                </div>
                <p className="text-sm text-gray-600 font-mono">{selectedDoc.path}</p>
              </div>

              {/* Document Content */}
              <div className="flex-1 overflow-y-auto p-6">
                {selectedDoc.content ? (
                  <div className="prose prose-sm max-w-none">
                    <pre className="whitespace-pre-wrap text-sm text-gray-800 font-mono">
                      {selectedDoc.content}
                    </pre>
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center h-full text-center">
                    <DocumentTextIcon className="w-12 h-12 text-gray-400 mb-4" />
                    <p className="text-gray-600">Content preview not available</p>
                    <p className="text-sm text-gray-500 mt-2">File last modified: {selectedDoc.lastModified}</p>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <DocumentTextIcon className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-900 mb-2">Select a document</h3>
                <p className="text-gray-600">Choose a file from the documentation tree to view its content</p>
              </div>
            </div>
          )}

          {/* Chat Interface (when in chat mode) */}
          {chatMode && (
            <div className="border-t border-gray-200 p-4">
              <div className="flex items-center gap-3">
                <ChatBubbleLeftRightIcon className="w-5 h-5 text-purple-600" />
                <input
                  type="text"
                  placeholder="Ask about this repository..."
                  value={chatMessage}
                  onChange={(e) => setChatMessage(e.target.value)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent text-sm"
                />
                <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium rounded-lg transition-colors flex items-center gap-2">
                  <SparklesIcon className="w-4 h-4" />
                  Ask
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}