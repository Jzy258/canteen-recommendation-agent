<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Refresh, ArrowUp } from '@element-plus/icons-vue'
import {
  getAdminStats, listAdminUsers, updateAdminUser, resetUserPassword,
  listAdminDishes, createAdminDish, updateAdminDish, deleteAdminDish,
  getAdminTokenUsage,
  type AdminStats, type AdminUser, type AdminDish, type DishPayload,
  type AdminTokenUsageItem,
} from '@/api/admin'

const activeTab = ref('overview')
const loading = ref(false)

// ===================== 概览 =====================
const stats = ref<AdminStats | null>(null)
const statCards = computed(() => [
  { label: '用户数', value: stats.value?.user_count ?? 0 },
  { label: '菜品数', value: stats.value?.dish_count ?? 0 },
  { label: '摄入记录', value: stats.value?.record_count ?? 0 },
  { label: '今日记录', value: stats.value?.today_record_count ?? 0 },
])
async function loadStats(): Promise<void> {
  stats.value = await getAdminStats()
}

// ===================== 菜品管理 =====================
const CATEGORIES = ['荤菜', '素菜', '汤', '主食', '水果', '饮品']
const dishes = ref<AdminDish[]>([])
const dishKeyword = ref('')
const dishPage = ref(1)
const dishPageSize = ref(50)
const dishTotal = ref(0)
const dishDialog = ref(false)
const editingDishId = ref<number | null>(null)
const emptyDish = (): DishPayload => ({
  name: '', price: 0, calories: 0, protein: 0, carbs: 0, fat: 0,
  category: '荤菜', flavor_tags: '', source: '中国食物成分表第6版',
})
const dishForm = ref<DishPayload>(emptyDish())
const showBackToTop = ref(false)

function scrollToTop(): void {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

async function loadDishes(): Promise<void> {
  loading.value = true
  try {
    const r = await listAdminDishes(dishKeyword.value, '', dishPage.value, dishPageSize.value)
    dishes.value = r.items
    dishTotal.value = r.total
  } finally {
    loading.value = false
  }
}
function openDishCreate(): void {
  editingDishId.value = null
  dishForm.value = emptyDish()
  dishDialog.value = true
}
function openDishEdit(d: AdminDish): void {
  editingDishId.value = d.id
  dishForm.value = {
    name: d.name, price: d.price, calories: d.calories, protein: d.protein,
    carbs: d.carbs, fat: d.fat, category: d.category,
    flavor_tags: d.flavor_tags, source: d.source,
  }
  dishDialog.value = true
}
async function saveDish(): Promise<void> {
  if (!dishForm.value.name.trim()) { ElMessage.warning('请输入菜品名称'); return }
  try {
    if (editingDishId.value != null) {
      await updateAdminDish(editingDishId.value, dishForm.value)
      ElMessage.success('菜品已更新')
    } else {
      await createAdminDish(dishForm.value)
      ElMessage.success('菜品已新增')
    }
    dishDialog.value = false
    await loadDishes()
  } catch {
    ElMessage.error('保存失败（可能名称已存在）')
  }
}
async function removeDish(d: AdminDish): Promise<void> {
  await ElMessageBox.confirm(`确定删除菜品「${d.name}」吗？`, '删除确认', { type: 'warning' })
  await deleteAdminDish(d.id)
  ElMessage.success('菜品已删除')
  await loadDishes()
}

// ===================== 用户管理 =====================
const users = ref<AdminUser[]>([])
const userKeyword = ref('')
async function loadUsers(): Promise<void> {
  loading.value = true
  try {
    const r = await listAdminUsers(userKeyword.value)
    users.value = r.items
  } finally {
    loading.value = false
  }
}
async function toggleUser(u: AdminUser): Promise<void> {
  const next = u.status === 1 ? 0 : 1
  await updateAdminUser(u.id, { status: next })
  u.status = next
  ElMessage.success(next === 1 ? '账号已启用' : '账号已禁用')
}
async function changeRole(u: AdminUser, role: string): Promise<void> {
  try {
    await updateAdminUser(u.id, { role })
    u.role = role as AdminUser['role']
    ElMessage.success('角色已更新')
  } catch {
    ElMessage.error('角色更新失败（不能修改自己的角色）')
  }
}
async function resetPwd(u: AdminUser): Promise<void> {
  const { value } = await ElMessageBox.prompt(`为「${u.username}」设置新密码（至少 6 位）`, '重置密码', {
    inputPattern: /^.{6,}$/,
    inputErrorMessage: '密码至少 6 位',
  })
  await resetUserPassword(u.id, value)
  ElMessage.success('密码已重置')
}

// ===================== Token 用量 =====================
const tokenUsage = ref<AdminTokenUsageItem[]>([])
const tokenTotal = ref(0)
async function loadTokenUsage(): Promise<void> {
  loading.value = true
  try {
    const r = await getAdminTokenUsage()
    tokenUsage.value = r.items
    tokenTotal.value = r.total_tokens
  } finally {
    loading.value = false
  }
}

// ===================== 初始化 =====================
onMounted(async () => {
  await Promise.all([loadStats(), loadDishes(), loadUsers(), loadTokenUsage()])
  const onScroll = () => { showBackToTop.value = window.scrollY > 200 }
  window.addEventListener('scroll', onScroll)
  // 初始化显示状态
  onScroll()
  onUnmounted(() => window.removeEventListener('scroll', onScroll))
})
</script>

<template>
  <div class="admin-page">
    <el-card shadow="never" class="admin-card">
      <template #header>
        <div class="admin-header">
          <span class="admin-title">⚙️ 后台管理系统</span>
          <el-button size="small" :icon="Refresh" @click="loadStats">刷新统计</el-button>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <!-- 概览 -->
        <el-tab-pane label="概览" name="overview">
          <div v-loading="loading" class="stat-grid">
            <div v-for="c in statCards" :key="c.label" class="stat-card">
              <div class="stat-value">{{ c.value }}</div>
              <div class="stat-label">{{ c.label }}</div>
            </div>
          </div>
        </el-tab-pane>

        <!-- 菜品管理 -->
        <el-tab-pane label="菜品管理" name="dishes">
          <div class="toolbar">
            <el-input v-model="dishKeyword" placeholder="搜索菜名" clearable style="width: 220px" @change="loadDishes" @clear="loadDishes" />
            <el-button type="primary" :icon="Plus" @click="openDishCreate">新增菜品</el-button>
          </div>
          <el-table v-loading="loading" :data="dishes" stripe size="small">
            <el-table-column prop="name" label="名称" min-width="110" />
            <el-table-column prop="category" label="类别" width="70" />
            <el-table-column prop="price" label="价格(元)" width="90" />
            <el-table-column prop="calories" label="热量" width="80" />
            <el-table-column prop="protein" label="蛋白(g)" width="80" />
            <el-table-column prop="carbs" label="碳水(g)" width="85" />
            <el-table-column prop="fat" label="脂肪(g)" width="80" />
            <el-table-column prop="flavor_tags" label="口味" width="90" />
            <el-table-column prop="source" label="来源" min-width="120" show-overflow-tooltip />
            <el-table-column label="操作" width="140" fixed="right">
              <template #default="{ row }">
                <div class="row-actions row-actions--left">
                  <el-tooltip content="编辑" placement="top">
                    <el-button size="small" circle :icon="Edit" @click="openDishEdit(row)" />
                  </el-tooltip>
                  <el-tooltip content="删除" placement="top">
                    <el-button size="small" circle type="danger" plain :icon="Delete" @click="removeDish(row)" />
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>
          <div style="padding:12px 6px; text-align:right">
            <el-pagination
              background
              :current-page="dishPage"
              :page-size="dishPageSize"
              :total="dishTotal"
              layout="prev, pager, next, sizes, jumper, total"
              :page-sizes="[10, 20, 50, 100]"
              @current-change="(p: number) => { dishPage = p; loadDishes() }"
              @size-change="(s: number) => { dishPageSize = s; dishPage = 1; loadDishes() }"
            />
          </div>
          <el-button
            v-show="showBackToTop"
            class="back-to-top"
            type="primary"
            circle
            :icon="ArrowUp"
            @click="scrollToTop"
          ></el-button>
        </el-tab-pane>

        <!-- 用户管理 -->
        <el-tab-pane label="用户管理" name="users">
          <div class="toolbar">
            <el-input v-model="userKeyword" placeholder="搜索用户名/昵称" clearable style="width: 220px" @change="loadUsers" @clear="loadUsers" />
          </div>
          <el-table v-loading="loading" :data="users" stripe size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="username" label="用户名" min-width="110" />
            <el-table-column prop="display_name" label="昵称" width="110" />
            <el-table-column label="角色" width="110">
              <template #default="{ row }">
                <el-select :model-value="row.role" size="small" style="width: 90px" @change="(v: string) => changeRole(row, v)">
                  <el-option label="管理员" value="admin" />
                  <el-option label="普通用户" value="user" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
                  {{ row.status === 1 ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="注册时间" width="150" />
            <el-table-column label="操作" width="180" fixed="right">
              <template #default="{ row }">
                <div class="row-actions">
                  <el-tooltip :content="row.status === 1 ? '禁用账号' : '启用账号'" placement="top">
                    <el-button size="small" circle plain @click="toggleUser(row)">{{ row.status === 1 ? '禁' : '启' }}</el-button>
                  </el-tooltip>
                  <el-tooltip content="重置密码" placement="top">
                    <el-button size="small" circle type="warning" plain :icon="Refresh" @click="resetPwd(row)" />
                  </el-tooltip>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <!-- Token 用量 -->
        <el-tab-pane label="Token 用量" name="tokens">
          <div class="toolbar">
            <span class="token-total">
              累计 Token：<b>{{ tokenTotal.toLocaleString() }}</b>
            </span>
            <el-button :icon="Refresh" @click="loadTokenUsage">刷新</el-button>
          </div>
          <el-table v-loading="loading" :data="tokenUsage" stripe size="small">
            <el-table-column prop="id" label="ID" width="60" />
            <el-table-column prop="username" label="用户名" min-width="110" />
            <el-table-column prop="display_name" label="昵称" width="110" />
            <el-table-column label="角色" width="90">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                  {{ row.role === 'admin' ? '管理员' : '普通用户' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="Token 用量" min-width="130">
              <template #default="{ row }">
                <span :class="{ 'token-zero': row.tokens === 0 }">{{ row.tokens.toLocaleString() }}</span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 1 ? 'success' : 'danger'" size="small">
                  {{ row.status === 1 ? '启用' : '禁用' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <!-- 新增 / 编辑菜品弹窗 -->
    <el-dialog v-model="dishDialog" :title="editingDishId != null ? '编辑菜品' : '新增菜品'" width="480px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="dishForm.name" placeholder="请输入菜品名称" />
        </el-form-item>
        <el-form-item label="类别">
          <el-select v-model="dishForm.category" style="width: 100%">
            <el-option v-for="c in CATEGORIES" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="价格(元)">
          <el-input-number v-model="dishForm.price" :min="0" :max="1000" :precision="1" style="width: 180px" />
        </el-form-item>
        <el-form-item label="热量(kcal)">
          <el-input-number v-model="dishForm.calories" :min="0" :max="5000" style="width: 180px" />
        </el-form-item>
        <el-form-item label="蛋白(g)">
          <el-input-number v-model="dishForm.protein" :min="0" :max="500" :precision="1" style="width: 180px" />
        </el-form-item>
        <el-form-item label="碳水(g)">
          <el-input-number v-model="dishForm.carbs" :min="0" :max="500" :precision="1" style="width: 180px" />
        </el-form-item>
        <el-form-item label="脂肪(g)">
          <el-input-number v-model="dishForm.fat" :min="0" :max="500" :precision="1" style="width: 180px" />
        </el-form-item>
        <el-form-item label="口味标签">
          <el-input v-model="dishForm.flavor_tags" placeholder="如 辣,酸甜（逗号分隔）" />
        </el-form-item>
        <el-form-item label="参考来源">
          <el-input v-model="dishForm.source" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dishDialog = false">取消</el-button>
        <el-button type="primary" @click="saveDish">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-page {
  max-width: 1200px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 16px;
}
.admin-card {
  border-radius: 16px;
}
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.admin-title {
  font-weight: 700;
  color: #303133;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 18px;
}
.stat-card {
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 12px;
  padding: 18px;
  text-align: center;
  background: #fff;
}
.stat-value {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.stat-label {
  margin-top: 6px;
  font-size: 13px;
  color: #909399;
}
.toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.token-total {
  font-size: 13px;
  color: #606266;
}
.token-total b {
  color: var(--el-color-primary);
  font-size: 16px;
  margin: 0 2px;
}
.token-zero {
  color: #c0c4cc;
}

.back-to-top {
  position: fixed;
  right: 24px;
  bottom: 84px;
  z-index: 1200;
  box-shadow: 0 6px 16px rgba(0,0,0,0.12);
}

.row-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-end;
}

.row-actions--left {
  justify-content: flex-start;
}
</style>
