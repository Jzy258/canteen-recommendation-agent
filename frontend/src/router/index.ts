import { createRouter, createWebHistory } from 'vue-router'
import { track } from '@/utils/analytics'
import { isTokenExpired } from '@/utils/jwt'

// P0 · 路由懒加载：按页面分包，降低首屏体积
// 子路径部署：base 跟随 Vite 构建的 base（如部署到 /canteen/ 前缀下，
// 构建时传 --base=/canteen/，站内导航会保持在 /canteen/ 内跳转）
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'chat', component: () => import('@/views/ChatView.vue'), meta: { requiresAuth: true } },
    { path: '/trend', name: 'trend', component: () => import('@/views/TrendView.vue'), meta: { requiresAuth: true } },
    { path: '/menu', name: 'menu', component: () => import('@/views/MenuView.vue'), meta: { requiresAuth: true } },
    { path: '/records', name: 'records', component: () => import('@/views/RecordsView.vue'), meta: { requiresAuth: true } },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue'), meta: { requiresAuth: true } },
    { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue') },
  ],
})

/** 从 localStorage 读取登录态（避免循环依赖 pinia store） */
function getStoredAuth(): { token?: string; user?: unknown } {
  try {
    const raw = localStorage.getItem('canteen.auth')
    return raw ? (JSON.parse(raw) as { token?: string; user?: unknown }) : {}
  } catch {
    return {}
  }
}

/** 渲染前登录态检测：清除过期/无效 token，返回是否有效登录 */
function resolveAuth(): boolean {
  const auth = getStoredAuth()
  if (!auth.token) return false
  // token 过期：渲染前清除，避免加载页面后才被 401 踢回
  if (isTokenExpired(auth.token)) {
    try {
      localStorage.removeItem('canteen.auth')
    } catch {
      // ignore
    }
    return false
  }
  return true
}

// 登录守卫：未登录/过期访问受保护页面 → 跳转登录页并携带 redirect
router.beforeEach((to) => {
  const loggedIn = resolveAuth()

  if (to.meta.requiresAuth && !loggedIn) {
    return {
      name: 'login',
      query: { redirect: to.fullPath },
    }
  }
  // 已登录访问登录页 → 回到首页
  if (to.name === 'login' && loggedIn) {
    return { name: 'chat' }
  }
  return true
})

// P0 · 前端埋点：路由 PV
router.afterEach((to) => {
  track('page_view', { page: to.path })
})

export default router
