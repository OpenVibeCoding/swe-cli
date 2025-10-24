/**
 * MCP Settings Component - Table View
 *
 * Displays MCP servers in a table format similar to terminal /mcp list
 * with real-time WebSocket updates
 */

import { useState, useEffect } from 'react';
import { AddMCPServerModal } from './AddMCPServerModal';
import { EditMCPServerModal } from './EditMCPServerModal';
import { MCPToolsModal } from './MCPToolsModal';
import { wsClient } from '../../api/websocket';
import type { MCPServer, MCPServerCreateRequest, MCPServerUpdateRequest, MCPTool } from '../../types/mcp';
import type { WSMessage } from '../../types';
import {
  listMCPServers,
  connectMCPServer,
  disconnectMCPServer,
  testMCPServer,
  createMCPServer,
  updateMCPServer,
  deleteMCPServer,
  getMCPServer,
} from '../../api/mcp';

export function MCPSettings() {
  // Server list state
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal states
  const [showAddModal, setShowAddModal] = useState(false);
  const [showEditModal, setShowEditModal] = useState(false);
  const [showToolsModal, setShowToolsModal] = useState(false);
  const [selectedServer, setSelectedServer] = useState<MCPServer | null>(null);
  const [selectedServerTools, setSelectedServerTools] = useState<MCPTool[]>([]);

  // Action states
  const [processingServer, setProcessingServer] = useState<string | null>(null);

  // Load servers on mount
  useEffect(() => {
    console.log('[MCPSettings] Component mounted, loading servers...');
    loadServers();
  }, []);

  // WebSocket event listener for real-time updates
  useEffect(() => {
    const handleWSMessage = (message: WSMessage) => {
      if (message.type === 'mcp_status_update') {
        const { server_name, status } = message.data;
        console.log('[MCPSettings] Status update via WebSocket:', { server_name, status });
        setServers(prev => prev.map(server =>
          server.name === server_name ? { ...server, status } : server
        ));
      } else if (message.type === 'mcp_servers_update') {
        console.log('[MCPSettings] Full update via WebSocket:', message.data);
        setServers(message.data.servers);
      }
    };

    const unsubscribe1 = wsClient.on('mcp_status_update', handleWSMessage);
    const unsubscribe2 = wsClient.on('mcp_servers_update', handleWSMessage);

    return () => {
      unsubscribe1();
      unsubscribe2();
    };
  }, []);

  const loadServers = async () => {
    setIsLoading(true);
    setError(null);
    try {
      console.log('[MCPSettings] Fetching from /api/mcp/servers...');
      const response = await listMCPServers();
      console.log('[MCPSettings] API Response:', response);
      console.log('[MCPSettings] Servers loaded:', response.servers?.length || 0, 'servers');
      setServers(response.servers || []);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to load servers';
      console.error('[MCPSettings] Load error:', errorMsg, err);
      setError(errorMsg);
    } finally {
      setIsLoading(false);
    }
  };

  const handleConnect = async (name: string) => {
    setProcessingServer(name);
    try {
      await connectMCPServer(name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to connect');
    } finally {
      setProcessingServer(null);
    }
  };

  const handleDisconnect = async (name: string) => {
    setProcessingServer(name);
    try {
      await disconnectMCPServer(name);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect');
    } finally {
      setProcessingServer(null);
    }
  };

  const handleTest = async (name: string) => {
    setProcessingServer(name);
    try {
      const response = await testMCPServer(name);
      alert(response.message || 'Connection test successful');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Test failed');
    } finally {
      setProcessingServer(null);
    }
  };

  const handleViewTools = async (name: string) => {
    try {
      const serverDetail = await getMCPServer(name);
      setSelectedServerTools(serverDetail.tools);
      setSelectedServer(servers.find(s => s.name === name) || null);
      setShowToolsModal(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load tools');
    }
  };

  const handleEdit = (server: MCPServer) => {
    setSelectedServer(server);
    setShowEditModal(true);
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Remove "${name}"? This action cannot be undone.`)) return;

    try {
      await deleteMCPServer(name);
      await loadServers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to remove server');
    }
  };

  const handleAddServer = async (server: MCPServerCreateRequest) => {
    try {
      await createMCPServer(server);
      await loadServers();
      setShowAddModal(false);
    } catch (err) {
      throw err;
    }
  };

  const handleUpdateServer = async (name: string, update: MCPServerUpdateRequest) => {
    try {
      await updateMCPServer(name, update);
      await loadServers();
      setShowEditModal(false);
      setSelectedServer(null);
    } catch (err) {
      throw err;
    }
  };

  // Debug render
  console.log('[MCPSettings] Rendering with:', { isLoading, serversCount: servers.length, error });

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">MCP Servers</h3>
          <p className="text-sm text-gray-500 mt-0.5">
            Manage Model Context Protocol server connections
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors"
        >
          Add Server
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="flex items-center justify-between px-4 py-3 bg-red-50 border border-red-200 rounded-lg">
          <div className="flex items-center gap-3">
            <svg className="w-5 h-5 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm text-red-800">{error}</p>
          </div>
          <button onClick={() => setError(null)} className="text-red-600 hover:text-red-800">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <LoadingState />
      ) : servers.length === 0 ? (
        <EmptyState />
      ) : (
        <ServerTable
          servers={servers}
          processingServer={processingServer}
          onConnect={handleConnect}
          onDisconnect={handleDisconnect}
          onTest={handleTest}
          onViewTools={handleViewTools}
          onEdit={handleEdit}
          onDelete={handleDelete}
        />
      )}

      {/* Footer Info */}
      <div className="pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          <strong>Note:</strong> Connected servers are available in both terminal and web interface.
          Changes take effect immediately.
        </p>
      </div>

      {/* Modals */}
      <AddMCPServerModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onSubmit={handleAddServer}
      />

      <EditMCPServerModal
        isOpen={showEditModal}
        server={selectedServer}
        onClose={() => {
          setShowEditModal(false);
          setSelectedServer(null);
        }}
        onSubmit={handleUpdateServer}
      />

      <MCPToolsModal
        isOpen={showToolsModal}
        serverName={selectedServer?.name || ''}
        tools={selectedServerTools}
        onClose={() => {
          setShowToolsModal(false);
          setSelectedServer(null);
          setSelectedServerTools([]);
        }}
      />
    </div>
  );
}

// ============================================================================
// Sub-components
// ============================================================================

function LoadingState() {
  return (
    <div className="text-center py-12 bg-gray-50 rounded-lg border border-gray-200">
      <div className="inline-flex items-center justify-center w-12 h-12 mb-3">
        <div className="w-8 h-8 border-3 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
      </div>
      <p className="text-sm text-gray-600">Loading MCP servers...</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
      <svg className="w-12 h-12 mx-auto text-gray-300 mb-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M12 5l7 7-7 7" />
      </svg>
      <p className="text-sm text-gray-600 font-medium mb-1">No MCP servers configured</p>
      <p className="text-xs text-gray-500">
        Click "Add Server" above to add your first MCP server
      </p>
    </div>
  );
}

interface ServerTableProps {
  servers: MCPServer[];
  processingServer: string | null;
  onConnect: (name: string) => void;
  onDisconnect: (name: string) => void;
  onTest: (name: string) => void;
  onViewTools: (name: string) => void;
  onEdit: (server: MCPServer) => void;
  onDelete: (name: string) => void;
}

function ServerTable({
  servers,
  processingServer,
  onConnect,
  onDisconnect,
  onTest,
  onViewTools,
  onEdit,
  onDelete,
}: ServerTableProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
              Name
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
              Status
            </th>
            <th className="px-4 py-3 text-left text-xs font-semibold text-gray-700 uppercase tracking-wider">
              Command
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
              Enabled
            </th>
            <th className="px-4 py-3 text-center text-xs font-semibold text-gray-700 uppercase tracking-wider">
              Auto-start
            </th>
            <th className="px-4 py-3 text-right text-xs font-semibold text-gray-700 uppercase tracking-wider">
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {servers.map((server) => (
            <ServerRow
              key={server.name}
              server={server}
              isProcessing={processingServer === server.name}
              onConnect={onConnect}
              onDisconnect={onDisconnect}
              onTest={onTest}
              onViewTools={onViewTools}
              onEdit={onEdit}
              onDelete={onDelete}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface ServerRowProps {
  server: MCPServer;
  isProcessing: boolean;
  onConnect: (name: string) => void;
  onDisconnect: (name: string) => void;
  onTest: (name: string) => void;
  onViewTools: (name: string) => void;
  onEdit: (server: MCPServer) => void;
  onDelete: (name: string) => void;
}

function ServerRow({
  server,
  isProcessing,
  onConnect,
  onDisconnect,
  onTest,
  onViewTools,
  onEdit,
  onDelete,
}: ServerRowProps) {
  const isConnected = server.status === 'connected';

  return (
    <tr className="hover:bg-gray-50 transition-colors">
      {/* Name */}
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="text-sm font-medium text-gray-900">{server.name}</div>
        <div className="text-xs text-gray-500">{server.config_location}</div>
      </td>

      {/* Status */}
      <td className="px-4 py-3 whitespace-nowrap">
        <div className="flex items-center gap-2">
          {isProcessing ? (
            <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-900 rounded-full animate-spin" />
          ) : (
            <>
              {isConnected ? (
                <>
                  <svg className="w-4 h-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm font-medium text-green-700">Connected</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
                  </svg>
                  <span className="text-sm text-gray-600">Disconnected</span>
                </>
              )}
            </>
          )}
        </div>
      </td>

      {/* Command */}
      <td className="px-4 py-3">
        <div className="text-sm text-gray-900 font-mono truncate max-w-xs" title={`${server.config.command} ${server.config.args.join(' ')}`}>
          {server.config.command} {server.config.args.slice(0, 2).join(' ')}
          {server.config.args.length > 2 && '...'}
        </div>
      </td>

      {/* Enabled */}
      <td className="px-4 py-3 text-center whitespace-nowrap">
        {server.config.enabled ? (
          <svg className="w-5 h-5 text-green-600 mx-auto" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>

      {/* Auto-start */}
      <td className="px-4 py-3 text-center whitespace-nowrap">
        {server.config.auto_start ? (
          <svg className="w-5 h-5 text-green-600 mx-auto" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        ) : (
          <span className="text-gray-400">-</span>
        )}
      </td>

      {/* Actions */}
      <td className="px-4 py-3 text-right whitespace-nowrap">
        <div className="flex items-center justify-end gap-1">
          {isConnected ? (
            <>
              <button
                onClick={() => onViewTools(server.name)}
                disabled={isProcessing}
                className="px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
                title="View Tools"
              >
                Tools
              </button>
              <button
                onClick={() => onDisconnect(server.name)}
                disabled={isProcessing}
                className="px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
                title="Disconnect"
              >
                Disconnect
              </button>
            </>
          ) : (
            <button
              onClick={() => onConnect(server.name)}
              disabled={isProcessing}
              className="px-2 py-1 text-xs font-medium text-white bg-gray-900 hover:bg-gray-800 rounded transition-colors disabled:opacity-50"
              title="Connect"
            >
              Connect
            </button>
          )}
          <button
            onClick={() => onTest(server.name)}
            disabled={isProcessing}
            className="px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
            title="Test Connection"
          >
            Test
          </button>
          <button
            onClick={() => onEdit(server)}
            disabled={isProcessing}
            className="px-2 py-1 text-xs font-medium text-gray-700 hover:bg-gray-100 rounded transition-colors disabled:opacity-50"
            title="Edit"
          >
            Edit
          </button>
          <button
            onClick={() => onDelete(server.name)}
            disabled={isProcessing}
            className="px-2 py-1 text-xs font-medium text-red-700 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
            title="Remove"
          >
            Remove
          </button>
        </div>
      </td>
    </tr>
  );
}
