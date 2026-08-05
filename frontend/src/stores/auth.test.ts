import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from './auth'

vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  register: vi.fn(),
  fetchMe: vi.fn(),
}))

import { login, fetchMe } from '@/api/auth'

const mockedLogin = vi.mocked(login)
const mockedFetchMe = vi.mocked(fetchMe)

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('登录成功后保存 token 与用户信息', async () => {
    mockedLogin.mockResolvedValue({
      access_token: 'token123',
      token_type: 'bearer',
      user: { id: 1, username: 'alice', role: 'user', display_name: '' },
    })
    const store = useAuthStore()
    await store.login('alice', 'secret123')

    expect(store.token).toBe('token123')
    expect(store.user?.username).toBe('alice')
    expect(store.isLoggedIn).toBe(true)
  })

  it('isAdmin 判定', () => {
    const store = useAuthStore()
    store.setAuth('t', { id: 2, username: 'root', role: 'admin', display_name: '管理员' })
    expect(store.isAdmin).toBe(true)
    expect(store.displayName).toBe('管理员')
  })

  it('loadMe 失败时自动登出', async () => {
    mockedFetchMe.mockRejectedValue(new Error('401'))
    const store = useAuthStore()
    store.setAuth('expired', { id: 1, username: 'a', role: 'user', display_name: '' })
    await store.loadMe()
    expect(store.isLoggedIn).toBe(false)
  })

  it('logout 清空状态', () => {
    const store = useAuthStore()
    store.setAuth('t', { id: 1, username: 'a', role: 'user', display_name: '' })
    store.logout()
    expect(store.isLoggedIn).toBe(false)
    expect(store.token).toBe('')
  })
})
