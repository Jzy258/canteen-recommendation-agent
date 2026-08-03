<script setup lang="ts">
import ProfileForm from '@/components/ProfileForm.vue'
</script>

<template>
  <div class="profile-page">
    <el-card shadow="never">
      <template #header>
        <span class="profile-title">我的偏好</span>
      </template>
      <ProfileForm />
    </el-card>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 16px;
}

.profile-title {
  font-weight: 600;
}
</style>
