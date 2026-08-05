import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import ChatView from './ChatView.vue'
import type { StreamEvent } from '@/types/chat'

vi.mock('@/api/chat', () => ({
  chat: vi.fn(),
  chatStream: vi.fn(),
}))

import { chat, chatStream } from '@/api/chat'

const mockedChat = vi.mocked(chat)
const mockedStream = vi.mocked(chatStream)

function emitStream(events: StreamEvent[]): void {
  mockedStream.mockImplementation(async (_req, onEvent) => {
    for (const e of events) onEvent(e)
  })
}

function mountView() {
  return mount(ChatView, {
    global: { plugins: [ElementPlus, createPinia()] },
  })
}

/** 精确定位“发送”按钮（避免匹配到“今日吃什么？”等 primary 快捷按钮） */
function findSendBtn(wrapper: ReturnType<typeof mountView>) {
  return wrapper.findAll('button').find((b) => b.text().includes('发送'))!
}

describe('ChatView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('空输入不发起请求并提示', async () => {
    const wrapper = mountView()
    await wrapper.find('textarea').setValue('   ')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    expect(mockedStream).not.toHaveBeenCalled()
    expect(mockedChat).not.toHaveBeenCalled()
  })

  it('流式输出逐字渲染回复', async () => {
    emitStream([
      { type: 'session', session_id: 's-abc' },
      { type: 'delta', content: '今日推荐：' },
      { type: 'delta', content: '清炒小白菜（4元）' },
      { type: 'done' },
    ])

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('推荐清淡的菜')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    expect(mockedStream).toHaveBeenCalledWith(
      { message: '推荐清淡的菜', session_id: undefined },
      expect.any(Function),
      expect.anything(),
    )
    const bubbles = wrapper.findAll('.chat-bubble')
    expect(bubbles[0].text()).toContain('推荐清淡的菜')
    expect(bubbles[1].text()).toBe('今日推荐：清炒小白菜（4元）')
  })

  it('session 事件持久化 session_id', async () => {
    emitStream([{ type: 'session', session_id: 's-first' }, { type: 'done' }])

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('你好')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    expect(localStorage.getItem('canteen.session_id')).toBe('s-first')

    emitStream([{ type: 'session', session_id: 's-first' }, { type: 'done' }])
    await wrapper.find('textarea').setValue('继续')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    expect(mockedStream).toHaveBeenLastCalledWith(
      { message: '继续', session_id: 's-first' },
      expect.any(Function),
      expect.anything(),
    )
  })

  it('流式失败时回退到普通 /chat', async () => {
    mockedStream.mockRejectedValue(new Error('stream down'))
    mockedChat.mockResolvedValue({ reply: '普通模式回复', session_id: 's-2' })

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('hi')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    expect(mockedChat).toHaveBeenCalled()
    const bubbles = wrapper.findAll('.chat-bubble')
    expect(bubbles[bubbles.length - 1].text()).toBe('普通模式回复')
  })

  it('流式与普通均失败时给出友好回复', async () => {
    mockedStream.mockRejectedValue(new Error('stream down'))
    mockedChat.mockRejectedValue(new Error('network down'))

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('hi')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    const bubbles = wrapper.findAll('.chat-bubble')
    expect(bubbles[bubbles.length - 1].text()).toContain('抱歉，系统处理出错')
  })

  it('停止按钮中断流式输出', async () => {
    let captureAbort: ((signal: AbortSignal) => void) | null = null
    mockedStream.mockImplementation((_req, _onEvent, signal) => {
      return new Promise((_resolve, reject) => {
        captureAbort = (sig) => {
          sig.addEventListener('abort', () => {
            const err = new Error('aborted') as Error & { name: string }
            err.name = 'AbortError'
            reject(err)
          })
        }
        captureAbort(signal as AbortSignal)
      })
    })

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('hi')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    const stopBtn = wrapper.findAll('button').find((b) => b.text().includes('停止'))
    expect(stopBtn).toBeTruthy()
    await stopBtn!.trigger('click')
    await flushPromises()

    // 中断后不产生错误兜底气泡
    const bubbles = wrapper.findAll('.chat-bubble')
    expect(bubbles.length).toBeLessThanOrEqual(1)
  })

  it('新会话清空消息与 session', async () => {
    emitStream([{ type: 'session', session_id: 's-x' }, { type: 'done' }])
    const wrapper = mountView()
    await wrapper.find('textarea').setValue('hi')
    await findSendBtn(wrapper).trigger('click')
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const newBtn = buttons.find((b) => b.text().includes('新会话'))
    expect(newBtn).toBeTruthy()
    await newBtn!.trigger('click')

    expect(wrapper.findAll('.chat-bubble')).toHaveLength(0)
    expect(localStorage.getItem('canteen.session_id')).toBeNull()
  })
})
