import { useState, useEffect } from 'react';
import { FolderIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import { useChatStore, Session } from '../../stores/chat';
import { NewSessionModal } from './NewSessionModal';
import { DeleteConfirmModal } from './DeleteConfirmModal';
import { apiClient } from '../../api/client';

export function SessionsSidebar() {
  const { sessions, fetchSessions, setCurrentSessionId, currentSessionId } = useChatStore();
  const [isNewSessionModalOpen, setNewSessionModalOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<Session | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  const handleCreateSession = async (name: string) => {
    try {
      const newSession = await apiClient.createSession({ working_dir: name });
      if (newSession) {
        await fetchSessions();
        setCurrentSessionId(newSession.id);
        setNewSessionModalOpen(false);
        setError(null);
      }
    } catch (err) {
      setError('Failed to create session. Please try again.');
      console.error(err);
    }
  };

  const handleDeleteSession = async () => {
    if (sessionToDelete) {
      try {
        await apiClient.deleteSession(sessionToDelete.id);
        await fetchSessions();
        if (currentSessionId === sessionToDelete.id) {
          setCurrentSessionId(null);
        }
        setSessionToDelete(null);
        setError(null);
      } catch (err) {
        setError('Failed to delete session. Please try again.');
        console.error(err);
      }
    }
  };

  const handleSessionClick = (sessionId: string) => {
    setCurrentSessionId(sessionId);
  };

  return (
    <aside className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Sessions</h2>
        <button
          onClick={() => setNewSessionModalOpen(true)}
          className="mt-2 w-full flex items-center justify-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-lg transition-colors"
        >
          <PlusIcon className="w-5 h-5" />
          New Session
        </button>
      </div>
      <div className="flex-1 overflow-y-auto">
        {error && <p className="p-4 text-sm text-red-600">{error}</p>}
        <ul className="p-2 space-y-1">
          {sessions.map((session) => (
            <li key={session.id}>
              <div
                onClick={() => handleSessionClick(session.id)}
                className={`flex items-center justify-between p-2 rounded-lg cursor-pointer ${
                  currentSessionId === session.id
                    ? 'bg-purple-100 text-purple-900'
                    : 'text-gray-700 hover:bg-gray-100'
                }`}
              >
                <div className="flex items-center gap-2">
                  <FolderIcon className="w-5 h-5" />
                  <span className="font-medium">{session.working_dir}</span>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSessionToDelete(session);
                  }}
                  className="p-1 rounded-full hover:bg-red-100 text-gray-500 hover:text-red-600"
                >
                  <TrashIcon className="w-4 h-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      </div>

      <NewSessionModal
        isOpen={isNewSessionModalOpen}
        onClose={() => setNewSessionModalOpen(false)}
        onCreate={handleCreateSession}
        errorMessage={error ?? undefined}
      />

      {sessionToDelete && (
        <DeleteConfirmModal
          isOpen={!!sessionToDelete}
          onClose={() => setSessionToDelete(null)}
          onConfirm={handleDeleteSession}
          sessionName={sessionToDelete.working_dir}
        />
      )}
    </aside>
  );
}
