import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { useChatStore } from '../../stores/chat';
import { ToolCallMessage } from './ToolCallMessage';

export function MessageList() {
  const messages = useChatStore(state => state.messages);
  const isLoading = useChatStore(state => state.isLoading);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full px-6">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-gray-100 flex items-center justify-center">
            <svg className="w-8 h-8 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Welcome to SWE-CLI</h2>
          <p className="text-sm text-gray-600">Start a conversation with your AI coding assistant</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto px-6 py-8">
      <div className="max-w-4.5xl mx-auto space-y-6">
        {messages.map((message, index) => {
          // Render tool calls and tool results with special component
          if (message.role === 'tool_call' || message.role === 'tool_result') {
            return <ToolCallMessage key={index} message={message} />;
          }

          // Render regular messages
          return (
            <div
              key={index}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'} animate-slide-up`}
            >
              <div className={`max-w-3xl ${message.role === 'user' ? 'ml-12' : 'mr-12'}`}>
                <div
                  className={`rounded-lg px-4 py-3 ${
                    message.role === 'user'
                      ? 'bg-primary-50 border border-primary-100'
                      : 'bg-white border border-gray-200 shadow-sm'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium mt-0.5 bg-gray-100 text-gray-700">
                      {message.role === 'user' ? 'You' : 'AI'}
                    </div>
                    <div className="flex-1 prose prose-sm max-w-none">
                      <ReactMarkdown
                        components={{
                          code({ node, inline, className, children, ...props }) {
                            return inline ? (
                              <code {...props}>
                                {children}
                              </code>
                            ) : (
                              <pre>
                                <code className={className} {...props}>
                                  {children}
                                </code>
                              </pre>
                            );
                          },
                          p({ children }) {
                            return <p className="text-gray-900 leading-relaxed">{children}</p>;
                          },
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        {isLoading && (
          <div className="flex justify-start animate-fade-in">
            <div className="max-w-3xl mr-12">
              <div className="rounded-lg px-4 py-3 bg-white border border-gray-200 shadow-sm">
                <div className="flex items-center gap-3">
                  <div className="w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium bg-gray-100 text-gray-700">
                    AI
                  </div>
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
