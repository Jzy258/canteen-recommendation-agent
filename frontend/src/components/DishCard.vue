<script setup lang="ts">
import type { Dish } from '@/types/chat'

defineProps<{ dish: Dish }>()
</script>

<template>
  <div class="dish-card">
    <div class="dish-name">{{ dish.name }}</div>
    <div class="dish-meta">{{ dish.category }}</div>
    <div class="dish-nutrition">
      <span class="nut"><b>{{ dish.calories }}</b> kcal</span>
      <span class="nut"><b>{{ dish.protein }}</b> 蛋白</span>
      <span class="nut"><b>{{ dish.carbs }}</b> 碳水</span>
      <span class="nut"><b>{{ dish.fat }}</b> 脂肪</span>
    </div>
    <div class="dish-price">¥{{ dish.price }}</div>
  </div>
</template>

<style scoped>
.dish-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px 14px;
  background: #fff;
  min-width: 180px;
}

.dish-name {
  font-weight: 600;
  font-size: 16px;
}

.dish-meta {
  color: #909399;
  font-size: 12px;
  margin: 2px 0 8px;
}

.dish-nutrition {
  display: flex;
  gap: 10px;
  font-size: 12px;
  color: #606266;
}

.dish-price {
  margin-top: 8px;
  color: #e6a23c;
  font-weight: 600;
}
</style>
