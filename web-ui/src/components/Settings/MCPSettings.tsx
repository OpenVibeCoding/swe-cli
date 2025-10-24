import { useState } from 'react';

// TODO: Connect to actual MCP server management API
export function MCPSettings() {
  const [servers, setServers] = useState<Array<{
    name: string;
    command: string;
    enabled: boolean;
  }>>([]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-medium text-gray-900">MCP Servers</h3>
          <p className="text-xs text-gray-500 mt-1">
            Manage Model Context Protocol server connections
          </p>
        </div>
        <button className="px-3 py-1.5 text-sm font-medium text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-colors">
          Add Server
        </button>
      </div>

      {servers.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 rounded-lg border-2 border-dashed border-gray-200">
          <div className="text-gray-400 mb-2">
            <svg className="w-12 h-12 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M12 5l7 7-7 7" />
            </svg>
          </div>
          <p className="text-sm text-gray-600 mb-1">No MCP servers configured</p>
          <p className="text-xs text-gray-500">
            Add your first MCP server to extend SWE-CLI capabilities
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {servers.map((server, index) => (
            <div
              key={index}
              className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200"
            >
              <div className="flex-1">
                <h4 className="text-sm font-medium text-gray-900">{server.name}</h4>
                <p className="text-xs text-gray-500 font-mono mt-1">{server.command}</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                    server.enabled ? 'bg-green-600' : 'bg-gray-300'
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      server.enabled ? 'translate-x-6' : 'translate-x-1'
                    }`}
                  />
                </button>
                <button className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 rounded transition-colors">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500">
          <strong>Note:</strong> MCP server changes will be synchronized with the terminal session.
          Changes take effect immediately after saving.
        </p>
      </div>
    </div>
  );
}
