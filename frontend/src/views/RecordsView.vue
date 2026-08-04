<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Calendar, Notebook } from '@element-plus/icons-vue'
import { getRecords } from '@/api/records'
import type { MealRecordItem } from '@/types/chat'

const MEAL_LABELS: Record<string, string> = {
  breakfast: '早餐',
  lunch: '午餐',
  dinner: '晚餐',
  other: '其他',
}

const MEAL_OPTIONS = [
  { label: '全部', value: '' },
  { label: '早餐', value: 'breakfast' },
  { label: '午餐', value: 'lunch' },
  { label: '晚餐', value: 'dinner' },
  { label: '其他', value: 'other' },
]

function fmtDate(d: Date): string {
  return d.toISOString().slice(0, 10)
}

function defaultRange(): [string, string] {
  const end = new Date()
  const start = new Date()
  start.setDate(start.getDate() - 29)
  return [fmtDate(start), fmtDate(end)]
}

const loading = ref(false)
// 第一级：日期范围（默认最近 30 天）
const dateRange = ref<[string, string]>(defaultRange())
// 第二级：餐次
const mealTime = ref('')
const records = ref<MealRecordItem[]>([])

// 按日期倒序分组
const grouped = computed(() => {
  const map = new Map<string, MealRecordItem[]>()
  for (const r of records.value) {
    if (!map.has(r.date)) map.set(r.date, [])
    map.get(r.date)!.push(r)
  }
  return Array.from(map.entries())
})

const summary = computed(() => {
  const total = records.value.length
  const kcal = records.value.reduce((s, r) => s + (r.calories || 0) * r.portion, 0)
  return { total, kcal: Math.round(kcal) }
})

function mealLabel(m: string): string {
  return MEAL_LABELS[m] ?? '其他'
}

async function load(): Promise<void> {
  loading.value = true
  try {
    records.value = await getRecords({
      start_date: dateRange.value[0],
      end_date: dateRange.value[1],
      meal_time: mealTime.value,
    })
  } catch {
    ElMessage.error('饮食记录加载失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="records-page">
    <el-card shadow="never" class="records-card">
      <template #header>
        <div class="records-header">
          <span class="records-title">
            <el-icon><Notebook /></el-icon>
            饮食记录
          </span>
          <el-button size="small" type="primary" plain @click="load">刷新</el-button>
        </div>
      </template>

      <!-- 第一级：日期范围选择 -->
      <div class="filter-row">
        <div class="filter-item">
          <span class="filter-label">
            <el-icon><Calendar /></el-icon>
            日期范围
          </span>
          <el-date-picker
            v-model="dateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            :clearable="false"
            @change="load"
          />
        </div>

        <!-- 第二级：餐次选择 -->
        <div class="filter-item">
          <span class="filter-label">餐次</span>
          <el-radio-group v-model="mealTime" size="default" @change="load">
            <el-radio-button v-for="opt in MEAL_OPTIONS" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 汇总 -->
      <div v-if="!loading && records.length" class="records-summary">
        共 <b>{{ summary.total }}</b> 条记录，合计热量 <b>{{ summary.kcal }}</b> kcal
      </div>

      <!-- 记录列表（按日期分组） -->
      <div v-loading="loading" class="records-list">
        <template v-if="records.length">
          <section v-for="[date, items] in grouped" :key="date" class="record-day">
            <div class="record-day-title">{{ date }}</div>
            <div class="record-day-items">
              <div v-for="r in items" :key="r.id" class="record-item">
                <span class="ri-meal" :class="r.meal_time">{{ mealLabel(r.meal_time) }}</span>
                <span class="ri-name">{{ r.dish_name }}</span>
                <span class="ri-cat">{{ r.category }}</span>
                <span class="ri-nut">
                  <span v-if="r.calories">{{ r.calories }} kcal</span>
                  <span v-if="r.protein">· 蛋白{{ r.protein }}g</span>
                  <span v-if="r.carbs">· 碳水{{ r.carbs }}g</span>
                  <span v-if="r.fat">· 脂肪{{ r.fat }}g</span>
                  <span v-if="r.portion !== 1">· x{{ r.portion }}</span>
                </span>
                <span class="ri-price">¥{{ r.price }}</span>
              </div>
            </div>
          </section>
        </template>

        <el-empty
          v-else-if="!loading"
          description="该范围内暂无饮食记录"
        />
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.records-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 16px;
  width: 100%;
}

.records-card {
  border-radius: 16px;
}

.records-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.records-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #303133;
}

.records-title .el-icon {
  color: var(--el-color-primary);
}

/* 筛选区 */
.filter-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 20px;
  margin-bottom: 16px;
}

.filter-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-label {
  display: flex;
  align-items: center;
  gap: 4px;
  color: #606266;
  font-size: 13px;
  white-space: nowrap;
}

.records-summary {
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
}

.records-summary b {
  color: var(--el-color-primary);
}

/* 记录列表 */
.records-list {
  min-height: 120px;
}

.record-day {
  margin-bottom: 16px;
}

.record-day-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
  border-left: 3px solid var(--el-color-primary);
  padding-left: 8px;
}

.record-day-items {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 10px;
  background: #fff;
  font-size: 13px;
  flex-wrap: wrap;
}

.ri-meal {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  white-space: nowrap;
}

.ri-meal.dinner {
  background: #fdf3e7;
  color: #e6a23c;
}

.ri-meal.other {
  background: #f3f4f6;
  color: #909399;
}

.ri-name {
  font-weight: 600;
  color: #303133;
}

.ri-cat {
  color: #909399;
  font-size: 12px;
}

.ri-nut {
  color: #606266;
  font-size: 12px;
}

.ri-price {
  color: #e6a23c;
  font-weight: 600;
  margin-left: auto;
  white-space: nowrap;
}
</style>
