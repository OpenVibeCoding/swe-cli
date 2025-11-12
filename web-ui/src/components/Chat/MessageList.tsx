import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useChatStore } from '../../stores/chat';
import { ToolCallMessage } from './ToolCallMessage';
import { SPINNER_FRAMES, THINKING_VERBS, SPINNER_COLORS } from '../../constants/spinner';

export function MessageList() {
  const messages = useChatStore(state => state.messages);
  const isLoading = useChatStore(state => state.isLoading);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Spinner animation state
  const [spinnerIndex, setSpinnerIndex] = useState(0);
  const [verbIndex, setVerbIndex] = useState(0);
  const [colorIndex, setColorIndex] = useState(0);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Animate spinner when loading
  useEffect(() => {
    if (!isLoading) return;

    const spinnerInterval = setInterval(() => {
      setSpinnerIndex(prev => (prev + 1) % SPINNER_FRAMES.length);
      setColorIndex(prev => (prev + 1) % SPINNER_COLORS.length);
    }, 100); // Match terminal speed: 100ms

    const verbInterval = setInterval(() => {
      setVerbIndex(prev => (prev + 1) % THINKING_VERBS.length);
    }, 2000); // Change verb every 2 seconds

    return () => {
      clearInterval(spinnerInterval);
      clearInterval(verbInterval);
    };
  }, [isLoading]);

  // Custom Page Up/Page Down handling with shorter scroll distance
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!scrollContainerRef.current) return;

      const scrollDistance = 300; // Shorter scroll distance (default is ~viewport height)

      if (e.key === 'PageUp') {
        e.preventDefault();
        scrollContainerRef.current.scrollBy({
          top: -scrollDistance,
          behavior: 'smooth'
        });
      } else if (e.key === 'PageDown') {
        e.preventDefault();
        scrollContainerRef.current.scrollBy({
          top: scrollDistance,
          behavior: 'smooth'
        });
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  if (messages.length === 0) {
    return (
      <div className="flex items-center justify-center h-full px-6 bg-cream">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-6 rounded-full bg-beige-200 flex items-center justify-center">
            <svg className="w-8 h-8 text-beige-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
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
    <div ref={scrollContainerRef} className="flex-1 overflow-y-auto bg-gray-50">
      <div className="max-w-4xl mx-auto py-6 px-6 space-y-3">
        {messages.map((message, index) => {
          // Render tool calls and tool results with special component
          if (message.role === 'tool_call' || message.role === 'tool_result') {
            return <ToolCallMessage key={index} message={message} />;
          }

          // ChatGPT-style message bubbles
          const isUser = message.role === 'user';

          return (
            <div key={index} className={`${isUser ? '' : 'ml-6'} animate-slide-up mb-2`}>
              {isUser ? (
                <div className="font-mono text-sm bg-gray-850 rounded px-4 py-3 border border-gray-700 shadow-md">
                  <div className="flex items-start">
                    <span className="text-cyan-400 font-bold mr-2">#</span>
                    <span className="text-green-400 flex-1">{message.content}</span>
                  </div>
                </div>
              ) : (
                <div className="text-gray-100 leading-relaxed">
                  {/* Terminal response prefix */}
                  <div className="flex items-start mb-2">
                    <span className="text-yellow-400 font-mono mr-2">❯</span>
                    <span className="text-gray-500 text-xs font-mono">
                      {message.timestamp ?
                        new Date(message.timestamp).toLocaleTimeString() :
                        new Date().toLocaleTimeString()
                      }
                    </span>
                  </div>
                  <div className="prose prose-sm max-w-none prose-invert">
                  <ReactMarkdown
                    components={{
                      code({ node, className, children, ...props }) {
                        const isInline = (props as any)?.inline;
                        const languageMatch = /language-(\w+)/.exec(className || '');
                        const language = languageMatch ? languageMatch[1] : null;
                        return isInline ? (
                          <code className="text-sm px-1.5 py-0.5 rounded font-mono bg-gray-800 text-gray-100" {...props}>
                            {children}
                          </code>
                        ) : (
                          <pre className="rounded-lg p-3 overflow-x-auto my-2 bg-gray-900 border border-gray-700">
                            <code className={className} data-language={language} {...props}>
                              {children}
                            </code>
                          </pre>
                        );
                      },
                      p({ children }) {
                        return <p className="leading-relaxed mb-2 last:mb-0 text-gray-300">{children}</p>;
                      },
                      ul({ children }) {
                        return <ul className="list-disc pl-5 space-y-1 mb-2 text-gray-300">{children}</ul>;
                      },
                      ol({ children }) {
                        return <ol className="list-decimal pl-5 space-y-1 mb-2 text-gray-300">{children}</ol>;
                      },
                      li({ children }) {
                        return <li className="text-gray-300">{children}</li>;
                      },
                      strong({ children }) {
                        return <strong className="font-semibold text-white">{children}</strong>;
                      },
                      a({ children, href }) {
                        return <a href={href} className="underline text-blue-400" target="_blank" rel="noopener noreferrer">{children}</a>;
                      },
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {isLoading && (
          <div className="flex justify-start px-6 animate-fade-in">
            <div className="max-w-[85%] px-5 py-3">
              <div className="flex items-center gap-3">
                {/* Braille dots spinner matching terminal style */}
                <span className={`text-lg font-medium ${SPINNER_COLORS[colorIndex]} transition-colors duration-100`}>
                  {SPINNER_FRAMES[spinnerIndex]}
                </span>
                <span className="text-sm text-gray-600 font-medium">
                  {THINKING_VERBS[verbIndex]}...
                </span>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}
