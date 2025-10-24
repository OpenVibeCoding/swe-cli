// Tool call information
export interface ToolCallInfo {
  id: string;
  name: string;
  parameters: Record<string, any>;
  result?: string | null;
  error?: string | null;
  approved?: boolean | null;
}

// Message types
export interface Message {
  role: 'user' | 'assistant' | 'system' | 'tool_call' | 'tool_result';
  content: string;
  timestamp?: string;
  tool_name?: string;
  tool_args?: Record<string, any>;
  tool_result?: any;
  tool_calls?: ToolCallInfo[];
}

// Session types
export interface Session {
  id: string;
  working_dir: string;  // Backend returns this key even though model has working_directory
  created_at: string;
  updated_at: string;
  message_count: number;
  token_usage: Record<string, number>;
}

// Configuration types
export interface Config {
  model_provider: string;
  model: string;
  api_key: string | null;
  temperature: number;
  max_tokens: number;
  enable_bash: boolean;
  working_directory: string;
}

// Provider types
export interface Model {
  id: string;
  name: string;
  description: string;
}

export interface Provider {
  id: string;
  name: string;
  description: string;
  models: Model[];
}

// WebSocket event types
export interface WSMessage {
  type: 'user_message' | 'message_start' | 'message_chunk' | 'message_complete' | 'tool_call' | 'tool_result' | 'approval_required' | 'approval_resolved' | 'error' | 'pong' | 'mcp_status_update' | 'mcp_servers_update';
  data: any;
}

export interface ToolCall {
  id: string;
  name: string;
  arguments: Record<string, any>;
  requiresApproval: boolean;
}

export interface ApprovalRequest {
  id: string;
  tool_name: string;
  arguments: Record<string, any>;
  description: string;
  preview?: string;
}
