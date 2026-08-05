<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Calendar, Delete, Edit, Notebook, Plus } from '@element-plus/icons-vue'
import {
  getFoodRecords, createFoodRecord, updateFoodRecord, deleteFoodRecord,
} from '@/api/records'
import type { FoodRecordItem } from '@/types/chat'

const MEAL_LABELS: Record<string, string> = {
  breakfast: '早餐', lunch: '午餐', dinner: '晚餐', other: '其他',
  // 兼容 agent 聊天记录写入的中文餐次
  早餐: '早餐', 午餐: '午餐', 晚餐: '晚餐', 其他: '其他',
}

const MEAL_OPTIONS = [
  { label: '全部', value: '' },
  { label: '早餐', value: 'breakfast' },
  { label: '午餐', value: 'lunch' },
  { label: '晚餐', value: 'dinner' },
  { label: '其他', value: 'other' },
]

const MEAL_CHOICES = [
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
// 第二级：就餐类型
const mealTime = ref('')
const records = ref<FoodRecordItem[]>([])

// 营养折算：聊天记录若用户说明了实际克重（grams>0），按 实际/推荐克重 折算营养
function nutScale(r: FoodRecordItem): number {
  const grams = Number(r.grams) || 0
  const rec = Number(r.recommended_grams) || 0
  return grams > 0 && rec > 0 ? grams / rec : 1
}

// 克重标签：没说明克重 → 显示推荐用量；说明了 → 显示实际克重
function gramLabel(r: FoodRecordItem): string {
  const grams = Number(r.grams) || 0
  const rec = Number(r.recommended_grams) || 0
  if (rec > 0) return grams > 0 ? `克重 ${grams}g` : `克重 推荐 ${rec}g`
  return grams > 0 ? `克重 ${grams}g` : ''
}

// 顶部统计：当前列表总热量 / 总蛋白质（按实际克重折算）
const summary = computed(() => {
  const kcal = records.value.reduce((s, r) => s + (Number(r.calories) || 0) * nutScale(r), 0)
  const protein = records.value.reduce((s, r) => s + (Number(r.protein) || 0) * nutScale(r), 0)
  return { kcal: Math.round(kcal), protein: Math.round(protein) }
})

function mealLabel(m: string): string {
  return MEAL_LABELS[m] ?? '其他'
}

// 查询：按日期范围 + 就餐类型筛选，数据按日期倒序返回
async function load(): Promise<void> {
  loading.value = true
  try {
    records.value = await getFoodRecords({
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

// ---- 新增 / 编辑弹窗 ----
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = ref({
  date: fmtDate(new Date()),
  meal_time: 'lunch',
  name: '',
  price: undefined as number | undefined,
  calories: undefined as number | undefined,
  protein: undefined as number | undefined,
  fat: undefined as number | undefined,
  carbs: undefined as number | undefined,
  grams: undefined as number | undefined,
  remark: '',
})

function openCreate(): void {
  editingId.value = null
  form.value = {
    date: fmtDate(new Date()),
    meal_time: 'lunch',
    name: '',
    price: undefined,
    calories: undefined,
    protein: undefined,
    fat: undefined,
    carbs: undefined,
    grams: undefined,
    remark: '',
  }
  dialogVisible.value = true
}

// 编辑：回填这条记录原有全部数据
function openEdit(r: FoodRecordItem): void {
  editingId.value = r.id
  form.value = {
    date: r.date,
    meal_time: r.meal_time,
    name: r.name,
    price: Number(r.price) || undefined,
    calories: Number(r.calories) || undefined,
    protein: Number(r.protein) || undefined,
    fat: Number(r.fat) || undefined,
    carbs: Number(r.carbs) || undefined,
    grams: Number(r.grams) || undefined,
    remark: r.remark || '',
  }
  dialogVisible.value = true
}

// 提交（新增或编辑）：必填项校验，保存后关闭弹窗并刷新列表
async function submit(): Promise<void> {
  if (!form.value.date) {
    ElMessage.warning('请选择就餐日期')
    return
  }
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入菜品名称')
    return
  }
  try {
    const payload = {
      date: form.value.date,
      meal_time: form.value.meal_time,
      name: form.value.name.trim(),
      price: form.value.price ?? 0,
      calories: form.value.calories ?? 0,
      protein: form.value.protein ?? 0,
      fat: form.value.fat ?? 0,
      carbs: form.value.carbs ?? 0,
      grams: form.value.grams ?? 0,
      remark: form.value.remark,
    }
    if (editingId.value != null) {
      await updateFoodRecord(editingId.value, payload)
      ElMessage.success('记录已更新')
    } else {
      await createFoodRecord(payload)
      ElMessage.success('记录已新增')
    }
    dialogVisible.value = false
    await load()
  } catch {
    ElMessage.error('保存失败，请稍后重试')
  }
}

// 删除：确认后删除并刷新
async function removeRecord(r: FoodRecordItem): Promise<void> {
  try {
    await ElMessageBox.confirm(
      '确定要删除这条饮食记录吗？删除后不可恢复',
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' },
    )
  } catch {
    return
  }
  try {
    await deleteFoodRecord(r.id)
    ElMessage.success('已删除')
    await load()
  } catch {
    ElMessage.error('删除失败，请稍后重试')
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
          <div class="records-actions">
            <el-button size="small" type="primary" plain @click="load">刷新</el-button>
            <el-button size="small" type="primary" :icon="Plus" @click="openCreate">
              新增记录
            </el-button>
          </div>
        </div>
      </template>

      <!-- 筛选控件 -->
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
        <div class="filter-item">
          <span class="filter-label">就餐类型</span>
          <el-radio-group v-model="mealTime" size="default" @change="load">
            <el-radio-button v-for="opt in MEAL_OPTIONS" :key="opt.value" :value="opt.value">
              {{ opt.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
      </div>

      <!-- 统计区域 -->
      <div v-if="records.length" class="records-summary">
        <div class="stat-item">总摄入热量 <b>{{ summary.kcal }}</b> kcal</div>
        <div class="stat-item">总蛋白质 <b>{{ summary.protein }}</b> g</div>
      </div>

      <!-- 记录列表（按日期倒序） -->
      <div v-loading="loading" class="records-list">
        <template v-if="records.length">
          <div v-for="r in records" :key="r.id" class="record-item">
            <div class="ri-left">
              <span class="ri-meal" :class="r.meal_time">{{ mealLabel(r.meal_time) }}</span>
              <span class="ri-date">{{ r.date }}</span>
              <span class="ri-name">{{ r.name }}</span>
            </div>
            <div class="ri-mid">
              <span class="ri-metric price">¥{{ Number(r.price) || 0 }}</span>
              <span class="ri-metric">{{ Math.round((Number(r.calories) || 0) * nutScale(r)) }} kcal</span>
              <span class="ri-metric">蛋白 {{ Math.round((Number(r.protein) || 0) * nutScale(r)) }}g</span>
              <span class="ri-metric">脂肪 {{ Math.round((Number(r.fat) || 0) * nutScale(r)) }}g</span>
              <span class="ri-metric">碳水 {{ Math.round((Number(r.carbs) || 0) * nutScale(r)) }}g</span>
              <span v-if="gramLabel(r)" class="ri-metric">{{ gramLabel(r) }}</span>
            </div>
            <div v-if="r.remark" class="ri-remark">{{ r.remark }}</div>
            <div class="ri-ops">
              <el-button size="small" :icon="Edit" @click="openEdit(r)">编辑</el-button>
              <el-button size="small" type="danger" plain :icon="Delete" @click="removeRecord(r)">
                删除
              </el-button>
            </div>
          </div>
        </template>
        <el-empty v-else-if="!loading" description="暂无饮食记录" />
      </div>
    </el-card>

    <!-- 新增 / 编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="editingId != null ? '编辑饮食记录' : '新增饮食记录'"
      width="480px"
      destroy-on-close
    >
      <el-form label-width="80px">
        <el-form-item label="就餐日期" required>
          <el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
        </el-form-item>
        <el-form-item label="就餐类型" required>
          <el-select v-model="form.meal_time" style="width: 100%">
            <el-option v-for="m in MEAL_CHOICES" :key="m.value" :label="m.label" :value="m.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="菜品名称" required>
          <el-input v-model="form.name" placeholder="请输入菜品名称" />
        </el-form-item>
        <el-form-item label="价格">
          <el-input-number v-model="form.price" :min="0" :max="1000" :precision="2" :step="1" style="width: 180px" />
          <span class="form-unit">元</span>
        </el-form-item>
        <el-form-item label="热量">
          <el-input-number v-model="form.calories" :min="0" :max="5000" style="width: 180px" />
          <span class="form-unit">kcal</span>
        </el-form-item>
        <el-form-item label="蛋白质">
          <el-input-number v-model="form.protein" :min="0" :max="500" :precision="1" style="width: 180px" />
          <span class="form-unit">g</span>
        </el-form-item>
        <el-form-item label="脂肪">
          <el-input-number v-model="form.fat" :min="0" :max="500" :precision="1" style="width: 180px" />
          <span class="form-unit">g</span>
        </el-form-item>
        <el-form-item label="碳水">
          <el-input-number v-model="form.carbs" :min="0" :max="500" :precision="1" style="width: 180px" />
          <span class="form-unit">g</span>
        </el-form-item>
        <el-form-item label="克重">
          <el-input-number v-model="form.grams" :min="0" :max="5000" :precision="1" style="width: 180px" />
          <span class="form-unit">g</span>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.records-page {
  max-width: 860px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 16px;
}

.records-card {
  border-radius: 16px;
}

.records-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.records-actions {
  display: flex;
  gap: 8px;
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

/* 统计区 */
.records-summary {
  display: flex;
  gap: 24px;
  font-size: 13px;
  color: #606266;
  margin-bottom: 12px;
}

.stat-item b {
  color: var(--el-color-primary);
  font-size: 16px;
  margin: 0 2px;
}

/* 列表 */
.records-list {
  min-height: 120px;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 10px 12px;
  margin-bottom: 8px;
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 10px;
  background: #fff;
  font-size: 13px;
  flex-wrap: wrap;
}

.ri-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.ri-meal {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 12px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  white-space: nowrap;
}

.ri-meal.lunch {
  background: #fdecec;
  color: #f56c6c;
}

.ri-meal.dinner {
  background: #fdf3e7;
  color: #e6a23c;
}

.ri-meal.other {
  background: #f3f4f6;
  color: #909399;
}

.ri-date {
  color: #909399;
  font-size: 12px;
  white-space: nowrap;
}

.ri-name {
  font-weight: 600;
  color: #303133;
}

.ri-mid {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #606266;
  flex-wrap: wrap;
}

.ri-metric.price {
  color: #e6a23c;
  font-weight: 600;
}

.ri-remark {
  font-size: 12px;
  color: #909399;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ri-ops {
  margin-left: auto;
  display: flex;
  gap: 8px;
  white-space: nowrap;
}

.form-unit {
  margin-left: 6px;
  color: #909399;
  font-size: 12px;
}
</style>
