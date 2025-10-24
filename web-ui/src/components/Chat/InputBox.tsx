import { useState, KeyboardEvent } from 'react';
import { useChatStore } from '../../stores/chat';
import { apiClient } from '../../api/client';

export function InputBox() {
  const [input, setInput] = useState('');
  const sendMessage = useChatStore(state => state.sendMessage);
  const isLoading = useChatStore(state => state.isLoading);
  const isConnected = useChatStore(state => state.isConnected);
  const currentSessionId = useChatStore(state => state.currentSessionId);
  const hasActiveSession = !!currentSessionId;

  const handleSend = () => {
    if (!input.trim() || isLoading || !isConnected || !hasActiveSession) return;

    sendMessage(input.trim());
    setInput('');
  };

  const handleStop = async () => {
    try {
      await apiClient.interruptTask();
    } catch (error) {
      console.error('Failed to interrupt task:', error);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    } else if (e.key === 'Escape' && isLoading) {
      e.preventDefault();
      handleStop();
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="max-w-4.5xl mx-auto">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              !hasActiveSession
                ? "Select a session to start chatting..."
                : !isConnected
                ? "Disconnected..."
                : "Type your message..."
            }
            disabled={!isConnected || isLoading || !hasActiveSession}
            className="flex-1 bg-white text-gray-900 rounded-lg px-4 py-3 resize-none border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50 transition-colors"
            rows={2}
          />
          <button
            onClick={isLoading ? handleStop : handleSend}
            disabled={!isLoading && (!input.trim() || !isConnected || !hasActiveSession)}
            className={`px-6 py-3 rounded-xl transition-all font-medium shadow-md hover:shadow-lg transform hover:scale-105 active:scale-95 ${
              isLoading
                ? 'bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 text-white'
                : 'bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100 disabled:shadow-none disabled:from-gray-300 disabled:to-gray-400'
            }`}
            title={isLoading ? 'Stop (Esc)' : 'Send (Enter)'}
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <rect x="6" y="6" width="12" height="12" rx="1" />
                </svg>
              </span>
            ) : (
              <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
              </svg>
            )}
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500 px-1">
          Press <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-xs">Enter</kbd> to send · <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-xs">Shift + Enter</kbd> for new line · <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-xs">Esc</kbd> to stop
        </div>
      </div>
    </div>
  );
}
