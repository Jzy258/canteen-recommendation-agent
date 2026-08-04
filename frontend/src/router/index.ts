import { createRouter, createWebHistory } from 'vue-router'
import { track } from '@/utils/analytics'

// P0 · 路由懒加载：按页面分包，降低首屏体积
const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'chat', component: () => import('@/views/ChatView.vue') },
    { path: '/trend', name: 'trend', component: () => import('@/views/TrendView.vue') },
    { path: '/profile', name: 'profile', component: () => import('@/views/ProfileView.vue') },
  ],
})

// P0 · 前端埋点：路由 PV
router.afterEach((to) => {
  track('page_view', { page: to.path })
})

export default router
