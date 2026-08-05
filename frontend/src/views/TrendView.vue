<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onMounted, ref } from 'vue'
import { init, graphic, use, type ECharts } from 'echarts/core'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import { TrendCharts } from '@element-plus/icons-vue'
import { getTrend } from '@/api/trend'
import type { TrendPoint } from '@/types/chat'

// P0 · ECharts 按需引入：仅注册用到的图表/组件，显著降低打包体积
use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

// 两个独立图表：热量 / 蛋白质·碳水·脂肪
const calChartRef = ref<HTMLDivElement>()
const macroChartRef = ref<HTMLDivElement>()
const compareChartRef = ref<HTMLDivElement>()
const days = ref(7)
const loading = ref(false)
const trend = ref<TrendPoint[]>([])
let calChart: ECharts | null = null
let macroChart: ECharts | null = null
let compareChart: ECharts | null = null

// C10 · 汇总统计
const stats = computed(() => {
  const pts = trend.value
  const daysWithData = pts.filter((p) => p.dish_count > 0)
  const totalCal = pts.reduce((s, p) => s + p.total_calories, 0)
  const avgCal = daysWithData.length
    ? Math.round(daysWithData.reduce((s, p) => s + p.total_calories, 0) / daysWithData.length)
    : 0
  const maxDay = daysWithData.length
    ? daysWithData.reduce((a, b) => (a.total_calories >= b.total_calories ? a : b))
    : null
  return {
    totalCal: Math.round(totalCal),
    avgCal,
    maxDate: maxDay ? maxDay.date.slice(5) : '--',
    recordDays: daysWithData.length,
  }
})

// 图表实例管理：容器常驻，若 DOM 变化则销毁重建，避免空白
function ensureChart(
  refEl: HTMLDivElement | undefined,
  holder: { chart: ECharts | null },
): ECharts | null {
  if (!refEl) return holder.chart
  if (holder.chart && holder.chart.getDom() !== refEl) {
    holder.chart.dispose()
    holder.chart = null
  }
  holder.chart ??= init(refEl)
  return holder.chart
}

// 营养洞察（建议3）：基于近 N 天数据给出规则化结论，帮助用户快速理解趋势
// （纯前端规则，不依赖 LLM；后续可升级为 Agent 生成）
type InsightLevel = 'success' | 'warning' | 'danger'
const insight = computed<{ level: InsightLevel; text: string } | null>(() => {
  const pts = trend.value.filter((p) => p.dish_count > 0)
  if (!pts.length) return null
  const n = pts.length
  const avgCal = Math.round(pts.reduce((s, p) => s + p.total_calories, 0) / n)
  const avgProtein = Math.round(pts.reduce((s, p) => s + p.total_protein, 0) / n)
  const avgFat = Math.round(pts.reduce((s, p) => s + p.total_fat, 0) / n)
  if (avgProtein < 40) {
    return { level: 'warning', text: `近${n}天日均蛋白质仅 ${avgProtein}g，偏低，建议每餐搭配 1 份荤菜或豆制品。` }
  }
  if (avgFat > 65) {
    return { level: 'danger', text: `近${n}天日均脂肪 ${avgFat}g 偏高，建议多选清蒸/白灼类菜品并控制油炸。` }
  }
  if (avgCal > 2600) {
    return { level: 'warning', text: `近${n}天日均热量 ${avgCal} kcal 偏高，注意控制份量。` }
  }
  if (avgCal < 1300) {
    return { level: 'warning', text: `近${n}天日均热量 ${avgCal} kcal 偏低，注意保证基础营养摄入。` }
  }
  return { level: 'success', text: `近${n}天摄入相对均衡（日均 ${avgCal} kcal / 蛋白 ${avgProtein}g），继续保持。` }
})

function insightIcon(level: InsightLevel): string {
  return level === 'success' ? '✅' : level === 'warning' ? '⚠️' : '🔴'
}

// 公共 tooltip
function makeTooltip() {
  return {
    trigger: 'axis' as const,
    backgroundColor: 'rgba(255,255,255,0.96)',
    borderColor: '#d6efe2',
    borderWidth: 1,
    padding: [10, 14],
    textStyle: { color: '#303133', fontSize: 13 },
    axisPointer: { type: 'line' as const, lineStyle: { color: '#99d8b6', type: 'dashed' as const } },
    formatter: (params: unknown) => {
      const list = params as Array<{ marker: string; seriesName: string; value: number; axisValue: string }>
      const head = list[0] ? list[0].axisValue : ''
      const rows = list
        .map(
          (x) =>
            `<div style="display:flex;align-items:center;gap:10px;line-height:1.9">${x.marker}` +
            `<span style="flex:1;color:#606266">${x.seriesName}</span><b style="color:#303133">${x.value}</b></div>`,
        )
        .join('')
      return `<div style="font-weight:600;margin-bottom:4px">${head}</div>${rows}`
    },
  }
}

// 公共坐标系配置
function makeBase(points: TrendPoint[], legendData: string[]) {
  return {
    tooltip: makeTooltip(),
    legend: {
      data: legendData,
      bottom: 8,
      left: 'center' as const,
      itemGap: 22,
      icon: 'circle' as const,
      itemWidth: 10,
      itemHeight: 10,
      textStyle: { color: '#606266', fontSize: 12 },
    },
    // 图例位于底部独立区域，grid 底部预留足够空间避免与图表重叠
    grid: { left: 48, right: 20, top: 28, bottom: 60 },
    xAxis: {
      type: 'category' as const,
      data: points.map((p) => p.date.slice(5)),
      boundaryGap: false,
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      axisTick: { show: false },
      axisLabel: { color: '#909399', fontSize: 12 },
    },
    yAxis: {
      type: 'value' as const,
      axisLabel: { color: '#909399', fontSize: 12 },
      splitLine: { lineStyle: { color: '#f0f2f5', type: 'dashed' as const } },
      axisLine: { show: false },
    },
  }
}

function hexToRgb(hex: string): string {
  const n = parseInt(hex.replace('#', ''), 16)
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`
}

function areaGradient(color: string, alpha: number) {
  return new graphic.LinearGradient(0, 0, 0, 1, [
    { offset: 0, color: `rgba(${hexToRgb(color)},${alpha})` },
    { offset: 1, color: `rgba(${hexToRgb(color)},0.02)` },
  ])
}

// C11 · 图表一：仅热量趋势
function renderCalChart(points: TrendPoint[]): void {
  const chart = ensureChart(calChartRef.value, { chart: calChart })
  if (!chart) return
  calChart = chart
  const calColor = '#32b16c'
  chart.setOption({
    ...makeBase(points, ['热量(kcal)']),
    series: [
      {
        name: '热量(kcal)',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        showSymbol: points.length <= 14,
        data: points.map((p) => p.total_calories),
        lineStyle: { width: 3, color: calColor },
        itemStyle: { color: calColor, borderColor: '#fff', borderWidth: 2 },
        areaStyle: { color: areaGradient(calColor, 0.32) },
      },
    ],
  })
}

// C11 · 图表二：蛋白质 / 碳水 / 脂肪
function renderMacroChart(points: TrendPoint[]): void {
  const chart = ensureChart(macroChartRef.value, { chart: macroChart })
  if (!chart) return
  macroChart = chart
  const series = [
    { name: '蛋白质(g)', key: 'total_protein' as const, color: '#288e56', alpha: 0.2 },
    { name: '碳水(g)', key: 'total_carbs' as const, color: '#e6a23c', alpha: 0.18 },
    { name: '脂肪(g)', key: 'total_fat' as const, color: '#f56c6c', alpha: 0.16 },
  ]
  chart.setOption({
    ...makeBase(points, series.map((s) => s.name)),
    series: series.map((s) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 6,
      data: points.map((p) => p[s.key]),
      lineStyle: { width: 2.5, color: s.color },
      itemStyle: { color: s.color },
      areaStyle: { color: areaGradient(s.color, s.alpha) },
    })),
  })
}

// 建议6：近 N 天各营养日均 vs 目标 —— 横向条形图（一眼看出营养是否达标）
function renderCompareChart(points: TrendPoint[]): void {
  const chart = ensureChart(compareChartRef.value, { chart: compareChart })
  if (!chart) return
  compareChart = chart
  const pts = points.filter((p) => p.dish_count > 0)
  const n = pts.length || 1
  const avg = (key: 'total_calories' | 'total_protein' | 'total_carbs' | 'total_fat'): number =>
    Math.round(pts.reduce((s, p) => s + (p[key] || 0), 0) / n)
  // 一份均衡食堂餐的近似目标值（可按需调整）
  const items = [
    { name: '热量(kcal)', value: avg('total_calories'), target: 2000, color: '#32b16c' },
    { name: '蛋白质(g)', value: avg('total_protein'), target: 60, color: '#288e56' },
    { name: '碳水(g)', value: avg('total_carbs'), target: 260, color: '#e6a23c' },
    { name: '脂肪(g)', value: avg('total_fat'), target: 60, color: '#f56c6c' },
  ]
  chart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: {
      data: ['日均摄入', '目标参考'],
      bottom: 4, left: 'center',
      icon: 'circle', itemWidth: 10, itemHeight: 10,
      textStyle: { color: '#606266', fontSize: 12 },
    },
    grid: { left: 96, right: 52, top: 16, bottom: 44 },
    xAxis: {
      type: 'value',
      axisLabel: { color: '#909399', fontSize: 12 },
      splitLine: { lineStyle: { color: '#f0f2f5', type: 'dashed' } },
    },
    yAxis: {
      type: 'category',
      data: items.map((i) => i.name),
      axisLabel: { color: '#606266', fontSize: 12 },
    },
    series: [
      {
        name: '日均摄入',
        type: 'bar',
        barWidth: 14,
        data: items.map((i) => ({ value: i.value, itemStyle: { color: i.color, borderRadius: [0, 4, 4, 0] } })),
        label: { show: true, position: 'right', color: '#606266', fontSize: 11 },
      },
      {
        name: '目标参考',
        type: 'bar',
        barWidth: 14,
        data: items.map((i) => i.target),
        itemStyle: { color: '#eef0f3', borderRadius: [0, 4, 4, 0] },
      },
    ],
  })
}

async function load(): Promise<void> {
  loading.value = true
  try {
    trend.value = await getTrend(days.value)
  } catch {
    ElMessage.error('趋势数据加载失败，请确认后端已启动')
  } finally {
    // 先结束加载态，等图表容器渲染后再初始化两个图表
    loading.value = false
    await nextTick()
    renderCalChart(trend.value)
    renderMacroChart(trend.value)
    renderCompareChart(trend.value)
  }
}

function onResize(): void {
  calChart?.resize()
  macroChart?.resize()
  compareChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  calChart?.dispose()
  macroChart?.dispose()
  compareChart?.dispose()
})

// KeepAlive 激活（切回趋势页）时校正两个图表尺寸
onActivated(() => {
  calChart?.resize()
  macroChart?.resize()
  compareChart?.resize()
})
</script>
<template>
  <div class="trend-page">
    <!-- C10 · 汇总统计卡 -->
    <div v-if="!loading && trend.length && stats.recordDays > 0" class="trend-stats">
      <div class="stat-card">
        <span class="stat-label">总摄入热量</span>
        <span class="stat-value">{{ stats.totalCal }}<small> kcal</small></span>
      </div>
      <div class="stat-card">
        <span class="stat-label">日均热量</span>
        <span class="stat-value">{{ stats.avgCal }}<small> kcal</small></span>
      </div>
      <div class="stat-card">
        <span class="stat-label">最高摄入日</span>
        <span class="stat-value stat-date">{{ stats.maxDate }}</span>
      </div>
      <div class="stat-card">
        <span class="stat-label">有记录天数</span>
        <span class="stat-value">{{ stats.recordDays }}<small> 天</small></span>
      </div>
    </div>

    <el-card shadow="never" class="trend-card">
      <template #header>
        <div class="trend-header">
          <span class="trend-title">
            <el-icon><TrendCharts /></el-icon>
            营养摄入趋势
          </span>
          <el-radio-group v-model="days" size="small" @change="load">
            <el-radio-button :value="7">近 7 天</el-radio-button>
            <el-radio-button :value="14">近 14 天</el-radio-button>
            <el-radio-button :value="30">近 30 天</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <!-- 用户提示：点击属性可显示对应折线 -->
      <div class="trend-tip">
        💡 点击图例中的属性（热量 / 蛋白质 / 碳水 / 脂肪）即可显示/隐藏对应的折线
      </div>

      <!-- AI 洞察：基于近 N 天营养数据的规则化结论（建议3） -->
      <div v-if="insight" class="trend-insight" :class="insight.level">
        <span class="insight-icon">{{ insightIcon(insight.level) }}</span>
        <span>{{ insight.text }}</span>
      </div>

      <!-- 图表一：仅热量趋势 -->
      <div class="trend-chart-block">
        <div class="block-title">🔥 热量趋势</div>
        <div class="trend-chart-wrap">
          <div class="trend-chart" ref="calChartRef" />
          <el-skeleton v-if="loading" :rows="5" animated class="trend-skeleton" />
        </div>
      </div>

      <!-- 图表二：蛋白质 / 碳水 / 脂肪 -->
      <div class="trend-chart-block">
        <div class="block-title">🍗 蛋白质 / 碳水 / 脂肪</div>
        <div class="trend-chart-wrap">
          <div class="trend-chart" ref="macroChartRef" />
          <el-skeleton v-if="loading" :rows="5" animated class="trend-skeleton" />
        </div>
      </div>

      <!-- 图表三：营养日均对比（建议6，横向条形图） -->
      <div class="trend-chart-block">
        <div class="block-title">📊 营养日均对比</div>
        <div class="trend-chart-wrap">
          <div class="trend-chart" ref="compareChartRef" />
          <el-skeleton v-if="loading" :rows="5" animated class="trend-skeleton" />
        </div>
      </div>

      <el-empty
        v-if="!loading && trend.length > 0 && trend.every((p) => p.dish_count === 0)"
        description="暂无摄入记录，先在对话中记录一餐吧"
      />
    </el-card>
  </div>
</template>
<style scoped>
.trend-page {
  max-width: 860px;
  width: 100%;
  box-sizing: border-box;
  margin: 0 auto;
  padding: 16px;
}

.trend-card {
  border-radius: 16px;
}

.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.trend-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  color: #303133;
}

.trend-title .el-icon {
  color: var(--el-color-primary);
}

/* 用户提示：点击图例属性可显示/隐藏对应折线 */
.trend-tip {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-7);
  border-radius: 10px;
  padding: 8px 12px;
  margin-bottom: 14px;
}

/* 营养洞察结论条（建议3） */
.trend-insight {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  line-height: 1.6;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid;
  margin-bottom: 14px;
}

.trend-insight.success {
  background: var(--el-color-success-light-9);
  border-color: var(--el-color-success-light-7);
  color: var(--el-color-success);
}

.trend-insight.warning {
  background: var(--el-color-warning-light-9);
  border-color: var(--el-color-warning-light-7);
  color: var(--el-color-warning);
}

.trend-insight.danger {
  background: var(--el-color-danger-light-9);
  border-color: var(--el-color-danger-light-7);
  color: var(--el-color-danger);
}

/* C10 · 统计卡 */
.trend-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.stat-card {
  background: #fff;
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 14px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s, transform 0.2s;
}

.stat-card:hover {
  box-shadow: 0 6px 16px rgba(50, 177, 108, 0.15);
  transform: translateY(-2px);
}

.stat-label {
  font-size: 12px;
  color: #909399;
}

.stat-value {
  font-size: 22px;
  font-weight: 700;
  color: #32b16c;
}

.stat-value small {
  font-size: 12px;
  font-weight: 400;
  color: #909399;
}

.stat-date {
  font-size: 16px;
  line-height: 30px;
}

/* 图表块：两块分隔 */
.trend-chart-block {
  margin-bottom: 18px;
}

.trend-chart-block + .trend-chart-block {
  border-top: 1px dashed var(--el-color-primary-light-8);
  padding-top: 16px;
}

.block-title {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.trend-chart-wrap {
  position: relative;
  width: 100%;
  height: 320px;
}

.trend-chart {
  width: 100%;
  height: 100%;
}

.trend-skeleton {
  position: absolute;
  inset: 0;
  padding: 24px 12px;
  background: #fff;
  z-index: 1;
}
</style>