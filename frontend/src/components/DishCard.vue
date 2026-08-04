<script setup lang="ts">
import type { ParsedDish } from '@/types/chat'

defineProps<{ dish: ParsedDish }>()

function fmt(v: number | undefined): string {
  return v !== undefined && v > 0 ? String(v) : '--'
}
</script>

<template>
  <div class="dish-card">
    <div class="dish-head">
      <span class="dish-name">{{ dish.name }}</span>
      <span class="dish-price">¥{{ dish.price }}</span>
    </div>
    <div class="dish-nutrition">
      <span class="nut"><b>{{ fmt(dish.calories) }}</b> kcal</span>
      <span class="nut"><b>{{ fmt(dish.protein) }}</b> 蛋白</span>
      <span class="nut"><b>{{ fmt(dish.carbs) }}</b> 碳水</span>
      <span class="nut"><b>{{ fmt(dish.fat) }}</b> 脂肪</span>
    </div>
    <div v-if="dish.reason" class="dish-reason">{{ dish.reason }}</div>
  </div>
</template>

<style scoped>
.dish-card {
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 12px;
  padding: 12px 14px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s, transform 0.2s;
}

.dish-card:hover {
  box-shadow: 0 6px 16px rgba(50, 177, 108, 0.15);
  transform: translateY(-2px);
}

.dish-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.dish-name {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.dish-price {
  color: #e6a23c;
  font-weight: 700;
  white-space: nowrap;
}

.dish-nutrition {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 12px;
  color: #606266;
  margin-top: 8px;
}

.nut b {
  color: #303133;
}

.dish-reason {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed var(--el-color-primary-light-8);
  font-size: 12px;
  color: #909399;
  line-height: 1.6;
}
</style>
