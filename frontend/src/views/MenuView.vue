<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Food, ArrowUp } from '@element-plus/icons-vue'
import { getDishes, type MenuDish } from '@/api/menu'

const dishes = ref<MenuDish[]>([])
const loading = ref(false)

// 参考截图：素食/不辣/粥类/面食/低热量 等标签（前端规则计算）
function tags(d: MenuDish): string[] {
  const t: string[] = []
  const name = d.name || ''
  const flavor = String(d.flavor_tags || '')
  if (d.category === '素菜') t.push('素食')
  if (!flavor.includes('辣')) t.push('不辣')
  if (name.includes('粥')) t.push('粥类')
  if (name.includes('面') || name.includes('馒头') || name.includes('花卷')) t.push('面食')
  if (Number(d.calories) > 0 && Number(d.calories) <= 150) t.push('低热量')
  return t
}


// ===== 筛选状态（UI 控件实时绑定，交集过滤）=====
const keyword = ref('')                    // 菜名模糊搜索
const categorySel = ref<string[]>([])      // 类别多选：荤菜/素菜/主食/汤品
const spiceSel = ref<string[]>([])         // 辣度多选：不辣/微辣/中辣/重辣
const priceMin = ref<number | undefined>() // 价格区间
const priceMax = ref<number | undefined>()
const calMin = ref<number | undefined>()   // 热量区间
const calMax = ref<number | undefined>()
const protMin = ref<number | undefined>()  // 蛋白质区间
const protMax = ref<number | undefined>()
const fatMin = ref<number | undefined>()    // 脂肪区间
const fatMax = ref<number | undefined>()
const carbMin = ref<number | undefined>()  // 碳水区间
const carbMax = ref<number | undefined>()
const sortBy = ref('')                     // 排序：cal-asc / cal-desc / price-asc / price-desc
const page = ref(1)
const pageSize = ref(12)
const showBackToTop = ref(false)

// 类别筛选选项（“汤品”匹配 category === '汤'）
const CATEGORY_OPTIONS = [
  { label: '荤菜', value: '荤菜' },
  { label: '素菜', value: '素菜' },
  { label: '主食', value: '主食' },
  { label: '汤品', value: '汤' },
  { label: '水果', value: '水果' },
  { label: '饮品', value: '饮品' },
]

// 辣度映射：根据 flavor_tags 判断（数据多为“辣”，默认按中辣；支持微/中/重辣关键词）
function spiceLevel(d: MenuDish): string {
  const f = String(d.flavor_tags || '')
  if (!f.includes('辣')) return '不辣'
  if (f.includes('重辣')) return '重辣'
  if (f.includes('中辣')) return '中辣'
  if (f.includes('微辣')) return '微辣'
  return '中辣'
}

// 筛选结果（全部条件为交集，实时计算；含排序）
const filtered = computed(() => {
  let list = dishes.value
  const kw = keyword.value.trim()
  if (kw) list = list.filter((d) => (d.name || '').includes(kw))
  if (categorySel.value.length) {
    list = list.filter((d) => categorySel.value.includes(String(d.category || '')))
  }
  if (spiceSel.value.length) {
    list = list.filter((d) => spiceSel.value.includes(spiceLevel(d)))
  }
  const pMin = priceMin.value, pMax = priceMax.value
  if (pMin != null) list = list.filter((d) => Number(d.price) >= pMin)
  if (pMax != null) list = list.filter((d) => Number(d.price) <= pMax)
  const cMin = calMin.value, cMax = calMax.value
  if (cMin != null) list = list.filter((d) => Number(d.calories) >= cMin)
  if (cMax != null) list = list.filter((d) => Number(d.calories) <= cMax)
  const rMin = protMin.value, rMax = protMax.value
  if (rMin != null) list = list.filter((d) => Number(d.protein) >= rMin)
  if (rMax != null) list = list.filter((d) => Number(d.protein) <= rMax)
  const fMin = fatMin.value, fMax = fatMax.value
  if (fMin != null) list = list.filter((d) => Number(d.fat) >= fMin)
  if (fMax != null) list = list.filter((d) => Number(d.fat) <= fMax)
  const cbMin = carbMin.value, cbMax = carbMax.value
  if (cbMin != null) list = list.filter((d) => Number(d.carbs) >= cbMin)
  if (cbMax != null) list = list.filter((d) => Number(d.carbs) <= cbMax)
  const s = sortBy.value
  if (s) {
    const key = s.startsWith('price') ? 'price' : 'calories'
    const desc = s.endsWith('desc')
    list = [...list].sort((a, b) => (Number(a[key]) - Number(b[key])) * (desc ? -1 : 1))
  }
  return list
})

const pageCount = computed(() => Math.max(1, Math.ceil(filtered.value.length / pageSize.value)))
const pageData = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filtered.value.slice(start, start + pageSize.value)
})

watch([filtered, pageSize], () => {
  if (page.value > pageCount.value) {
    page.value = pageCount.value
  }
})

function scrollToTop(): void {
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function onScroll(): void {
  showBackToTop.value = window.scrollY > 200
}

function resetFilters(): void {
  keyword.value = ''
  categorySel.value = []
  spiceSel.value = []
  priceMin.value = undefined
  priceMax.value = undefined
  calMin.value = undefined
  calMax.value = undefined
  protMin.value = undefined
  protMax.value = undefined
  fatMin.value = undefined
  fatMax.value = undefined
  carbMin.value = undefined
  carbMax.value = undefined
  sortBy.value = ''
}


async function load(): Promise<void> {
  loading.value = true
  try {
    dishes.value = await getDishes()
  } catch {
    ElMessage.error('菜单加载失败，请确认后端已启动')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load()
  window.addEventListener('scroll', onScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', onScroll)
})
</script>

<template>
  <div class="menu-page">
    <el-card shadow="never" class="menu-card">
      <template #header>
        <span class="menu-title">
          <el-icon><Food /></el-icon>
          菜品菜单
        </span>
      </template>

      <!-- 筛选组件区域 -->
      <div class="menu-filter">
        <div class="mf-row">
          <el-input v-model="keyword" placeholder="搜索菜名…" clearable class="mf-search" />
          <el-select v-model="sortBy" placeholder="排序" clearable class="mf-sort">
            <el-option label="热量升序" value="cal-asc" />
            <el-option label="热量降序" value="cal-desc" />
            <el-option label="价格升序" value="price-asc" />
            <el-option label="价格降序" value="price-desc" />
          </el-select>
          <el-button @click="resetFilters">重置</el-button>
        </div>

        <div class="mf-row">
          <span class="mf-label">类别</span>
          <el-checkbox-group v-model="categorySel">
            <el-checkbox v-for="opt in CATEGORY_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="mf-row">
          <span class="mf-label">辣度</span>
          <el-checkbox-group v-model="spiceSel">
            <el-checkbox value="不辣">不辣</el-checkbox>
            <el-checkbox value="微辣">微辣</el-checkbox>
            <el-checkbox value="中辣">中辣</el-checkbox>
            <el-checkbox value="重辣">重辣</el-checkbox>
          </el-checkbox-group>
        </div>

        <div class="mf-row">
          <span class="mf-label">价格</span>
          <el-input-number v-model="priceMin" :min="0" :max="100" placeholder="最低" controls-position="right" class="mf-num" />
          <span class="mf-sep">-</span>
          <el-input-number v-model="priceMax" :min="0" :max="100" placeholder="最高" controls-position="right" class="mf-num" />
          <span class="mf-unit">元</span>
        </div>

        <div class="mf-row">
          <span class="mf-label">热量</span>
          <el-input-number v-model="calMin" :min="0" :max="2000" placeholder="最低" controls-position="right" class="mf-num" />
          <span class="mf-sep">-</span>
          <el-input-number v-model="calMax" :min="0" :max="2000" placeholder="最高" controls-position="right" class="mf-num" />
          <span class="mf-unit">kcal</span>
        </div>

        <div class="mf-row">
          <span class="mf-label">蛋白质</span>
          <el-input-number v-model="protMin" :min="0" :max="100" placeholder="最低" controls-position="right" class="mf-num" />
          <span class="mf-sep">-</span>
          <el-input-number v-model="protMax" :min="0" :max="100" placeholder="最高" controls-position="right" class="mf-num" />
          <span class="mf-unit">g</span>
        </div>

        <div class="mf-row">
          <span class="mf-label">脂肪</span>
          <el-input-number v-model="fatMin" :min="0" :max="100" placeholder="最低" controls-position="right" class="mf-num" />
          <span class="mf-sep">-</span>
          <el-input-number v-model="fatMax" :min="0" :max="100" placeholder="最高" controls-position="right" class="mf-num" />
          <span class="mf-unit">g</span>
        </div>

        <div class="mf-row">
          <span class="mf-label">碳水</span>
          <el-input-number v-model="carbMin" :min="0" :max="200" placeholder="最低" controls-position="right" class="mf-num" />
          <span class="mf-sep">-</span>
          <el-input-number v-model="carbMax" :min="0" :max="200" placeholder="最高" controls-position="right" class="mf-num" />
          <span class="mf-unit">g</span>
        </div>
      </div>

      <!-- 菜品卡片网格 -->
      <div v-loading="loading" class="menu-grid">
        <div v-for="d in pageData" :key="d.id" class="menu-item">
          <div class="mi-cat">{{ d.category }}</div>
          <div class="mi-name">{{ d.name }}</div>
          <div class="mi-price">¥{{ Number(d.price).toFixed(2) }}</div>
          <div class="mi-weight">每份 {{ d.serving_grams || '--' }}g</div>
          <div class="mi-nut">
            <span>{{ Number(d.calories) || 0 }} kcal</span>
            <span>· {{ Number(d.protein) || 0 }} g 蛋白质</span>
            <span>· {{ Number(d.fat) || 0 }} g 脂肪</span>
            <span>· {{ Number(d.carbs) || 0 }} g 碳水</span>
          </div>
          <div v-if="tags(d).length" class="mi-tags">
            <span v-for="tag in tags(d)" :key="tag" class="mi-tag">{{ tag }}</span>
          </div>
        </div>
        <el-empty v-if="!loading && !dishes.length" description="暂无菜品" />
      </div>

      <!-- 无匹配结果提示 -->
      <div v-if="!loading && dishes.length && !filtered.length" class="menu-empty-tip">
        没有找到符合筛选条件的菜品，请调整筛选条件
      </div>

      <div class="menu-pagination">
        <el-pagination
          background
          :current-page="page"
          :page-size="pageSize"
          :total="filtered.length"
          layout="prev, pager, next, sizes, jumper, total"
          :page-sizes="[6, 12, 18, 24]"
          @current-change="(p: number) => page = p"
          @size-change="(s: number) => { pageSize = s; page = 1 }"
        />
      </div>

      <el-button
        v-show="showBackToTop"
        class="menu-back-top"
        type="primary"
        circle
        :icon="ArrowUp"
        @click="scrollToTop"
      />
    </el-card>
  </div>
</template>

<style scoped>
.menu-page {
  max-width: 1080px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 16px;
}

.menu-card {
  border-radius: 16px;
}

/* 筛选组件区域 */
.menu-filter {
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 14px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.mf-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.mf-search {
  width: 240px;
}

.mf-sort {
  width: 130px;
}

.mf-label {
  font-size: 13px;
  color: #606266;
  white-space: nowrap;
  min-width: 44px;
}

.mf-num {
  width: 110px;
}

.mf-sep {
  color: #909399;
}

.mf-unit {
  color: #909399;
  font-size: 12px;
}

.menu-empty-tip {
  padding: 40px 0;
  text-align: center;
  color: #909399;
  font-size: 14px;
}

.menu-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #303133;
}

.menu-title .el-icon {
  color: var(--el-color-primary);
}

/* 菜品卡片网格 */
.menu-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 14px;
}

.menu-item {
  position: relative;
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 14px;
  padding: 14px 16px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s, transform 0.15s;
}

.menu-item:hover {
  box-shadow: 0 8px 20px rgba(50, 177, 108, 0.14);
  transform: translateY(-2px);
}

.mi-cat {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
}

.mi-name {
  margin-top: 10px;
  font-weight: 700;
  font-size: 16px;
  color: #303133;
  padding-right: 30px;
}

.mi-price {
  margin-top: 6px;
  color: #e6a23c;
  font-weight: 700;
  font-size: 15px;
}

.mi-weight {
  margin-top: 3px;
  font-size: 12px;
  color: #909399;
}

.mi-nut {
  margin-top: 8px;
  font-size: 12px;
  color: #606266;
  display: flex;
  gap: 8px;
}

.mi-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;
}

.mi-tag {
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 11px;
  background: #e5ecff;
  color: #2457d6;
}

.menu-pagination {
  padding: 18px 0 8px;
  text-align: center;
}

.menu-back-top {
  position: fixed;
  right: 24px;
  bottom: 84px;
  z-index: 1200;
  box-shadow: 0 6px 18px rgba(0, 0, 0, 0.12);
}
/* ===== 移动端适配 ===== */
@media (max-width: 768px) {
  .menu-page {
    padding: 10px;
  }
  .menu-card {
    border-radius: 12px;
  }
  .menu-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
  }
  .menu-filter {
    padding: 10px;
  }
  .mf-row {
    flex-wrap: wrap;
    gap: 8px;
  }
}
</style>