import { createRouter, createWebHistory } from 'vue-router'
import ChatView from '@/views/ChatView.vue'
import TrendView from '@/views/TrendView.vue'
import ProfileView from '@/views/ProfileView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'chat', component: ChatView },
    { path: '/trend', name: 'trend', component: TrendView },
    { path: '/profile', name: 'profile', component: ProfileView },
  ],
})

export default router
