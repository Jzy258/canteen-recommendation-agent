<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { getTrend } from '@/api/trend'
import type { TrendPoint } from '@/types/chat'

const chartRef = ref<HTMLDivElement>()
const days = ref(7)
const loading = ref(false)
const trend = ref<TrendPoint[]>([])
let chart: echarts.ECharts | null = null

function renderChart(points: TrendPoint[]): void {
  if (!chartRef.value) return
  chart ??= echarts.init(chartRef.value)

  chart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['热量(kcal)', '蛋白质(g)', '碳水(g)', '脂肪(g)'] },
    grid: { left: 48, right: 24, top: 40, bottom: 32 },
    xAxis: {
      type: 'category',
      data: points.map((p) => p.date.slice(5)),
    },
    yAxis: { type: 'value' },
    series: [
      { name: '热量(kcal)', type: 'line', smooth: true, data: points.map((p) => p.total_calories) },
      { name: '蛋白质(g)', type: 'line', smooth: true, data: points.map((p) => p.total_protein) },
      { name: '碳水(g)', type: 'line', smooth: true, data: points.map((p) => p.total_carbs) },
      { name: '脂肪(g)', type: 'line', smooth: true, data: points.map((p) => p.total_fat) },
    ],
  })
}

async function load(): Promise<void> {
  loading.value = true
  try {
    trend.value = await getTrend(days.value)
    renderChart(trend.value)
  } catch {
    ElMessage.error('趋势数据加载失败，请确认后端已启动')
  } finally {
    loading.value = false
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
    <el-card shadow="never">
      <template #header>
        <div class="trend-header">
          <span class="trend-title">营养摄入趋势</span>
          <el-radio-group v-model="days" size="small" @change="load">
            <el-radio-button :value="7">近 7 天</el-radio-button>
            <el-radio-button :value="14">近 14 天</el-radio-button>
            <el-radio-button :value="30">近 30 天</el-radio-button>
          </el-radio-group>
        </div>
      </template>

      <div v-loading="loading" class="trend-chart" ref="chartRef" />

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

.trend-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trend-title {
  font-weight: 600;
}

.trend-chart {
  width: 100%;
  height: 360px;
}
</style>
