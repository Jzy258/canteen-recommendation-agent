import { http } from './client'
import type { ChatRequest, ChatResponse, StreamEvent } from '@/types/chat'

export interface ChatSessionItem {
  session_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export async function chat(req: ChatRequest): Promise<ChatResponse> {
  const { data } = await http.post<ChatResponse>('/chat', req)
  return data
}

export async function listSessions(limit = 50): Promise<ChatSessionItem[]> {
  const { data } = await http.get<ChatSessionItem[]>('/sessions', {
    params: { limit },
  })
  return data
}

export async function getSessionMessages(sessionId: string): Promise<ChatHistoryMessage[]> {
  const { data } = await http.get<ChatHistoryMessage[]>(`/sessions/${sessionId}/messages`)
  return data
}

export async function deleteSession(sessionId: string): Promise<void> {
  await http.delete(`/sessions/${sessionId}`)
}

export async function chatStream(
  req: ChatRequest,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${http.defaults.baseURL}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
    signal,
  })

  if (!res.ok || !res.body) {
    throw new Error(`stream request failed: ${res.status}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n\n')
    buffer = lines.pop() ?? ''

    for (const block of lines) {
      const line = block.trim()
      if (!line.startsWith('data:')) continue
      const payload = line.slice(5).trim()
      if (!payload) continue
      try {
        onEvent(JSON.parse(payload) as StreamEvent)
      } catch {
        // ignore malformed frame
      }
    }
  }
}
