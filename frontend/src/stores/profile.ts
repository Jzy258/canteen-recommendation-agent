import { defineStore } from 'pinia'
import type { UserProfile } from '@/types/chat'

const DEFAULT_PROFILE: UserProfile = {
  budget: 20,
  flavor_preferences: '',
  health_goals: '',
  region: '',
}

/**
 * 用户偏好与设置（预算 / 口味 / 健康目标 / 所在地区）。
 * 持久化到 localStorage（key: canteen.profile），并派生注入对话的话术前缀。
 */
export const useProfileStore = defineStore('profile', {
  state: () => ({
    budget: DEFAULT_PROFILE.budget,
    flavor_preferences: '',
    health_goals: '',
    region: '',
    /** 用户是否显式保存过偏好；未保存不注入对话（企业级语义） */
    configured: false,
  }),
  getters: {
    profile: (s): UserProfile => ({
      budget: s.budget,
      flavor_preferences: s.flavor_preferences,
      health_goals: s.health_goals,
      region: s.region,
    }),
    /** 以自然语言注入对话的前缀，如"（用户偏好：预算20元，所在城市北京）" */
    injectedPrompt: (s) => {
      if (!s.configured) return ''
      const parts: string[] = []
      if (s.budget > 0) parts.push(`预算${s.budget}元`)
      if (s.flavor_preferences.trim()) parts.push(`口味偏好${s.flavor_preferences.trim()}`)
      if (s.health_goals) parts.push(`目标${s.health_goals}`)
      if (s.region.trim()) parts.push(`所在城市${s.region.trim()}`)
      return parts.length ? `（用户偏好：${parts.join('，')}）` : ''
    },
  },
  actions: {
    save(p: UserProfile) {
      this.budget = p.budget
      this.flavor_preferences = p.flavor_preferences
      this.health_goals = p.health_goals
      this.region = p.region || ''
      this.configured = true
    },
    reset() {
      this.budget = DEFAULT_PROFILE.budget
      this.flavor_preferences = ''
      this.health_goals = ''
      this.region = ''
      this.configured = false
    },
  },
  persist: {
    key: 'canteen.profile',
  },
})
