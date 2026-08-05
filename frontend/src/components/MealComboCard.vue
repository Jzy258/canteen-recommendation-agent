<script setup lang="ts">
import type { ComboMeal, ParsedDish } from '@/types/chat'
import DishCard from '@/components/DishCard.vue'

// 组合优化结果（建议2：组合卡）——展示总热量/总蛋白/总价 + 各菜品
defineProps<{ combo: ComboMeal }>()

// 组合内菜品点击：透传给外层（聊天页），复用填入输入框等业务
const emit = defineEmits<{ (e: 'onDishCardClick', dishItem: ParsedDish): void }>()

function fmt(v: number | undefined): string {
  return v !== undefined && v > 0 ? String(v) : '--'
}
</script>

<template>
  <div class="combo-card">
    <div class="combo-head">
      <span class="combo-title">🍱 推荐搭配</span>
      <span class="combo-balance" :class="combo.balance_ok ? 'ok' : 'warn'">
        {{ combo.balance_ok ? '荤素搭配合理' : '搭配不完整' }}
      </span>
    </div>
    <div class="combo-metrics">
      <div class="combo-metric"><b>{{ fmt(combo.total_calories) }}</b><small>总热量 kcal</small></div>
      <div class="combo-metric"><b>{{ fmt(combo.total_protein) }}</b><small>总蛋白 g</small></div>
      <div class="combo-metric"><b>¥{{ combo.total_price }}</b><small>总价</small></div>
    </div>
    <div class="combo-dishes">
      <DishCard
        v-for="d in combo.dishes"
        :key="d.name"
        :dish="d"
        @onDishCardClick="(d) => emit('onDishCardClick', d)"
      />
    </div>
    <div v-if="combo.reason" class="combo-reason">{{ combo.reason }}</div>
  </div>
</template>

<style scoped>
.combo-card {
  border: 1px solid var(--el-color-primary-light-7);
  border-top: 4px solid var(--el-color-primary);
  border-radius: 12px;
  padding: 12px 14px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.combo-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.combo-title {
  font-weight: 700;
  color: #303133;
  font-size: 14px;
}

.combo-balance {
  font-size: 12px;
}

.combo-balance.ok {
  color: var(--el-color-success);
}

.combo-balance.warn {
  color: var(--el-color-warning);
}

.combo-metrics {
  display: flex;
  gap: 22px;
  margin-bottom: 10px;
}

.combo-metric {
  display: flex;
  flex-direction: column;
}

.combo-metric b {
  color: var(--el-color-primary);
  font-size: 18px;
}

.combo-metric small {
  color: #909399;
  font-size: 11px;
}

.combo-dishes {
  display: grid;
  gap: 8px;
}

.combo-reason {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed var(--el-color-primary-light-8);
  font-size: 12px;
  color: #909399;
}
</style>