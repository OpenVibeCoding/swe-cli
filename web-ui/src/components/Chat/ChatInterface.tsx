import { useEffect } from 'react';
import { useChatStore } from '../../stores/chat';
import { MessageList } from './MessageList';
import { InputBox } from './InputBox';

export function ChatInterface() {
  const loadMessages = useChatStore(state => state.loadMessages);
  const error = useChatStore(state => state.error);

  useEffect(() => {
    loadMessages();
  }, [loadMessages]);

  return (
    <div className="flex flex-col h-full">
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 px-4 py-3 mx-6 mt-4 rounded-lg">
          <strong className="font-semibold">Error:</strong> {error}
        </div>
      )}

      <MessageList />
      <InputBox />
    </div>
  );
}
