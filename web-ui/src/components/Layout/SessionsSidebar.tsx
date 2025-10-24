import { useState, useEffect } from 'react';
import { ChevronDownIcon, Cog6ToothIcon, Bars3Icon, XMarkIcon } from '@heroicons/react/24/outline';
import { useChatStore } from '../../stores/chat';
import { SettingsModal } from '../Settings/SettingsModal';
import { NewSessionModal } from './NewSessionModal';
import { DeleteConfirmModal } from './DeleteConfirmModal';
import { apiClient } from '../../api/client';

interface Session {
  id: string;
  working_dir: string;
  message_count: number;
  token_usage: {
    prompt_tokens: number;
    completion_tokens: number;
  };
  created_at: string;
  updated_at: string;
  status?: 'active' | 'answered' | 'open';
}

interface WorkspaceGroup {
  path: string;
  sessions: Session[];
  mostRecent: Session;
}

export function SessionsSidebar() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceGroup[]>([]);
  const [expandedWorkspaces, setExpandedWorkspaces] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNewSessionOpen, setIsNewSessionOpen] = useState(false);
  const [deleteWorkspace, setDeleteWorkspace] = useState<WorkspaceGroup | null>(null);
  const [deleteSessionId, setDeleteSessionId] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  // Get loadSession from chat store
  const loadSession = useChatStore(state => state.loadSession);
  const currentSessionId = useChatStore(state => state.currentSessionId);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await fetch('/api/sessions');
      const data = await response.json();
      setSessions(data);

      // Group sessions by workspace
      const grouped = groupByWorkspace(data);
      setWorkspaces(grouped);
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const groupByWorkspace = (sessions: Session[]): WorkspaceGroup[] => {
    const groups: Record<string, Session[]> = {};

    // Filter out sessions without a working directory
    sessions.forEach(session => {
      if (!session.working_dir || session.working_dir.trim() === '') {
        return; // Skip sessions without working_dir
      }
      const path = session.working_dir;
      if (!groups[path]) {
        groups[path] = [];
      }
      groups[path].push(session);
    });

    // Convert to array and sort each group by updated_at
    return Object.entries(groups).map(([path, sessions]) => {
      const sorted = sessions.sort((a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );
      return {
        path,
        sessions: sorted,
        mostRecent: sorted[0],
      };
    }).sort((a, b) =>
      new Date(b.mostRecent.updated_at).getTime() - new Date(a.mostRecent.updated_at).getTime()
    );
  };

  const formatWorkspacePath = (workingDir: string) => {
    // Show full path, or just the last part if too long
    if (!workingDir) return 'Unknown';
    return workingDir;
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const toggleWorkspace = (workspacePath: string, e: React.MouseEvent) => {
    e.stopPropagation();
    console.log('[SessionsSidebar] Toggling workspace:', workspacePath);
    setExpandedWorkspaces(prev => {
      const next = new Set(prev);
      if (next.has(workspacePath)) {
        console.log('[SessionsSidebar] Collapsing workspace');
        next.delete(workspacePath);
      } else {
        console.log('[SessionsSidebar] Expanding workspace');
        next.add(workspacePath);
      }
      return next;
    });
  };

  const handleSessionClick = async (session: Session, e: React.MouseEvent) => {
    e.stopPropagation();
    console.log('[SessionsSidebar] Session clicked:', session.id);
    await loadSession(session.id);
  };

  const handleNewWorkspace = () => {
    setIsNewSessionOpen(true);
  };

  const handleNewSessionInWorkspace = async (workspacePath: string, e: React.MouseEvent) => {
    e.stopPropagation();
    console.log('[SessionsSidebar] Creating new session for workspace:', workspacePath);

    try {
      const result = await apiClient.createSession(workspacePath);
      console.log('[SessionsSidebar] New session created:', result);

      // Refresh sessions list
      await fetchSessions();

      // Load the new session
      if (result.session && result.session.id) {
        await loadSession(result.session.id);
      }
    } catch (error) {
      console.error('[SessionsSidebar] Failed to create session:', error);
      alert('Failed to create new session');
    }
  };

  const handleDeleteWorkspace = (workspace: WorkspaceGroup, e: React.MouseEvent) => {
    e.stopPropagation();
    setDeleteWorkspace(workspace);
  };

  const handleDeleteSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    console.log('[SessionsSidebar] Delete session clicked:', sessionId);
    setDeleteSessionId(sessionId);
  };

  const confirmDeleteSession = async () => {
    if (!deleteSessionId) return;

    try {
      console.log('[SessionsSidebar] Deleting session:', deleteSessionId);
      await fetch(`/api/sessions/${deleteSessionId}`, { method: 'DELETE' });

      // Refresh the sessions list
      await fetchSessions();

      setDeleteSessionId(null);
    } catch (error) {
      console.error('Failed to delete session:', error);
      alert('Failed to delete session');
    }
  };

  const confirmDelete = async () => {
    if (!deleteWorkspace) return;

    try {
      // Delete all sessions for this workspace
      for (const session of deleteWorkspace.sessions) {
        await fetch(`/api/sessions/${session.id}`, { method: 'DELETE' });
      }

      // Refresh the sessions list
      await fetchSessions();

      // Remove from expanded workspaces if it was expanded
      setExpandedWorkspaces(prev => {
        const next = new Set(prev);
        next.delete(deleteWorkspace.path);
        return next;
      });

      setDeleteWorkspace(null);
    } catch (error) {
      console.error('Failed to delete workspace:', error);
      alert('Failed to delete workspace');
    }
  };

  return (
    <aside className={`h-full bg-gradient-to-b from-gray-50 to-white border-r border-gray-200 flex flex-col shadow-sm transition-all duration-300 ${
      isCollapsed ? 'w-16' : 'w-88'
    }`}>
      {/* Logo and Brand - Centered */}
      <div className={`border-b border-gray-200 flex flex-col items-center ${isCollapsed ? 'p-3' : 'p-6'}`}>
        {/* Toggle Button */}
        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="mb-3 p-2 rounded-lg hover:bg-gray-200 transition-colors self-end"
          title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {isCollapsed ? (
            <Bars3Icon className="w-5 h-5 text-gray-600" />
          ) : (
            <XMarkIcon className="w-5 h-5 text-gray-600" />
          )}
        </button>

        {!isCollapsed && (
          <>
        <div className="flex flex-col items-center gap-2 mb-2">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-md">
            <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
            </svg>
          </div>
          <div className="text-center">
            <h1 className="text-lg font-bold text-gray-900">SWE-CLI</h1>
            <p className="text-xs text-gray-500">AI Coding Assistant</p>
          </div>
        </div>

        {/* New Workspace Button */}
        <button
          onClick={handleNewWorkspace}
          className="w-full mt-3 px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white text-sm font-medium rounded-lg shadow-md hover:shadow-lg transition-all duration-200 flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          <span>New Workspace</span>
        </button>
          </>
        )}
      </div>

      {/* Workspaces Header */}
      {!isCollapsed && (
      <>
        <div className="px-5 py-4 border-b border-gray-100">
          <h2 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Workspaces</h2>
        </div>

        {/* Workspaces List */}
        <div className="flex-1 overflow-y-auto px-3 py-2">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-12 px-4">
            <div className="w-8 h-8 border-2 border-gray-200 border-t-blue-500 rounded-full animate-spin mb-3" />
            <p className="text-sm text-gray-500">Loading workspaces...</p>
          </div>
        ) : workspaces.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
            </div>
            <h3 className="text-sm font-medium text-gray-900 mb-1">No workspaces yet</h3>
            <p className="text-xs text-gray-500 max-w-[200px]">
              Start a conversation to create your first workspace
            </p>
          </div>
        ) : (
          <div className="space-y-2">
            {workspaces.map((workspace) => {
              const isExpanded = expandedWorkspaces.has(workspace.path);
              // Check if any session in this workspace is currently active
              const hasActiveSession = workspace.sessions.some(s => s.id === currentSessionId);

              return (
                <div
                  key={workspace.path}
                  className="relative w-full rounded-lg transition-all duration-200 bg-white border border-gray-200 hover:border-gray-300 hover:shadow-sm"
                >
                  {/* Workspace Header - Clickable to expand/collapse */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleWorkspace(workspace.path, e);
                    }}
                    className="w-full px-3 py-3 text-left group cursor-pointer hover:bg-gray-50 transition-colors rounded-t-lg"
                  >
                    <div className="flex items-start gap-2 pr-10">
                      {/* Expand/Collapse Chevron */}
                      <ChevronDownIcon
                        className={`mt-0.5 w-4 h-4 flex-shrink-0 text-gray-500 transition-transform duration-200 ${
                          isExpanded ? 'transform rotate-0' : 'transform -rotate-90'
                        }`}
                      />

                      {/* Folder Icon */}
                      <div className="mt-0.5 w-4 h-4 rounded flex-shrink-0 flex items-center justify-center bg-gray-100 group-hover:bg-gray-200">
                        <svg className="w-2.5 h-2.5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
                        </svg>
                      </div>

                      {/* Workspace Info */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-sm font-medium line-clamp-2 mb-1.5 text-gray-900">
                          {formatWorkspacePath(workspace.path)}
                        </h3>
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-gray-500">
                            {formatDate(workspace.mostRecent.updated_at)}
                          </span>
                          <span className={`px-1.5 py-0.5 rounded-full text-xs ${
                            hasActiveSession
                              ? 'bg-blue-100 text-blue-700 font-medium'
                              : 'bg-gray-100 text-gray-600'
                          }`}>
                            {workspace.sessions.length} session{workspace.sessions.length !== 1 ? 's' : ''}
                          </span>
                        </div>
                      </div>
                    </div>
                  </button>

                  {/* Delete Button - Positioned absolutely */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleDeleteWorkspace(workspace, e);
                    }}
                    className="absolute top-3 right-3 w-7 h-7 rounded-md flex items-center justify-center hover:bg-red-100 transition-colors text-gray-400 hover:text-red-600 bg-white shadow-sm z-10"
                    title="Delete workspace"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>

                  {/* Sessions List (Expanded) */}
                  {isExpanded && (
                    <div className="px-3 pb-2 space-y-1 border-t border-gray-100 pt-2">
                      {/* Add New Session Button */}
                      <button
                        onClick={(e) => handleNewSessionInWorkspace(workspace.path, e)}
                        className="w-full px-3 py-2 rounded-md text-left transition-colors cursor-pointer bg-gray-100 hover:bg-gray-200 border border-dashed border-gray-300 hover:border-blue-400 flex items-center gap-2 text-gray-600 hover:text-blue-600"
                      >
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                        </svg>
                        <span className="text-xs font-medium">New Session</span>
                      </button>

                      {/* Sessions List */}
                      {workspace.sessions.map((session) => {
                        const isActiveSession = currentSessionId === session.id;

                        return (
                          <div key={session.id} className="relative group">
                            <button
                              onClick={(e) => handleSessionClick(session, e)}
                              className={`w-full px-3 py-2.5 pr-10 rounded-md text-left transition-all cursor-pointer ${
                                isActiveSession
                                  ? 'bg-gradient-to-r from-blue-50 to-blue-100 border-2 border-blue-400 shadow-sm'
                                  : 'bg-gray-50 hover:bg-gray-100 border border-gray-200 hover:border-blue-300 hover:shadow-sm'
                              }`}
                            >
                              <div className="flex items-center justify-between text-xs mb-1">
                                <span className={`font-semibold ${
                                  isActiveSession ? 'text-blue-900' : 'text-gray-700'
                                }`}>
                                  {isActiveSession && '● '}{session.id.substring(0, 8)}
                                </span>
                                <span className={`font-medium ${
                                  isActiveSession ? 'text-blue-700' : 'text-gray-500'
                                }`}>
                                  {session.message_count} msgs
                                </span>
                              </div>
                              <div className={`text-xs ${
                                isActiveSession ? 'text-blue-600 font-medium' : 'text-gray-500'
                              }`}>
                                {formatDate(session.updated_at)}
                              </div>
                            </button>

                            {/* Delete Session Button */}
                            <button
                              onClick={(e) => handleDeleteSession(session.id, e)}
                              className="absolute top-1.5 right-1.5 w-6 h-6 rounded flex items-center justify-center opacity-0 group-hover:opacity-100 hover:bg-red-100 transition-all text-gray-400 hover:text-red-600 z-10"
                              title="Delete session"
                            >
                              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                              </svg>
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
        </div>
      </>
      )}

      {/* Footer */}
      {!isCollapsed ? (
      <div className="p-4 border-t border-gray-200 bg-gray-50">
        <button
          onClick={() => setIsSettingsOpen(true)}
          className="w-full px-4 py-2.5 text-sm font-medium text-gray-700 hover:text-gray-900 bg-white hover:bg-gray-100 border border-gray-200 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 shadow-sm hover:shadow"
        >
          <Cog6ToothIcon className="w-4 h-4" />
          <span>Settings</span>
        </button>
      </div>
      ) : (
        /* Collapsed Footer - Just Settings Icon */
        <div className="p-2 border-t border-gray-200 bg-gray-50">
          <button
            onClick={() => setIsSettingsOpen(true)}
            className="w-full p-2 text-gray-700 hover:text-gray-900 bg-white hover:bg-gray-100 border border-gray-200 rounded-lg transition-all duration-200 flex items-center justify-center shadow-sm hover:shadow"
            title="Settings"
          >
            <Cog6ToothIcon className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />

      {/* New Session Modal */}
      <NewSessionModal
        isOpen={isNewSessionOpen}
        onClose={() => setIsNewSessionOpen(false)}
      />

      {/* Delete Workspace Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteWorkspace !== null}
        workspacePath={deleteWorkspace?.path || ''}
        onConfirm={confirmDelete}
        onCancel={() => setDeleteWorkspace(null)}
      />

      {/* Delete Session Confirmation Modal */}
      {deleteSessionId && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            zIndex: 99999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
          onClick={() => setDeleteSessionId(null)}
        >
          <div
            style={{
              backgroundColor: 'white',
              padding: '24px',
              borderRadius: '12px',
              minWidth: '400px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)'
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 style={{ margin: '0 0 12px 0', fontSize: '18px', fontWeight: '600', color: '#1f2937' }}>
              Delete Session
            </h3>
            <p style={{ margin: '0 0 20px 0', fontSize: '14px', color: '#6b7280' }}>
              Are you sure you want to delete session <strong>{deleteSessionId.substring(0, 8)}</strong>?
              <br />
              This action cannot be undone.
            </p>
            <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
              <button
                onClick={() => setDeleteSessionId(null)}
                style={{
                  padding: '8px 16px',
                  border: '1px solid #d1d5db',
                  backgroundColor: 'white',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#374151'
                }}
              >
                Cancel
              </button>
              <button
                onClick={confirmDeleteSession}
                style={{
                  padding: '8px 16px',
                  backgroundColor: '#ef4444',
                  color: 'white',
                  border: 'none',
                  borderRadius: '8px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: '500'
                }}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
