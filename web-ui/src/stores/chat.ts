import { create } from 'zustand';
import type { Message, ApprovalRequest } from '../types';
import { apiClient } from '../api/client';
import { wsClient } from '../api/websocket';

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  isConnected: boolean;
  pendingApproval: ApprovalRequest | null;
  currentSessionId: string | null;
  hasWorkspace: boolean;

  // Actions
  loadMessages: () => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  clearChat: () => Promise<void>;
  addMessage: (message: Message) => void;
  setConnected: (connected: boolean) => void;
  setPendingApproval: (approval: ApprovalRequest | null) => void;
  respondToApproval: (approvalId: string, approved: boolean) => void;
  setHasWorkspace: (hasWorkspace: boolean) => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isLoading: false,
  error: null,
  isConnected: false,
  pendingApproval: null,
  currentSessionId: null,
  hasWorkspace: false,

  loadMessages: async () => {
    set({ isLoading: true, error: null });
    try {
      const messages = await apiClient.getMessages();
      set({ messages, isLoading: false });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to load messages',
        isLoading: false
      });
    }
  },

  loadSession: async (sessionId: string) => {
    console.log(`[Frontend] Loading session ${sessionId}`);
    set({ isLoading: true, error: null });
    try {
      // Resume the session first
      console.log(`[Frontend] Resuming session ${sessionId}`);
      await apiClient.resumeSession(sessionId);
      console.log(`[Frontend] Session resumed successfully`);

      // Then load its messages
      console.log(`[Frontend] Fetching messages...`);
      const rawMessages = await apiClient.getMessages();
      console.log(`[Frontend] Received ${rawMessages.length} raw messages:`, rawMessages);

      // Expand tool_calls into separate messages
      const expandedMessages: Message[] = [];
      for (const msg of rawMessages) {
        // If message has tool calls, expand them
        if (msg.tool_calls && msg.tool_calls.length > 0) {
          // Add main message only if it has meaningful content
          if (msg.content && msg.content.trim()) {
            expandedMessages.push({
              role: msg.role as any,
              content: msg.content,
              timestamp: msg.timestamp,
            });
          }

          // Add each tool call and its result
          for (const tc of msg.tool_calls) {
            // Add tool call message
            expandedMessages.push({
              role: 'tool_call',
              content: `Calling ${tc.name}`,
              tool_name: tc.name,
              tool_args: tc.parameters,
              timestamp: msg.timestamp,
            });

            // Add tool result message
            expandedMessages.push({
              role: 'tool_result',
              content: tc.error ? 'Failed' : 'Success',
              tool_name: tc.name,
              tool_result: tc.error || tc.result || '',
              timestamp: msg.timestamp,
            });
          }
        } else {
          // No tool calls, add the message normally (but skip if empty)
          if (msg.content && msg.content.trim()) {
            expandedMessages.push({
              role: msg.role as any,
              content: msg.content,
              timestamp: msg.timestamp,
            });
          }
        }
      }

      console.log(`[Frontend] Expanded to ${expandedMessages.length} messages`);
      set({
        messages: expandedMessages,
        isLoading: false,
        currentSessionId: sessionId,
        hasWorkspace: true,
      });
      console.log(`[Frontend] Session ${sessionId} loaded successfully`);
    } catch (error) {
      console.error(`[Frontend] Failed to load session:`, error);
      set({
        error: error instanceof Error ? error.message : 'Failed to load session',
        isLoading: false
      });
    }
  },

  sendMessage: async (content: string) => {
    // Optimistically add user message
    const userMessage: Message = {
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };

    set(state => ({
      messages: [...state.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      // Send via WebSocket for real-time updates
      wsClient.send({
        type: 'query',
        data: { message: content },
      });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to send message',
        isLoading: false
      });
    }
  },

  clearChat: async () => {
    try {
      await apiClient.clearChat();
      set({ messages: [], error: null });
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : 'Failed to clear chat'
      });
    }
  },

  addMessage: (message: Message) => {
    set(state => ({
      messages: [...state.messages, message],
    }));
  },

  setConnected: (connected: boolean) => {
    set({ isConnected: connected });
  },

  setPendingApproval: (approval: ApprovalRequest | null) => {
    set({ pendingApproval: approval });
  },

  respondToApproval: (approvalId: string, approved: boolean) => {
    // Send approval response via WebSocket
    wsClient.send({
      type: 'approve',
      data: {
        approvalId,
        approved,
      },
    });
    // Clear pending approval
    set({ pendingApproval: null });
  },

  setHasWorkspace: (hasWorkspace: boolean) => {
    set({ hasWorkspace });
  },
}));

// Setup WebSocket listeners
wsClient.on('connected', () => {
  useChatStore.getState().setConnected(true);
});

wsClient.on('disconnected', () => {
  useChatStore.getState().setConnected(false);
});

wsClient.on('user_message', (message) => {
  // Message already added optimistically
});

wsClient.on('message_start', () => {
  useChatStore.setState({ isLoading: true });
});

wsClient.on('message_chunk', (message) => {
  const { messages } = useChatStore.getState();
  const lastMessage = messages[messages.length - 1];

  if (lastMessage && lastMessage.role === 'assistant') {
    // Append to existing assistant message
    useChatStore.setState({
      messages: [
        ...messages.slice(0, -1),
        {
          ...lastMessage,
          content: lastMessage.content + message.data.content,
        },
      ],
    });
  } else {
    // Create new assistant message
    useChatStore.getState().addMessage({
      role: 'assistant',
      content: message.data.content,
    });
  }
});

wsClient.on('message_complete', () => {
  useChatStore.setState({ isLoading: false });
});

wsClient.on('error', (message) => {
  useChatStore.setState({
    error: message.data.message,
    isLoading: false,
  });
});

wsClient.on('approval_required', (message) => {
  useChatStore.getState().setPendingApproval(message.data as ApprovalRequest);
});

wsClient.on('approval_resolved', () => {
  // Clear pending approval when resolved
  useChatStore.getState().setPendingApproval(null);
});

wsClient.on('tool_call', (message) => {
  // Add tool call message
  const toolCallMessage: Message = {
    role: 'tool_call',
    content: message.data.description || `Calling ${message.data.tool_name}`,
    tool_name: message.data.tool_name,
    tool_args: message.data.arguments,
    timestamp: new Date().toISOString(),
  };
  useChatStore.getState().addMessage(toolCallMessage);
});

wsClient.on('tool_result', (message) => {
  // Add tool result message
  const toolResultMessage: Message = {
    role: 'tool_result',
    content: message.data.result || 'Tool completed',
    tool_name: message.data.tool_name,
    tool_result: message.data.output,
    timestamp: new Date().toISOString(),
  };
  useChatStore.getState().addMessage(toolResultMessage);
});
