import type { Message, Session, Config, Provider } from '../types';

const API_BASE = '/api';

class APIClient {
  // Chat endpoints
  async sendQuery(message: string, sessionId?: string): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/chat/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, sessionId }),
    });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async getMessages(): Promise<Message[]> {
    const response = await fetch(`${API_BASE}/chat/messages`);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async clearChat(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/chat/clear`, {
      method: 'DELETE',
    });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async interruptTask(): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/chat/interrupt`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  // Session endpoints
  async listSessions(): Promise<Session[]> {
    const response = await fetch(`${API_BASE}/sessions`);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async getCurrentSession(): Promise<Session> {
    const response = await fetch(`${API_BASE}/sessions/current`);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async resumeSession(sessionId: string): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/resume`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async exportSession(sessionId: string): Promise<any> {
    const response = await fetch(`${API_BASE}/sessions/${sessionId}/export`);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async verifyPath(path: string): Promise<{ exists: boolean; is_directory: boolean; path?: string; error?: string }> {
    const response = await fetch(`${API_BASE}/sessions/verify-path`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ path }),
    });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async createSession(workspace: string): Promise<{ status: string; message: string; session: any }> {
    const response = await fetch(`${API_BASE}/sessions/create`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workspace }),
    });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  // Config endpoints
  async getConfig(): Promise<any> {
    const response = await fetch(`${API_BASE}/config`);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async updateConfig(config: any): Promise<{ status: string; message: string }> {
    const response = await fetch(`${API_BASE}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config),
    });
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  async listProviders(): Promise<any[]> {
    const response = await fetch(`${API_BASE}/config/providers`);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  // File listing
  async listFiles(query?: string): Promise<{ files: Array<{ path: string; name: string; is_file: boolean }> }> {
    const url = query ? `${API_BASE}/sessions/files?query=${encodeURIComponent(query)}` : `${API_BASE}/sessions/files`;
    const response = await fetch(url);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }

  // Health check
  async health(): Promise<{ status: string; service: string }> {
    const response = await fetch(`${API_BASE}/health`);
    if (!response.ok) throw new Error(`API error: ${response.statusText}`);
    return response.json();
  }
}

export const apiClient = new APIClient();
