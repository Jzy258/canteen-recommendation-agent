import { createRouter, createWebHistory } from 'vue-router'
import { track } from '@/utils/analytics'

// P0 · 路由懒加载：按页面分包，降低首屏体积
// 子路径部署：base 跟随 Vite 构建的 base（如部署到 /canteen/ 前缀下，
// 构建时传 --base=/canteen/，站内导航会保持在 /canteen/ 内跳转）
const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', name: 'chat', component: () => import('@/views/ChatView.vue') },
    { path: '/trend', name: 'trend', component: () => import('@/views/TrendView.vue') },
    { path: '/records', name: 'records', component: () => import('@/views/RecordsView.vue') },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
  ],
})

// P0 · 前端埋点：路由 PV
router.afterEach((to) => {
  track('page_view', { page: to.path })
})

export default router
