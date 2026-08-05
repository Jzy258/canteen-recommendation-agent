<script setup lang="ts">
import type { ParsedDish } from '@/types/chat'

// 是否可点击：为 false 时卡片变为静态不可点击（去掉 hover、光标恢复默认箭头）
const props = withDefaults(
  defineProps<{
    dish: ParsedDish
    isCardClickable?: boolean
  }>(),
  { isCardClickable: true },
)

// 菜品卡片点击事件：入参为当前菜品完整对象，交由外层（聊天页）处理
const emit = defineEmits<{
  (e: 'onDishCardClick', dishItem: ParsedDish): void
}>()

function fmt(v: number | undefined): string {
  return v !== undefined && v > 0 ? String(v) : '--'
}

// 类别 → emoji 图标映射（建议1）
const CATEGORY_EMOJI: Record<string, string> = {
  荤菜: '🍖',
  素菜: '🥬',
  汤: '🍲',
  主食: '🍚',
  水果: '🍎',
  饮品: '🥤',
}

function categoryEmoji(category?: string): string {
  return (category && CATEGORY_EMOJI[category]) || '🍽️'
}

// 每份推荐克重（g）：仅前端展示文本，按类别映射，不新增字段/不进后端
const RECOMMEND_WEIGHT: Record<string, number> = {
  荤菜: 180,
  素菜: 200,
  主食: 150,
  汤: 300,
  水果: 150,
  饮品: 250,
}
function recommendWeight(category?: string): number {
  return (category && RECOMMEND_WEIGHT[category]) || 180
}

// 根据营养数据前端计算营养标签（建议1）
function nutritionTags(): string[] {
  const d = props.dish
  const tags: string[] = []
  if (d.protein != null && d.protein >= 20) tags.push('高蛋白')
  if (d.fat != null && d.fat <= 8) tags.push('低脂')
  if (d.carbs != null && d.carbs >= 40) tags.push('高碳水')
  if (d.calories != null && d.calories > 0 && d.calories <= 150) tags.push('低卡')
  return tags
}

/**
 * 整卡点击处理：
 * - 阻止事件冒泡，避免触发外层 AI 聊天大卡片的点击逻辑；
 * - 控制台打印菜品完整信息（仅模拟，后续可替换为真实业务）；
 * - 不可点击态直接忽略点击。
 */
function handleDishClick(e: MouseEvent): void {
  e.stopPropagation()
  if (!props.isCardClickable) return
  console.log('[DishCard] 点击菜品完整信息：', props.dish)
  emit('onDishCardClick', props.dish)
}
</script>

<template>
  <div
    class="dish-card"
    :class="{ 'is-clickable': isCardClickable }"
    @click="handleDishClick"
  >
    <div class="dish-head">
      <span class="dish-name">
        <span class="dish-emoji">{{ categoryEmoji(dish.category) }}</span>
        {{ dish.name }}<span class="dish-weight">(推荐{{ recommendWeight(dish.category) }}g)</span>
      </span>
      <span class="dish-price">¥{{ dish.price }}</span>
    </div>
    <div class="dish-nutrition">
      <span class="nut"><b>{{ fmt(dish.calories) }}</b> kcal</span>
      <span class="nut"><b>{{ fmt(dish.protein) }}g</b> 蛋白</span>
      <span class="nut"><b>{{ fmt(dish.carbs) }}g</b> 碳水</span>
      <span class="nut"><b>{{ fmt(dish.fat) }}g</b> 脂肪</span>
    </div>
    <div v-if="nutritionTags().length" class="dish-tags">
      <span v-for="tag in nutritionTags()" :key="tag" class="dish-tag">{{ tag }}</span>
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
  transition: box-shadow 0.2s, transform 0.15s, background-color 0.2s;
}

/* 可点击态：鼠标光标变为 pointer */
.dish-card.is-clickable {
  cursor: pointer;
}

/* hover：柔和上浮阴影 + 背景轻微高亮 */
.dish-card.is-clickable:hover {
  box-shadow: 0 6px 16px rgba(50, 177, 108, 0.18);
  transform: translateY(-2px);
  background: #f6fbf8;
}

/* 按下：按压样式反馈（轻微下沉缩放） */
.dish-card.is-clickable:active {
  transform: translateY(0) scale(0.985);
  box-shadow: 0 2px 6px rgba(50, 177, 108, 0.15);
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

.dish-emoji {
  margin-right: 4px;
}

.dish-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.dish-tag {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
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
