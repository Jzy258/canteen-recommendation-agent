import { defineStore } from 'pinia'

const SESSION_KEY = 'canteen.session_id'

/**
 * 会话状态（多会话隔离）。
 * session_id 以纯字符串持久化到 localStorage，与历史格式保持一致。
 */
export const useChatStore = defineStore('chat', {
  state: () => ({
    sessionId: (typeof localStorage !== 'undefined' && localStorage.getItem(SESSION_KEY)) || '',
  }),
  getters: {
    hasSession: (s) => !!s.sessionId,
  },
  actions: {
    setSession(id: string) {
      this.sessionId = id
      localStorage.setItem(SESSION_KEY, id)
    },
    clearSession() {
      this.sessionId = ''
      localStorage.removeItem(SESSION_KEY)
    },
  },
})
