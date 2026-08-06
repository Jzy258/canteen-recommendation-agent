<script setup lang="ts">
import { computed, onBeforeMount } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { ChatDotRound, InfoFilled, KnifeFork, Notebook, Setting, SwitchButton, TrendCharts, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { isTokenExpired } from '@/utils/jwt'

const authStore = useAuthStore()
const route = useRoute()

// 渲染前清理过期登录态，保证导航栏状态与路由守卫一致
onBeforeMount(() => {
  if (authStore.token && isTokenExpired(authStore.token)) {
    authStore.logout()
  }
})

// 登录/注册页不显示导航栏用户区
const isAuthPage = computed(() => route.name === 'login')

function onLogout(): void {
  authStore.logout()
  // 回到登录页
  window.location.href = `${import.meta.env.BASE_URL}login`
}

function goLogin(): void {
  window.location.href = `${import.meta.env.BASE_URL}login`
}

function goAbout(): void {
  window.location.href = `${import.meta.env.BASE_URL}about`
}
</script>

<template>
  <div class="app-shell">
    <header v-if="!isAuthPage" class="app-header">
      <div class="app-brand">
        <span class="brand-logo">
          <el-icon :size="18"><KnifeFork /></el-icon>
        </span>
        <span class="brand-name">食堂推荐 Agent</span>
        <a
          href="https://github.com/Jzy258/canteen-recommendation-agent"
          target="_blank"
          rel="noopener noreferrer"
          class="brand-github"
          title="GitHub 仓库"
        >
          <svg viewBox="0 0 16 16" width="18" height="18" fill="currentColor" aria-hidden="true">
            <path d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z"/>
          </svg>
        </a>
      </div>

      <nav class="app-nav-wrap">
        <el-menu
          mode="horizontal"
          router
          :default-active="$route.path"
          class="app-nav"
          :ellipsis="false"
        >
          <el-menu-item index="/">
            <span class="nav-logo"><el-icon><ChatDotRound /></el-icon></span>
            <span class="nav-label">聊天</span>
          </el-menu-item>
          <el-menu-item index="/menu">
            <span class="nav-logo"><el-icon><KnifeFork /></el-icon></span>
            <span class="nav-label">菜单</span>
          </el-menu-item>
          <el-menu-item index="/trend">
            <span class="nav-logo"><el-icon><TrendCharts /></el-icon></span>
            <span class="nav-label">营养趋势</span>
          </el-menu-item>
          <el-menu-item index="/records">
            <span class="nav-logo"><el-icon><Notebook /></el-icon></span>
            <span class="nav-label">饮食记录</span>
          </el-menu-item>
          <el-menu-item index="/profile">
            <span class="nav-logo"><el-icon><User /></el-icon></span>
            <span class="nav-label">偏好与设置</span>
          </el-menu-item>
          <el-menu-item v-if="authStore.isAdmin" index="/admin">
            <span class="nav-logo"><el-icon><Setting /></el-icon></span>
            <span class="nav-label">后台管理</span>
          </el-menu-item>
        </el-menu>
      </nav>

      <div class="app-nav-spacer" />

      <div v-if="!isAuthPage" class="app-user">
        <template v-if="authStore.isLoggedIn">
          <el-dropdown>
            <span class="user-trigger">
              <el-icon :size="16"><User /></el-icon>
              <span class="user-name">{{ authStore.displayName }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-if="authStore.isAdmin" disabled>
                  管理员
                </el-dropdown-item>
                <el-dropdown-item :divided="authStore.isAdmin" @click="goAbout">
                  <el-icon style="margin-right: 4px"><InfoFilled /></el-icon>
                  关于
                </el-dropdown-item>
                <el-dropdown-item @click="onLogout">
                  <el-icon style="margin-right: 4px"><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </template>
        <template v-else>
          <el-button class="login-btn" @click="goLogin">
            <el-icon :size="15" style="margin-right: 4px"><User /></el-icon>
            登录 / 注册
          </el-button>
        </template>
      </div>
    </header>

    <main class="app-main">
      <!-- keep-alive：切换标签页时缓存页面组件，返回后保持原样（聊天记录等不丢失）。
           注意：transition 与 keep-alive 组合在本项目存在缓存组件未隐藏的 bug，
           故此处只使用 keep-alive（fade-slide 动画在页面内部元素上实现）。 -->
      <router-view v-slot="{ Component }">
        <keep-alive>
          <component :is="Component" />
        </keep-alive>
      </router-view>
    </main>
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ===== 顶部导航：居中 + 每项专属 logo 徽标 ===== */
.app-header {
  position: sticky;
  top: 0;
  z-index: 10;
  display: flex;
  align-items: center;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  box-shadow: 0 1px 8px rgba(50, 177, 108, 0.08);
  border-bottom: 1px solid #eef3f0;
}

/* 品牌区 */
.app-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 190px;
}

.brand-logo {
  width: 34px;
  height: 34px;
  border-radius: 10px;
  background: linear-gradient(135deg, #32b16c, #288e56);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 8px rgba(50, 177, 108, 0.35);
}

.brand-name {
  font-weight: 700;
  font-size: 16px;
  color: #1f2d27;
  letter-spacing: 0.5px;
  white-space: nowrap;
}

/* GitHub 仓库链接图标 */
.brand-github {
  display: inline-flex;
  align-items: center;
  color: #909399;
  transition: color 0.2s, transform 0.2s;
}

.brand-github:hover {
  color: #303133;
  transform: translateY(-1px);
}

/* 菜单整体居中 */
.app-nav-wrap {
  flex: 1;
  display: flex;
  justify-content: center;
}

.app-nav {
  border-bottom: none;
}

.app-nav .el-menu-item {
  height: 56px;
  line-height: 56px;
}

/* 每项专属 logo 徽标 */
.app-nav .el-menu-item .nav-logo {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 8px;
  font-size: 15px;
  vertical-align: middle;
  transition: all 0.2s;
}

/* 使 logo 内图标严格水平/垂直居中 */
.app-nav .el-menu-item .nav-logo .el-icon {
  margin: auto;
}

.app-nav .el-menu-item:hover .nav-logo {
  background: var(--el-color-primary-light-8);
  transform: scale(1.06);
}

.app-nav .el-menu-item.is-active .nav-logo {
  background: var(--el-color-primary);
  color: #fff;
}

.app-nav .el-menu-item .nav-label {
  font-size: 14px;
  font-weight: 500;
}

/* 右侧占位，保持品牌-菜单视觉平衡 */
.app-nav-spacer {
  min-width: 190px;
}

/* 用户区（登录状态） */
.app-user {
  display: flex;
  align-items: center;
  margin-left: 12px;
  flex-shrink: 0;
}

.user-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: #606266;
  font-size: 13px;
  padding: 4px 8px;
  border-radius: 8px;
  transition: all 0.2s;
}

.user-trigger:hover {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.user-name {
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 醒目登录按钮 */
.login-btn {
  background: linear-gradient(135deg, #32b16c, #288e56);
  border: none;
  color: #fff;
  font-weight: 600;
  border-radius: 999px;
  padding: 8px 18px;
  box-shadow: 0 3px 10px rgba(50, 177, 108, 0.35);
  transition: all 0.2s;
}

.login-btn:hover,
.login-btn:focus {
  background: linear-gradient(135deg, #3dc47a, #2c9a5c);
  color: #fff;
  transform: translateY(-1px);
  box-shadow: 0 5px 16px rgba(50, 177, 108, 0.45);
}

/* 主体 */
.app-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

/* ===== D · 响应式：小屏收起品牌文字、压缩间距 ===== */
@media (max-width: 640px) {
  .app-brand {
    min-width: auto;
  }

  .brand-name {
    display: none;
  }

  .app-nav-spacer {
    min-width: auto;
  }

  .app-header {
    padding: 0 8px;
  }

  .app-nav .el-menu-item {
    padding: 0 12px;
  }

  .app-nav .el-menu-item .nav-label {
    font-size: 12px;
  }
}
</style>
