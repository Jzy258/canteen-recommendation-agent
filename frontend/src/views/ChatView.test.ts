import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import ChatView from './ChatView.vue'

vi.mock('@/api/chat', () => ({
  chat: vi.fn(),
}))

import { chat } from '@/api/chat'

const mockedChat = vi.mocked(chat)

function mountView() {
  return mount(ChatView, {
    global: { plugins: [ElementPlus] },
  })
}

describe('ChatView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('空输入不发起请求并提示', async () => {
    const wrapper = mountView()
    await wrapper.find('textarea').setValue('   ')
    await wrapper.find('button.el-button--primary').trigger('click')
    await flushPromises()

    expect(mockedChat).not.toHaveBeenCalled()
  })

  it('发送后展示用户消息并渲染回复', async () => {
    mockedChat.mockResolvedValue({
      reply: '今日推荐：清炒小白菜（4元）',
      session_id: 's-abc',
    })

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('推荐清淡的菜')
    await wrapper.find('button.el-button--primary').trigger('click')
    await flushPromises()

    expect(mockedChat).toHaveBeenCalledWith({
      message: '推荐清淡的菜',
      session_id: undefined,
    })
    const bubbles = wrapper.findAll('.chat-bubble')
    expect(bubbles[0].text()).toContain('推荐清淡的菜')
    expect(bubbles[1].text()).toContain('清炒小白菜')
  })

  it('持久化 session_id 并在下一轮传入', async () => {
    mockedChat.mockResolvedValueOnce({
      reply: '第一轮',
      session_id: 's-first',
    })

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('你好')
    await wrapper.find('button.el-button--primary').trigger('click')
    await flushPromises()

    expect(localStorage.getItem('canteen.session_id')).toBe('s-first')

    mockedChat.mockResolvedValue({
      reply: '第二轮',
      session_id: 's-first',
    })
    await wrapper.find('textarea').setValue('继续')
    await wrapper.find('button.el-button--primary').trigger('click')
    await flushPromises()

    expect(mockedChat).toHaveBeenLastCalledWith({
      message: '继续',
      session_id: 's-first',
    })
  })

  it('后端异常时给出友好回复', async () => {
    mockedChat.mockRejectedValue(new Error('network down'))

    const wrapper = mountView()
    await wrapper.find('textarea').setValue('hi')
    await wrapper.find('button.el-button--primary').trigger('click')
    await flushPromises()

    const bubbles = wrapper.findAll('.chat-bubble')
    expect(bubbles[bubbles.length - 1].text()).toContain('抱歉，系统处理出错')
  })

  it('新会话清空消息与 session', async () => {
    mockedChat.mockResolvedValue({ reply: 'ok', session_id: 's-x' })
    const wrapper = mountView()
    await wrapper.find('textarea').setValue('hi')
    await wrapper.find('button.el-button--primary').trigger('click')
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const newBtn = buttons.find((b) => b.text().includes('新会话'))
    expect(newBtn).toBeTruthy()
    await newBtn!.trigger('click')

    expect(wrapper.findAll('.chat-bubble')).toHaveLength(0)
    expect(localStorage.getItem('canteen.session_id')).toBeNull()
  })
})
