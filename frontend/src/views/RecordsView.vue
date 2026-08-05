<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
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

const MEAL_ORDER = ['breakfast', 'lunch', 'dinner', 'other']

interface DayMeal {
  meal_time: string
  label: string
  items: MealRecordItem[]
}

interface DayGroup {
  date: string
  meals: DayMeal[]
}

// 按日期倒序 → 餐次分组（每个餐次下显示该餐记录的所有菜）
const grouped = computed<DayGroup[]>(() => {
  const dayMap = new Map<string, Map<string, MealRecordItem[]>>()
  for (const r of records.value) {
    if (!dayMap.has(r.date)) dayMap.set(r.date, new Map())
    const mealMap = dayMap.get(r.date)!
    if (!mealMap.has(r.meal_time)) mealMap.set(r.meal_time, [])
    mealMap.get(r.meal_time)!.push(r)
  }
  return Array.from(dayMap.entries()).map(([date, mealMap]) => ({
    date,
    meals: Array.from(mealMap.entries())
      .sort((a, b) => MEAL_ORDER.indexOf(a[0]) - MEAL_ORDER.indexOf(b[0]))
      .map(([meal_time, items]) => ({ meal_time, label: mealLabel(meal_time), items })),
  }))
})

// 日期折叠面板（默认展开最近一天）
const expandedDays = ref<string[]>([])

// 餐次菜品展开状态：`date::meal_time` -> boolean
const mealExpanded = ref<Record<string, boolean>>({})

function mealKey(date: string, meal: string): string {
  return `${date}::${meal}`
}

function toggleMeal(date: string, meal: string): void {
  const k = mealKey(date, meal)
  mealExpanded.value[k] = !mealExpanded.value[k]
}

function isMealExpanded(date: string, meal: string): boolean {
  return !!mealExpanded.value[mealKey(date, meal)]
}

function mealTotalKcal(meal: DayMeal): number {
  return Math.round(meal.items.reduce((s, r) => s + (r.calories || 0), 0))
}

// 是否全部折叠（用于切换按钮文案）
const allCollapsed = computed(() => {
  const keys = grouped.value.flatMap((d) => d.meals.map((m) => mealKey(d.date, m.meal_time)))
  return keys.length > 0 && keys.every((k) => !mealExpanded.value[k])
})

// 全部折叠 / 展开：当前全部折叠则展开全部，否则全部折叠（含日期面板）
function toggleAll(): void {
  const expand = allCollapsed.value
  for (const day of grouped.value) {
    for (const m of day.meals) {
      mealExpanded.value[mealKey(day.date, m.meal_time)] = expand
    }
  }
  if (expand) {
    expandedDays.value = grouped.value.map((d) => d.date)
  } else {
    expandedDays.value = []
  }
}

// 加载到记录后：默认全部折叠
watch(
  records,
  (list) => {
    if (!list.length) return
    // 初始全部折叠
    mealExpanded.value = {}
    if (grouped.value.length) {
      expandedDays.value = [grouped.value[0].date]
    }
  },
  { immediate: true },
)

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
        <span>
          共 <b>{{ summary.total }}</b> 条记录，合计热量 <b>{{ summary.kcal }}</b> kcal
        </span>
        <el-button size="small" text type="primary" @click="toggleAll">
          {{ allCollapsed ? '全部展开' : '全部折叠' }}
        </el-button>
      </div>

      <!-- 记录列表（按日期 → 餐次折叠面板，展开查看该餐所有菜） -->
      <div v-loading="loading" class="records-list">
        <template v-if="records.length">
          <el-collapse v-model="expandedDays" class="record-collapse">
            <el-collapse-item
              v-for="day in grouped"
              :key="day.date"
              :name="day.date"
              :title="day.date"
            >
              <div v-for="meal in day.meals" :key="meal.meal_time" class="record-meal">
                <div class="record-meal-title">
                  <span class="rm-badge" :class="meal.meal_time">{{ meal.label }}</span>
                  <span class="rm-count">{{ meal.items.length }} 道菜</span>
                  <span class="rm-kcal">
                    {{ mealTotalKcal(meal) }} kcal
                  </span>
                  <el-button
                    size="small"
                    text
                    type="primary"
                    class="rm-toggle"
                    @click="toggleMeal(day.date, meal.meal_time)"
                  >
                    {{ isMealExpanded(day.date, meal.meal_time) ? '收起' : '展开' }}
                  </el-button>
                </div>
                <el-collapse-transition>
                  <div v-if="isMealExpanded(day.date, meal.meal_time)" class="record-meal-items">
                    <div v-for="r in meal.items" :key="r.id" class="record-item">
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
                    <el-empty
                      v-if="!meal.items.length"
                      description="该餐次暂无记录"
                      :image-size="60"
                    />
                  </div>
                </el-collapse-transition>
              </div>
            </el-collapse-item>
          </el-collapse>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
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

.record-collapse :deep(.el-collapse-item__header) {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.record-collapse :deep(.el-collapse-item__content) {
  padding-bottom: 8px;
}

.record-meal {
  margin-bottom: 12px;
}

.record-meal-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.rm-kcal {
  margin-left: auto;
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
}

.rm-toggle {
  padding: 0 6px;
  flex-shrink: 0;
}

.rm-badge {
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  white-space: nowrap;
}

/* 午餐：红色，与早餐（绿）、晚餐（橙）明显区分 */
.rm-badge.lunch {
  background: #fdecec;
  color: #f56c6c;
}

.rm-badge.dinner {
  background: #fdf3e7;
  color: #e6a23c;
}

.rm-badge.other {
  background: #f3f4f6;
  color: #909399;
}

.rm-count {
  color: #909399;
  font-size: 12px;
}

.record-meal-items {
  display: flex;
  flex-direction: column;
  gap: 6px;
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
