<script setup lang="ts">
import { onMounted } from 'vue'
import { User } from '@element-plus/icons-vue'
import ProfileForm from '@/components/ProfileForm.vue'
import { useProfileStore } from '@/stores/profile'

const profileStore = useProfileStore()

// 进入偏好页时从后端加载当前用户画像（按 user_id 隔离）
onMounted(() => {
  profileStore.load()
})
</script>

<template>
  <div class="profile-page">
    <el-card shadow="never" class="profile-card">
      <template #header>
        <span class="profile-title">
          <el-icon><User /></el-icon>
          偏好与设置
        </span>
      </template>
      <ProfileForm />
    </el-card>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 860px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 16px;
}

.profile-card {
  border-radius: 16px;
}

.profile-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #303133;
}

.profile-title .el-icon {
  color: var(--el-color-primary);
}
/* ===== 移动端适配 ===== */
@media (max-width: 768px) {
  .profile-page {
    padding: 10px;
  }
  .profile-card {
    border-radius: 12px;
  }
}
</style>
