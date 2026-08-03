<script setup lang="ts">
import { RouterView } from 'vue-router'
</script>

<template>
  <div class="app-shell">
    <el-menu mode="horizontal" router :default-active="$route.path" class="app-nav">
      <el-menu-item index="/">聊天</el-menu-item>
      <el-menu-item index="/trend">营养趋势</el-menu-item>
      <el-menu-item index="/profile">我的偏好</el-menu-item>
    </el-menu>
    <RouterView />
  </div>
</template>

<style scoped>
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-nav {
  position: sticky;
  top: 0;
  z-index: 10;
}
</style>
