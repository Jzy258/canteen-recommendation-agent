<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { Calendar, Lightning, Wallet } from '@element-plus/icons-vue'
import { getRecords } from '@/api/records'
import { useProfileStore } from '@/stores/profile'

// 今日工作台（建议5）：展示今日已摄入热量 / 记录菜数 / 每餐预算，并提供"今日吃什么"快捷入口
const profileStore = useProfileStore()

const todayKcal = ref(0)
const todayDishes = ref(0)

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}

// 后端 /records 已只返回已确认记录，直接求和
async function loadToday(): Promise<void> {
  const today = todayStr()
  try {
    const records = await getRecords({ start_date: today, end_date: today })
    todayKcal.value = Math.round(records.reduce((s, r) => s + (r.calories || 0) * r.portion, 0))
    todayDishes.value = records.length
  } catch {
    todayKcal.value = 0
    todayDishes.value = 0
  }
}

const budgetLabel = computed(() => {
  const hi = profileStore.budget
  const lo = profileStore.budget_min
  return lo > 0 ? `${lo}~${hi} 元` : `${hi} 元`
})

onMounted(loadToday)

const emit = defineEmits<{ (e: 'recommend'): void }>()
</script>

<template>
  <div class="today-overview">
    <div class="to-item">
      <el-icon class="to-icon fire"><Lightning /></el-icon>
      <div class="to-meta">
        <span class="to-label">今日已摄入</span>
        <span class="to-value">{{ todayKcal }} kcal</span>
      </div>
    </div>
    <div class="to-item">
      <el-icon class="to-icon wallet"><Wallet /></el-icon>
      <div class="to-meta">
        <span class="to-label">每餐预算</span>
        <span class="to-value">{{ budgetLabel }}</span>
      </div>
    </div>
    <div class="to-item">
      <el-icon class="to-icon cal"><Calendar /></el-icon>
      <div class="to-meta">
        <span class="to-label">今日记录</span>
        <span class="to-value">{{ todayDishes }} 道菜</span>
      </div>
    </div>
    <el-button class="to-action" type="primary" plain size="small" @click="emit('recommend')">
      今日吃什么？
    </el-button>
  </div>
</template>

<style scoped>
.today-overview {
  display: flex;
  align-items: center;
  gap: 20px;
  flex-wrap: wrap;
  padding: 12px 16px;
  margin-bottom: 14px;
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.to-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.to-icon {
  font-size: 18px;
}

.to-icon.fire { color: #f56c6c; }
.to-icon.wallet { color: #e6a23c; }
.to-icon.cal { color: #32b16c; }

.to-meta {
  display: flex;
  flex-direction: column;
}

.to-label {
  font-size: 11px;
  color: #909399;
}

.to-value {
  font-size: 15px;
  font-weight: 700;
  color: #303133;
}

.to-action {
  margin-left: auto;
}
</style>