import { useState, KeyboardEvent } from 'react';
import { useChatStore } from '../../stores/chat';

export function InputBox() {
  const [input, setInput] = useState('');
  const sendMessage = useChatStore(state => state.sendMessage);
  const isLoading = useChatStore(state => state.isLoading);
  const isConnected = useChatStore(state => state.isConnected);

  const handleSend = () => {
    if (!input.trim() || isLoading || !isConnected) return;

    sendMessage(input.trim());
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
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
            placeholder={isConnected ? "Type your message..." : "Disconnected..."}
            disabled={!isConnected || isLoading}
            className="flex-1 bg-white text-gray-900 rounded-lg px-4 py-3 resize-none border border-gray-200 focus:border-primary-500 focus:ring-2 focus:ring-primary-100 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-50 transition-colors"
            rows={2}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isLoading || !isConnected}
            className="px-5 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-500 transition-all font-medium h-auto self-end"
          >
            {isLoading ? (
              <span className="flex items-center gap-2">
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
              </span>
            ) : (
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            )}
          </button>
        </div>
        <div className="mt-2 text-xs text-gray-500 px-1">
          Press <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-xs">Enter</kbd> to send · <kbd className="px-1.5 py-0.5 bg-gray-100 border border-gray-200 rounded text-xs">Shift + Enter</kbd> for new line
        </div>
      </div>
    </div>
  );
}
