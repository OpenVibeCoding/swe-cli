import { useState, useEffect, useRef, useMemo } from 'react';
import { ChevronDownIcon, Cog6ToothIcon, Bars3Icon, XMarkIcon, FolderIcon, PlusIcon, TrashIcon, MagnifyingGlassIcon, EllipsisVerticalIcon, DocumentDuplicateIcon, ArrowsUpDownIcon } from '@heroicons/react/24/outline';
import { useChatStore } from '../../stores/chat';
import { SettingsModal } from '../Settings/SettingsModal';
import { NewSessionModal } from './NewSessionModal';
import { DeleteConfirmModal } from './DeleteConfirmModal';
import { apiClient } from '../../api/client';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { IconButton } from '../ui/IconButton';
import { Input } from '../ui/Input';
import { SegmentedControl } from '../ui/SegmentedControl';

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
  const [_sessions, setSessions] = useState<Session[]>([]);
  const [workspaces, setWorkspaces] = useState<WorkspaceGroup[]>([]);
  const [expandedWorkspaces, setExpandedWorkspaces] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isNewSessionOpen, setIsNewSessionOpen] = useState(false);
  const [deleteWorkspace, setDeleteWorkspace] = useState<WorkspaceGroup | null>(null);
  const [deleteSessionId, setDeleteSessionId] = useState<string | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState<'all' | 'active' | 'recent'>('all');
  const [menuWorkspacePath, setMenuWorkspacePath] = useState<string | null>(null);
  const searchRef = useRef<HTMLInputElement>(null);
  const [focusedWorkspacePath, setFocusedWorkspacePath] = useState<string | null>(null);
  const [focusedSessionIndex, setFocusedSessionIndex] = useState<number | null>(null);
  const [isCompact, setIsCompact] = useState(false);
  const listSpacingCls = isCompact ? 'space-y-1.5' : 'space-y-2';

  // Get loadSession from chat store (must be declared before useMemo below)
  const loadSession = useChatStore(state => state.loadSession);
  const currentSessionId = useChatStore(state => state.currentSessionId);

  const visibleWorkspaces = useMemo(() => {
    const q = searchQuery.toLowerCase().trim();
    const list = workspaces
      .filter(ws => !q || ws.path.toLowerCase().includes(q))
      .filter(ws => filter === 'active' ? ws.sessions.some(s => s.id === currentSessionId) : true);
    if (filter === 'recent') {
      return [...list].sort((a, b) => new Date(b.mostRecent.updated_at).getTime() - new Date(a.mostRecent.updated_at).getTime());
    }
    return list;
  }, [workspaces, searchQuery, filter, currentSessionId]);

  const rowIdForPath = (p: string) => 'ws-' + p.replace(/[^a-zA-Z0-9_-]/g, '-');
  const rowIdForSession = (p: string, i: number) => `${rowIdForPath(p)}-s-${i}`;

  useEffect(() => {
    // Reset focus to first visible when filters/search change
    if (visibleWorkspaces.length > 0) {
      setFocusedWorkspacePath(visibleWorkspaces[0].path);
      setFocusedSessionIndex(null);
    } else {
      setFocusedWorkspacePath(null);
      setFocusedSessionIndex(null);
    }
  }, [visibleWorkspaces]);

  useEffect(() => {
    if (!focusedWorkspacePath) return;
    const el = focusedSessionIndex !== null
      ? document.getElementById(rowIdForSession(focusedWorkspacePath, focusedSessionIndex))
      : document.getElementById(rowIdForPath(focusedWorkspacePath));
    el?.scrollIntoView({ block: 'nearest' });
  }, [focusedWorkspacePath, focusedSessionIndex]);


  useEffect(() => {
    fetchSessions();
  }, []);

  // Keyboard shortcut to toggle sidebar (Ctrl/Cmd + B)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        setIsCollapsed(prev => !prev);
      }
    };

    document.addEventListener('keydown', handleKeyDown);

    const handleFocusSearch = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f') {
        e.preventDefault();
        if (isCollapsed) {
          setIsCollapsed(false);
          setTimeout(() => searchRef.current?.focus(), 120);
        } else {
          searchRef.current?.focus();
        }
      }
      if (e.key === 'Escape') {
        setMenuWorkspacePath(null);
      }
    };
    document.addEventListener('keydown', handleFocusSearch);

    const handleListNavigation = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const tag = target?.tagName;
      if (tag === 'INPUT' || tag === 'TEXTAREA' || (target as any)?.isContentEditable) return;
      if (isCollapsed) return; // navigation only when expanded
      if (visibleWorkspaces.length === 0) return;

      const currentIndex = focusedWorkspacePath
        ? visibleWorkspaces.findIndex(w => w.path === focusedWorkspacePath)
        : -1;

      const prevent = () => { e.preventDefault(); setMenuWorkspacePath(null); };

      const currentWs = currentIndex >= 0 ? visibleWorkspaces[currentIndex] : null;
      const isExpanded = currentWs ? expandedWorkspaces.has(currentWs.path) : false;
      const sessionCount = currentWs ? currentWs.sessions.length : 0;

      if (e.key === 'ArrowDown') {
        prevent();
        if (isExpanded && sessionCount > 0) {
          if (focusedSessionIndex === null) {
            setFocusedSessionIndex(0);
            return;
          }
          if (focusedSessionIndex < sessionCount - 1) {
            setFocusedSessionIndex(focusedSessionIndex + 1);
            return;
          }
          // move to next workspace
          const next = Math.min(currentIndex + 1, visibleWorkspaces.length - 1);
          setFocusedWorkspacePath(visibleWorkspaces[next].path);
          setFocusedSessionIndex(null);
        } else {
          const next = currentIndex < 0 ? 0 : Math.min(currentIndex + 1, visibleWorkspaces.length - 1);
          setFocusedWorkspacePath(visibleWorkspaces[next].path);
          setFocusedSessionIndex(null);
        }
      } else if (e.key === 'ArrowUp') {
        prevent();
        if (focusedSessionIndex !== null) {
          if (focusedSessionIndex > 0) {
            setFocusedSessionIndex(focusedSessionIndex - 1);
            return;
          }
          // move focus back to workspace header
          setFocusedSessionIndex(null);
          return;
        }
        const prev = currentIndex < 0 ? 0 : Math.max(currentIndex - 1, 0);
        setFocusedWorkspacePath(visibleWorkspaces[prev].path);
        setFocusedSessionIndex(null);
      } else if (e.key === 'Enter' || e.key === ' ') {
        if (focusedWorkspacePath && currentWs) {
          prevent();
          if (focusedSessionIndex === null) {
            setExpandedWorkspaces(prev => {
              const next = new Set(prev);
              if (next.has(focusedWorkspacePath)) next.delete(focusedWorkspacePath);
              else next.add(focusedWorkspacePath);
              return next;
            });
          } else {
            const session = currentWs.sessions[focusedSessionIndex];
            if (session) {
              // trigger session load
              loadSession(session.id);
            }
          }
        }
      } else if (e.key === 'ArrowRight') {
        if (focusedWorkspacePath) {
          prevent();
          if (focusedSessionIndex === null) {
            setExpandedWorkspaces(prev => {
              const next = new Set(prev);
              next.add(focusedWorkspacePath);
              return next;
            });
          }
        }
      } else if (e.key === 'ArrowLeft') {
        if (focusedWorkspacePath) {
          prevent();
          if (focusedSessionIndex !== null) {
            setFocusedSessionIndex(null);
            return;
          }
          setExpandedWorkspaces(prev => {
            const next = new Set(prev);
            next.delete(focusedWorkspacePath);
            return next;
          });
        }
      }
    };
    document.addEventListener('keydown', handleListNavigation);

    const handleClickAway = (e: MouseEvent) => {
      // Close menu on outside click
      setMenuWorkspacePath(null);
    };
    document.addEventListener('click', handleClickAway);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('keydown', handleFocusSearch);
      document.removeEventListener('keydown', handleListNavigation);
      document.removeEventListener('click', handleClickAway);
    };
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
    <aside className={`h-full bg-gradient-to-b from-gray-50 to-white border-r border-gray-200 flex flex-col shadow-sm transition-all duration-300 ease-in-out ${
      isCollapsed ? 'w-16' : 'w-80'
    } relative`}>
      {/* Sidebar Header */}
      <div className={`sticky top-0 z-10 border-b border-gray-200 ${isCollapsed ? 'p-3' : 'p-3'} bg-white/90 backdrop-blur`}>        
        <div className="flex items-center justify-between">
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={`p-2 rounded-lg transition-colors ${
              isCollapsed ? 'hover:bg-gray-200 bg-white shadow-sm' : 'hover:bg-gray-100'
            }`}
            title={`${isCollapsed ? 'Expand' : 'Collapse'} sidebar (Ctrl/Cmd+B)`}
          >
            {isCollapsed ? (
              <Bars3Icon className="w-5 h-5 text-gray-600" />
            ) : (
              <XMarkIcon className="w-5 h-5 text-gray-600" />
            )}
          </button>
          {!isCollapsed && (
            <span className="text-sm font-semibold text-gray-900">Workspaces</span>
          )}
          {!isCollapsed ? (
            <div className="flex items-center gap-1">
              <IconButton
                aria-label="Toggle density"
                title="Toggle density"
                variant="subtle"
                size="sm"
                onClick={() => setIsCompact(v => !v)}
              >
                <ArrowsUpDownIcon className="w-5 h-5" />
              </IconButton>
              <IconButton
                aria-label="New workspace"
                title="New workspace"
                onClick={handleNewWorkspace}
                variant="subtle"
                size="sm"
              >
                <PlusIcon className="w-5 h-5" />
              </IconButton>
            </div>
          ) : (
            <span className="w-5" />
          )}
        </div>

        {!isCollapsed && (
          <div className="mt-3 space-y-2">
            <Input
              ref={searchRef}
              placeholder="Search workspaces…"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              leftIcon={<MagnifyingGlassIcon className="w-4 h-4" />}
            />
            <div className="flex items-center justify-between">
              <SegmentedControl
                options={[
                  { label: 'All', value: 'all' },
                  { label: 'Active', value: 'active' },
                  { label: 'Recent', value: 'recent' },
                ]}
                value={filter}
                onChange={setFilter}
              />
              <span className="text-xs text-gray-400">{visibleWorkspaces.length} items</span>
            </div>
          </div>
        )}
      </div>

  
      {/* Workspaces Header */}
      {!isCollapsed && (
      <>
        {/* Workspaces List */}
        <div className="flex-1 overflow-y-auto px-3 py-2">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-10 px-4">
            <div className="w-8 h-8 border-2 border-gray-200 border-t-blue-500 rounded-full animate-spin mb-3" />
            <p className="text-sm text-gray-500">Loading workspaces...</p>
          </div>
        ) : workspaces.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
            <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
              <FolderIcon className="w-8 h-8 text-gray-400" />
            </div>
            <h3 className="text-sm font-medium text-gray-900 mb-1">No workspaces yet</h3>
            <p className="text-xs text-gray-500 max-w-[200px]">
              Start a conversation to create your first workspace
            </p>
          </div>
        ) : (
          <div className={listSpacingCls}>
            {visibleWorkspaces.map((workspace) => {
              const isExpanded = expandedWorkspaces.has(workspace.path);
              const hasActiveSession = workspace.sessions.some(s => s.id === currentSessionId);
              const isFocusedWorkspace = focusedWorkspacePath === workspace.path && focusedSessionIndex === null;

              return (
                <div
                  key={workspace.path}
                  id={rowIdForPath(workspace.path)}
                  className={`relative w-full rounded-lg transition-all duration-200 bg-white border ${isFocusedWorkspace ? 'border-blue-400 ring-2 ring-blue-200' : 'border-gray-200'} hover:border-gray-300 hover:shadow-sm`}
                >
                  {/* Workspace Header - Clickable to expand/collapse */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleWorkspace(workspace.path, e);
                    }}
                    className={`w-full px-3 ${isCompact ? 'py-2' : 'py-3'} text-left group cursor-pointer hover:bg-gray-50 transition-colors rounded-t-lg`}
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
                        <FolderIcon className="w-3.5 h-3.5 text-gray-500" />
                      </div>

                      {/* Workspace Info */}
                      <div className="flex-1 min-w-0">
                        <h3 className="text-xs font-medium mb-1.5 text-gray-900 break-all" title={workspace.path}>
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

                  {/* Row actions: overflow menu */}
                  <div className="absolute top-2 right-2 z-20">
                    <IconButton
                      aria-label="More"
                      title="More"
                      variant="subtle"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuWorkspacePath(prev => prev === workspace.path ? null : workspace.path);
                      }}
                    >
                      <EllipsisVerticalIcon className="w-5 h-5" />
                    </IconButton>

                    {menuWorkspacePath === workspace.path && (
                      <div
                        className="absolute right-0 mt-1 w-44 bg-white border border-gray-200 rounded-lg shadow-lg overflow-hidden"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <button
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={(e) => handleNewSessionInWorkspace(workspace.path, e)}
                        >
                          <PlusIcon className="w-4 h-4 text-gray-500" />
                          New session
                        </button>
                        <button
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                          onClick={() => navigator.clipboard?.writeText(workspace.path)}
                        >
                          <DocumentDuplicateIcon className="w-4 h-4 text-gray-500" />
                          Copy path
                        </button>
                        <div className="my-1 h-px bg-gray-200" />
                        <button
                          className="w-full flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50"
                          onClick={(e) => handleDeleteWorkspace(workspace, e)}
                        >
                          <TrashIcon className="w-4 h-4" />
                          Delete workspace
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Sessions List (Expanded) */}
                  {isExpanded && (
                    <div className="px-3 pb-2 space-y-1 border-t border-gray-100 pt-2">
                      {/* Add New Session Button */}
                      <button
                        onClick={(e) => handleNewSessionInWorkspace(workspace.path, e)}
                        className="w-full px-3 py-2 rounded-md text-left transition-colors cursor-pointer bg-gray-100 hover:bg-gray-200 border border-dashed border-gray-300 hover:border-blue-400 flex items-center gap-2 text-gray-600 hover:text-blue-600"
                      >
                        <PlusIcon className="w-3.5 h-3.5" />
                        <span className="text-xs font-medium">New Session</span>
                      </button>

                      {/* Sessions List */}
                      {workspace.sessions.map((session, idx) => {
                        const isActiveSession = currentSessionId === session.id;
                        const isFocusedSession = focusedWorkspacePath === workspace.path && focusedSessionIndex === idx;

                        return (
                          <div id={rowIdForSession(workspace.path, idx)} key={session.id} className={`relative group ${isFocusedSession ? 'ring-2 ring-blue-200 border-blue-400 rounded-md' : ''}`}>
                            <button
                              onClick={(e) => handleSessionClick(session, e)}
                              className={`w-full px-3 ${isCompact ? 'py-2' : 'py-2.5'} pr-10 rounded-md text-left transition-all cursor-pointer ${
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
                              <TrashIcon className="w-3.5 h-3.5" />
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

      {/* Collapsed State - Minimal Workspace Indicators */}
      {isCollapsed && (
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-2">
          {workspaces.map((workspace) => {
            const hasActiveSession = workspace.sessions.some(s => s.id === currentSessionId);
            
            return (
              <div
                key={workspace.path}
                className="relative group"
                title={`${formatWorkspacePath(workspace.path)} (${workspace.sessions.length} sessions)`}
              >
                <button
                  onClick={() => {
                    // Expand sidebar and select this workspace
                    setIsCollapsed(false);
                    // Auto-expand this workspace after sidebar expands
                    setTimeout(() => {
                      setExpandedWorkspaces(prev => new Set([...prev, workspace.path]));
                    }, 100);
                  }}
                  className={`w-full aspect-square rounded-lg flex items-center justify-center transition-colors duration-200 ${
                    hasActiveSession
                      ? 'bg-blue-100 border-2 border-blue-400 shadow-sm'
                      : 'bg-gray-100 hover:bg-gray-200 border border-gray-200 hover:border-gray-300 hover:shadow-sm'
                  }`}
                >
                  <FolderIcon className={`w-5 h-5 ${hasActiveSession ? 'text-blue-600' : 'text-gray-500'}`} />
                </button>
                
                {/* Tooltip */}
                <div className="absolute left-full ml-2 top-1/2 transform -translate-y-1/2 bg-gray-900 text-white text-xs rounded-lg px-3 py-2 whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity duration-200 pointer-events-none z-50 shadow-lg">
                  <div className="font-medium text-sm mb-1">{formatWorkspacePath(workspace.path)}</div>
                  <div className="text-gray-300 text-xs">{workspace.sessions.length} session{workspace.sessions.length !== 1 ? 's' : ''}</div>
                  {hasActiveSession && <div className="text-blue-300 text-xs mt-1">● Active</div>}
                  {/* Arrow */}
                  <div className="absolute right-full top-1/2 transform -translate-y-1/2 border-4 border-transparent border-r-gray-900"></div>
                </div>
              </div>
            );
          })}
          
          {/* New Workspace Button (Collapsed) */}
          <button
            onClick={() => {
              setIsCollapsed(false);
              setTimeout(() => setIsNewSessionOpen(true), 100);
            }}
            className="w-full aspect-square rounded-lg flex items-center justify-center bg-gray-50 hover:bg-gray-100 border border-dashed border-gray-300 hover:border-blue-400 text-gray-600 hover:text-blue-600 transition-colors"
            title="New Workspace"
          >
            <PlusIcon className="w-5 h-5" />
          </button>
        </div>
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
      <Modal
        isOpen={!!deleteSessionId}
        onClose={() => setDeleteSessionId(null)}
        title="Delete Session"
        footer={
          <div className="flex gap-3 justify-end">
            <Button variant="secondary" onClick={() => setDeleteSessionId(null)}>Cancel</Button>
            <Button variant="danger" onClick={confirmDeleteSession}>Delete</Button>
          </div>
        }
      >
        {deleteSessionId && (
          <p className="text-sm text-gray-700">
            Are you sure you want to delete session <strong>{deleteSessionId.substring(0, 8)}</strong>?<br />
            This action cannot be undone.
          </p>
        )}
      </Modal>
    </aside>
  );
}
