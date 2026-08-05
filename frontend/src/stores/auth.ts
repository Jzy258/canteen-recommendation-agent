import { defineStore } from 'pinia'
import { login as apiLogin, register as apiRegister, fetchMe } from '@/api/auth'
import type { UserInfo } from '@/api/auth'

interface AuthState {
  token: string
  user: UserInfo | null
}

/**
 * 用户认证状态（v1.1.0）
 * 持久化到 localStorage（key: canteen.auth），含 token 与用户信息。
 */
export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: '',
    user: null,
  }),
  getters: {
    isLoggedIn: (s) => !!s.token && !!s.user,
    isAdmin: (s) => s.user?.role === 'admin',
    displayName: (s) => s.user?.display_name || s.user?.username || '',
  },
  actions: {
    setAuth(token: string, user: UserInfo) {
      this.token = token
      this.user = user
    },
    async login(username: string, password: string) {
      const res = await apiLogin(username, password)
      this.setAuth(res.access_token, res.user)
    },
    async register(username: string, password: string, displayName = '') {
      const user = await apiRegister(username, password, displayName)
      // 注册接口不返回 token，注册后引导用户登录
      this.user = user
    },
    async loadMe() {
      if (!this.token) return
      try {
        this.user = await fetchMe()
      } catch {
        this.logout()
      }
    },
    logout() {
      this.token = ''
      this.user = null
    },
  },
  persist: {
    key: 'canteen.auth',
  },
})
