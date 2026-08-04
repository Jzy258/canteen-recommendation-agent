<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { init, graphic, use, type ECharts } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import { TrendCharts } from '@element-plus/icons-vue'
import { getTrend } from '@/api/trend'
import type { TrendPoint } from '@/types/chat'

// P0 · ECharts 按需引入：仅注册用到的图表/组件，显著降低打包体积
use([LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])

const chartRef = ref<HTMLDivElement>()
const days = ref(7)
const loading = ref(false)
const trend = ref<TrendPoint[]>([])
let chart: ECharts | null = null

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

// C11 · 图表主题美化
function renderChart(points: TrendPoint[]): void {
  if (!chartRef.value) return
  chart ??= init(chartRef.value)

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: unknown) => {
        const list = params as Array<{ marker: string; seriesName: string; value: number; axisValue: string }>
        const head = list[0] ? list[0].axisValue : ''
        return `<b>${head}</b><br/>` + list.map((x) => `${x.marker}${x.seriesName}：<b>${x.value}</b>`).join('<br/>')
      },
    },
    legend: {
      data: ['热量(kcal)', '蛋白质(g)', '碳水(g)', '脂肪(g)'],
      bottom: 8,
      left: 'center',
      itemGap: 24,
      textStyle: { color: '#606266' },
    },
    // 图例位于底部独立区域，grid 底部预留足够空间避免与图表重叠
    grid: { left: 56, right: 24, top: 32, bottom: 64 },
    xAxis: {
      type: 'category',
      data: points.map((p) => p.date.slice(5)),
      axisLabel: { color: '#909399' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#909399' },
      splitLine: { lineStyle: { color: '#f0f2f5' } },
    },
    series: [
      {
        name: '热量(kcal)',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        data: points.map((p) => p.total_calories),
        lineStyle: { width: 3, color: '#32b16c' },
        itemStyle: { color: '#32b16c' },
        areaStyle: {
          color: new graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(50,177,108,0.35)' },
            { offset: 1, color: 'rgba(50,177,108,0.02)' },
          ]),
        },
      },
      { name: '蛋白质(g)', type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, data: points.map((p) => p.total_protein), lineStyle: { width: 2, color: '#288e56' }, itemStyle: { color: '#288e56' } },
      { name: '碳水(g)', type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, data: points.map((p) => p.total_carbs), lineStyle: { width: 2, color: '#e6a23c' }, itemStyle: { color: '#e6a23c' } },
      { name: '脂肪(g)', type: 'line', smooth: true, symbol: 'circle', symbolSize: 6, data: points.map((p) => p.total_fat), lineStyle: { width: 2, color: '#f56c6c' }, itemStyle: { color: '#f56c6c' } },
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
    // 先结束加载态，等 .trend-chart 渲染后再初始化图表
    loading.value = false
    await nextTick()
    renderChart(trend.value)
  }
}

function onResize(): void {
  chart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
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

      <!-- D13 · 骨架屏加载态 -->
      <el-skeleton v-if="loading" :rows="6" animated class="trend-skeleton" />
      <div v-else class="trend-chart" ref="chartRef" />

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

.trend-chart {
  width: 100%;
  height: 360px;
}

.trend-skeleton {
  padding: 24px 12px;
}
</style>
