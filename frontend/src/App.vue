<script setup lang="ts">
import { RouterView } from 'vue-router'
import { ChatDotRound, KnifeFork, Notebook, TrendCharts, User } from '@element-plus/icons-vue'
</script>

<template>
  <div class="app-shell">
    <header class="app-header">
      <div class="app-brand">
        <span class="brand-logo">
          <el-icon :size="18"><KnifeFork /></el-icon>
        </span>
        <span class="brand-name">食堂推荐 Agent</span>
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
            <span class="nav-label">我的偏好</span>
          </el-menu-item>
        </el-menu>
      </nav>

      <div class="app-nav-spacer" />
    </header>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <transition name="fade-slide" mode="out-in">
          <component :is="Component" />
        </transition>
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
