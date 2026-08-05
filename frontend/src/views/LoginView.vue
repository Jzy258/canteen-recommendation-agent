<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const confirmPassword = ref('')
const displayName = ref('')
const loading = ref(false)

watch(
  () => route.query.mode,
  (m) => {
    if (m === 'register') mode.value = 'register'
  },
  { immediate: true },
)

function switchMode(): void {
  mode.value = mode.value === 'login' ? 'register' : 'login'
  confirmPassword.value = ''
}

function redirectBack(): void {
  const redirect = (route.query.redirect as string) || '/'
  router.replace(redirect)
}

async function submit(): Promise<void> {
  if (!username.value.trim() || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (mode.value === 'register') {
    if (password.value.length < 6) {
      ElMessage.warning('密码至少 6 位')
      return
    }
    if (password.value !== confirmPassword.value) {
      ElMessage.warning('两次输入的密码不一致')
      return
    }
  }
  loading.value = true
  try {
    if (mode.value === 'login') {
      await authStore.login(username.value.trim(), password.value)
      ElMessage.success('登录成功')
    } else {
      await authStore.register(username.value.trim(), password.value, displayName.value.trim())
      ElMessage.success('注册成功，请登录')
      mode.value = 'login'
      password.value = ''
      confirmPassword.value = ''
      return
    }
    redirectBack()
  } catch (e) {
    const err = e as { isApiError?: boolean; apiData?: { detail?: string }; message?: string }
    const detail = err.apiData?.detail
    ElMessage.error(typeof detail === 'string' ? detail : (err.message || '操作失败'))
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="auth-page">
    <el-card class="auth-card" shadow="never">
      <div class="auth-title">
        <span class="auth-logo">🍚</span>
        <h2>{{ mode === 'login' ? '欢迎回来' : '创建账号' }}</h2>
        <p class="auth-sub">食堂菜品推荐与营养分析 Agent</p>
      </div>

      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input
            v-model="username"
            :prefix-icon="User"
            placeholder="用户名"
            autocomplete="username"
          />
        </el-form-item>

        <el-form-item v-if="mode === 'register'">
          <el-input
            v-model="displayName"
            :prefix-icon="User"
            placeholder="昵称（可选）"
          />
        </el-form-item>

        <el-form-item>
          <el-input
            v-model="password"
            :prefix-icon="Lock"
            type="password"
            placeholder="密码"
            show-password
            autocomplete="current-password"
            @keyup.enter="submit"
          />
        </el-form-item>

        <el-form-item v-if="mode === 'register'">
          <el-input
            v-model="confirmPassword"
            :prefix-icon="Lock"
            type="password"
            placeholder="确认密码"
            show-password
            autocomplete="new-password"
            @keyup.enter="submit"
          />
        </el-form-item>

        <el-button
          type="primary"
          class="auth-submit"
          :loading="loading"
          native-type="submit"
          @click="submit"
        >
          {{ mode === 'login' ? '登 录' : '注 册' }}
        </el-button>
      </el-form>

      <div class="auth-switch">
        <span v-if="mode === 'login'">还没有账号？</span>
        <span v-else>已有账号？</span>
        <el-link type="primary" @click="switchMode">
          {{ mode === 'login' ? '立即注册' : '去登录' }}
        </el-link>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.auth-page {
  min-height: calc(100vh - 120px);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  box-sizing: border-box;
}

.auth-card {
  width: 380px;
  max-width: 100%;
  border-radius: 16px;
  padding: 8px 12px;
}

.auth-title {
  text-align: center;
  margin-bottom: 20px;
}

.auth-logo {
  font-size: 36px;
  display: block;
  margin-bottom: 8px;
}

.auth-title h2 {
  margin: 0 0 6px;
  color: #303133;
  font-size: 20px;
}

.auth-sub {
  margin: 0;
  color: #909399;
  font-size: 13px;
}

.auth-submit {
  width: 100%;
  margin-top: 4px;
}

.auth-switch {
  text-align: center;
  margin-top: 16px;
  font-size: 13px;
  color: #606266;
}
</style>
