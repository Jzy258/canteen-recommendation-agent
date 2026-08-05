import { defineStore } from 'pinia'
import type { UserProfile } from '@/types/chat'
import { fetchProfile, saveProfile } from '@/api/profile'

const DEFAULT_PROFILE: UserProfile = {
  budget: 20,
  flavor_preferences: '',
  health_goals: '',
  region: '',
}

/**
 * 用户偏好与设置（预算 / 口味 / 健康目标 / 所在地区）。
 * - 预算/口味/健康目标：**后端按 user_id 数据隔离**（GET/PUT /profile），
 *   登录用户各自独立，游客用无主画像。
 * - region（所在城市）：本地 localStorage（轻量位置信息，不入库）。
 */
export const useProfileStore = defineStore('profile', {
  state: () => ({
    budget: DEFAULT_PROFILE.budget,
    flavor_preferences: '',
    health_goals: '',
    region: '',
    /** 用户是否显式保存过偏好；未保存不注入对话（企业级语义） */
    configured: false,
    /** 是否已从后端加载过 */
    loaded: false,
    /** 加载/保存中 */
    saving: false,
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
    /**
     * 从后端加载当前用户画像（按 user_id 隔离）。
     * 登录态变化时应调用；游客后端返回无主画像。
     */
    async load() {
      try {
        const p = await fetchProfile()
        this.budget = p.budget ?? DEFAULT_PROFILE.budget
        this.flavor_preferences = p.flavor_preferences || ''
        this.health_goals = p.health_goals || ''
        this.configured = true
      } catch {
        // 后端不可用则保留本地默认值
      } finally {
        this.loaded = true
      }
    },
    /** 保存偏好：写入后端（按 user_id 隔离），region 存本地 */
    async save(p: UserProfile) {
      this.budget = p.budget
      this.flavor_preferences = p.flavor_preferences
      this.health_goals = p.health_goals
      this.region = p.region || ''
      this.configured = true
      this.saving = true
      try {
        await saveProfile({
          budget: p.budget,
          flavor_preferences: p.flavor_preferences,
          health_goals: p.health_goals,
        })
      } finally {
        this.saving = false
      }
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
    // 仅持久化 region（后端负责预算/口味/目标隔离）
    pick: ['region'],
    key: 'canteen.profile',
  },
})
