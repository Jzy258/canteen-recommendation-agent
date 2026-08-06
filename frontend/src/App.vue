<script setup lang="ts">
import { computed, onBeforeMount, ref } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { ChatDotRound, InfoFilled, KnifeFork, Message, Notebook, Setting, SwitchButton, TrendCharts, User } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { isTokenExpired } from '@/utils/jwt'
import { http } from '@/api/client'

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

// 意见反馈
const feedbackVisible = ref(false)
const feedbackContent = ref('')
const feedbackContact = ref('')
const feedbackSubmitting = ref(false)

function openFeedback(): void {
  feedbackContent.value = ''
  feedbackContact.value = ''
  feedbackVisible.value = true
}

async function submitFeedback(): Promise<void> {
  const content = feedbackContent.value.trim()
  if (!content) {
    ElMessage.warning('请输入反馈内容')
    return
  }
  feedbackSubmitting.value = true
  try {
    await http.post('/feedback', { content, contact: feedbackContact.value.trim() })
    ElMessage.success('感谢您的反馈！')
    feedbackVisible.value = false
  } catch {
    ElMessage.error('提交失败，请稍后重试')
  } finally {
    feedbackSubmitting.value = false
  }
}
</script>

<template>
  <div class="app-shell">
    <header v-if="!isAuthPage" class="app-header">
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
          <el-dropdown trigger="click">
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
                <el-dropdown-item @click="openFeedback">
                  <el-icon style="margin-right: 4px"><Message /></el-icon>
                  反馈
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

    <!-- 意见反馈弹窗 -->
    <el-dialog v-model="feedbackVisible" title="意见反馈" width="480px">
      <el-form label-width="80px">
        <el-form-item label="反馈内容" required>
          <el-input v-model="feedbackContent" type="textarea" :rows="4" placeholder="请描述您的建议、问题或改进想法" />
        </el-form-item>
        <el-form-item label="联系方式">
          <el-input v-model="feedbackContact" placeholder="选填：邮箱 / QQ / 微信，方便我们回复您" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="feedbackVisible = false">取消</el-button>
        <el-button type="primary" :loading="feedbackSubmitting" @click="submitFeedback">提交反馈</el-button>
      </template>
    </el-dialog>
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
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 2fr) minmax(0, 1fr);
  column-gap: 24px;
  align-items: center;
  padding: 0 24px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  box-shadow: 0 1px 8px rgba(50, 177, 108, 0.08);
  border-bottom: 1px solid #eef3f0;
}

/* 菜单整体居中 */
.app-nav-wrap {
  display: flex;
  grid-column: 2;
}

.app-nav {
  border-bottom: none;
  height: 56px;
  flex: 1;
  justify-content: center;
}

.app-nav .el-menu-item {
  flex: 1;
  height: 56px;
  padding: 0 12px;
  line-height: normal;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  gap: 1px;
}

/* 每项专属 logo 徽标 */
.app-nav .el-menu-item .nav-logo {
  width: 28px;
  height: 28px;
  color: var(--el-color-primary-dark-2);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  margin-right: 0;
  margin-bottom: 2px;
  font-size: 16px;
  vertical-align: middle;
}

/* 使 logo 内图标严格水平/垂直居中 */
.app-nav .el-menu-item .nav-logo .el-icon {
  margin: auto;
}

.app-nav .el-menu-item:hover .nav-logo {
  color: var(--el-color-primary);
}

.app-nav .el-menu-item.is-active .nav-logo {
  color: var(--el-color-primary);
}

.app-nav .el-menu-item .nav-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-color-primary-dark-2);
}

.app-nav .el-menu-item.is-active .nav-label {
  color: var(--el-color-primary);
  font-weight: 600;
}

/* 右侧占位，保持品牌-菜单视觉平衡 */
/* grid 对称布局下不再需要占位 */
.app-nav-spacer {
  display: none;
}

/* 用户区（登录状态） */
.app-user {
  display: flex;
  align-items: center;
  margin-left: 12px;
  flex-shrink: 0;
  justify-self: end;
  grid-column: 3;
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

/* ===== D · 响应式：小屏收起品牌与图标，文字标签紧凑显示 ===== */
@media (max-width: 880px) {
  .app-nav-spacer {
    min-width: auto;
  }

  .app-header {
    padding: 0 6px;
    column-gap: 8px;
    grid-template-columns: auto minmax(0, 1fr) auto;
  }

  .app-nav .el-menu-item {
    padding: 0 5px;
  }

  .app-nav .el-menu-item .nav-label {
    font-size: 10px;
    white-space: nowrap;
  }

  /* 缩小图标，与文字标签同行显示，保证全部标签可见 */
  .app-nav .el-menu-item .nav-logo {
    width: 18px;
    height: 18px;
    margin-right: 0;
    font-size: 13px;
  }

  /* 兜底：极端窄屏仍可横向滚动 */
  .app-nav-wrap {
    justify-content: flex-start;
    overflow-x: auto;
    scrollbar-width: none;
    -ms-overflow-style: none;
  }
  .app-nav-wrap::-webkit-scrollbar {
    display: none;
  }
  .app-nav {
    flex-wrap: nowrap;
    justify-content: flex-start;
  }
  .app-user .user-name {
    max-width: 90px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

/* 超小屏：进一步压缩字号，保持文字标签可见 */
@media (max-width: 480px) {
  .app-header {
    padding: 0 4px;
  }
  .app-nav .el-menu-item {
    padding: 0 3px;
  }
  .app-nav .el-menu-item .nav-logo {
    width: 16px;
    height: 16px;
    margin-right: 0;
    font-size: 12px;
  }
  .app-nav .el-menu-item .nav-label {
    font-size: 9px;
  }
  .app-user .user-name {
    display: none;
  }
  .user-trigger {
    padding: 8px 10px;
  }
}
</style>
