<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Food } from '@element-plus/icons-vue'
import { getDishes, type MenuDish } from '@/api/menu'

const dishes = ref<MenuDish[]>([])
const loading = ref(false)

// 分类 → emoji 图标（与聊天菜品卡片一致）
const CATEGORY_EMOJI: Record<string, string> = {
  荤菜: '🍖', 素菜: '🥬', 汤: '🍲', 主食: '🍚', 水果: '🍎', 饮品: '🥤',
}

function emoji(category?: string): string {
  return (category && CATEGORY_EMOJI[category]) || '🍽️'
}

// 顶部统计徽章：总数 / 价格范围 / 热量范围
const summary = computed(() => {
  if (!dishes.value.length) return null
  const prices = dishes.value.map((d) => Number(d.price) || 0)
  const cals = dishes.value.map((d) => Number(d.calories) || 0)
  return {
    total: dishes.value.length,
    priceMin: Math.min(...prices),
    priceMax: Math.max(...prices),
    calMin: Math.min(...cals),
    calMax: Math.max(...cals),
  }
})

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

onMounted(load)
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

      <!-- 顶部统计徽章 -->
      <div v-if="summary" class="menu-summary">
        <span class="ms-badge">找到 {{ summary.total }} 道</span>
        <span class="ms-badge">价格 {{ summary.priceMin.toFixed(2) }}-{{ summary.priceMax.toFixed(2) }} 元</span>
        <span class="ms-badge">热量 {{ summary.calMin }}-{{ summary.calMax }} kcal</span>
      </div>

      <!-- 菜品卡片网格 -->
      <div v-loading="loading" class="menu-grid">
        <div v-for="d in dishes" :key="d.id" class="menu-item">
          <div class="mi-cat">{{ d.category }}</div>
          <div class="mi-emoji">{{ emoji(d.category) }}</div>
          <div class="mi-name">{{ d.name }}</div>
          <div class="mi-price">¥{{ Number(d.price).toFixed(2) }}</div>
          <div class="mi-nut">
            <span>{{ Number(d.calories) || 0 }} kcal</span>
            <span>· {{ Number(d.protein) || 0 }} g 蛋白质</span>
          </div>
          <div v-if="tags(d).length" class="mi-tags">
            <span v-for="tag in tags(d)" :key="tag" class="mi-tag">{{ tag }}</span>
          </div>
        </div>
        <el-empty v-if="!loading && !dishes.length" description="暂无菜品" />
      </div>
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

/* 顶部统计徽章 */
.menu-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-bottom: 16px;
}

.ms-badge {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 13px;
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border: 1px solid var(--el-color-primary-light-7);
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

.mi-emoji {
  position: absolute;
  top: 14px;
  right: 16px;
  font-size: 24px;
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
</style>