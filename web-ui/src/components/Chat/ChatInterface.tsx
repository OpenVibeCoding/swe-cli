import { useEffect, useState } from 'react';
import { useChatStore } from '../../stores/chat';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';
import { apiClient } from '../../api/client';
import { ComputerDesktopIcon, ChatBubbleLeftRightIcon, InformationCircleIcon } from '@heroicons/react/24/outline';

interface Config {
  model_provider: string;
  model: string;
  temperature?: number;
  max_tokens?: number;
}

export function ChatInterface() {
  const error = useChatStore(state => state.error);
  const currentSessionId = useChatStore(state => state.currentSessionId);
  const hasActiveSession = !!currentSessionId;
  const [config, setConfig] = useState<Config | null>(null);

  useEffect(() => {
    const initializeApp = async () => {
      // Don't check for current session or auto-load messages
      // Let user explicitly select a session from the sidebar first
    };

    initializeApp();
    loadConfig();

    // Listen for config updates
    const handleConfigUpdate = (event: CustomEvent) => {
      setConfig(event.detail);
    };

    window.addEventListener('config-updated', handleConfigUpdate as EventListener);

    return () => {
      window.removeEventListener('config-updated', handleConfigUpdate as EventListener);
    };
  }, []);

  const loadConfig = async () => {
    try {
      const configData = await apiClient.getConfig();
      setConfig(configData);
    } catch (error) {
      console.error('Failed to load config:', error);
    }
  };

  return (
    <div className="flex flex-col h-full relative">
      {/* Model Info Header */}
      {config && (
        <div className="border-b border-gray-200 bg-gradient-to-r from-gray-50 to-white px-6 py-3">
          <div className="flex items-center gap-3">
            <div className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-sm">
              <ComputerDesktopIcon className="w-3.5 h-3.5 text-white" />
            </div>
            <div className="flex items-center gap-2 text-sm">
              <span className="font-semibold text-gray-900 capitalize">
                {config.model_provider}
              </span>
              <span className="text-gray-400">/</span>
              <span className="text-gray-600 font-mono text-xs">
                {config.model}
              </span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 mx-6 mt-4 rounded-lg">
          <strong className="font-semibold">Error:</strong> {error}
        </div>
      )}

      <MessageList />
      <InputBox />

      {/* Session Required Overlay */}
      {!hasActiveSession && (
        <div className="absolute inset-0 bg-white/95 backdrop-blur-sm flex items-center justify-center z-40">
          <div className="text-center max-w-md px-6">
            <div className="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center shadow-xl">
              <ChatBubbleLeftRightIcon className="w-10 h-10 text-white" />
            </div>
            <h2 className="text-2xl font-bold text-gray-900 mb-3">
              No Session Selected
            </h2>
            <p className="text-gray-600 mb-6 leading-relaxed">
              To start chatting, please select an existing session from the sidebar or create a new workspace.
            </p>
            <div className="flex items-center justify-center gap-2 text-sm text-gray-500">
              <InformationCircleIcon className="w-4 h-4" />
              <span>Click a session or "New Workspace" to get started</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
