import { describe, it, expect, vi, beforeEach } from 'vitest'
import { chat, chatStream } from './chat'
import type { StreamEvent } from '@/types/chat'

vi.mock('@/api/client', () => ({
  http: {
    defaults: { baseURL: 'http://test.local' },
    post: vi.fn(),
  },
}))

import { http } from '@/api/client'

const mockedPost = vi.mocked(http.post)

describe('chat api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('chat 调用 /chat 并返回 reply 与 session_id', async () => {
    mockedPost.mockResolvedValue({
      data: { reply: '今日推荐：红烧肉', session_id: 's-1' },
    })

    const res = await chat({ message: '有什么菜？' })

    expect(mockedPost).toHaveBeenCalledWith('/chat', { message: '有什么菜？' })
    expect(res.reply).toContain('红烧肉')
    expect(res.session_id).toBe('s-1')
  })

  it('chat 透传 session_id', async () => {
    mockedPost.mockResolvedValue({
      data: { reply: 'ok', session_id: 's-2' },
    })

    await chat({ message: 'hi', session_id: 's-2' })

    expect(mockedPost).toHaveBeenCalledWith('/chat', {
      message: 'hi',
      session_id: 's-2',
    })
  })
})

describe('chatStream SSE 解析', () => {
  it('解析 session / delta / done 事件', async () => {
    const frames = [
      'data: {"type":"session","session_id":"s-3"}\n\n',
      'data: {"type":"delta","content":"你"}\n\n',
      'data: {"type":"delta","content":"好"}\n\n',
      'data: {"type":"done"}\n\n',
    ]
    const encoder = new TextEncoder()
    const stream = new ReadableStream({
      start(controller) {
        for (const f of frames) controller.enqueue(encoder.encode(f))
        controller.close()
      },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: true, body: stream }))

    const events: StreamEvent[] = []
    await chatStream({ message: 'hi' }, (e) => events.push(e))

    expect(events).toHaveLength(4)
    expect(events[0]).toEqual({ type: 'session', session_id: 's-3' })
    expect(events[1]).toEqual({ type: 'delta', content: '你' })
    expect(events[3]).toEqual({ type: 'done' })
    vi.unstubAllGlobals()
  })
})
