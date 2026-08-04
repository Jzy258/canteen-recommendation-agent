<script setup lang="ts">
import { User } from '@element-plus/icons-vue'
import ProfileForm from '@/components/ProfileForm.vue'
</script>

<template>
  <div class="profile-page">
    <el-card shadow="never" class="profile-card">
      <template #header>
        <span class="profile-title">
          <el-icon><User /></el-icon>
          我的偏好
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
</style>
