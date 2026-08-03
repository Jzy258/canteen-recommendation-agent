<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UserProfile } from '@/types/chat'

const PROFILE_KEY = 'canteen.profile'

const budget = ref(20)
const flavor = ref('')
const healthGoal = ref('')

const GOALS = ['高蛋白', '增肌', '控油', '控糖', '减脂']

function load(): void {
  const raw = localStorage.getItem(PROFILE_KEY)
  if (!raw) return
  try {
    const p = JSON.parse(raw) as UserProfile
    budget.value = p.budget || 20
    flavor.value = p.flavor_preferences || ''
    healthGoal.value = p.health_goals || ''
  } catch {
    // ignore corrupted profile
  }
}

function save(): void {
  const profile: UserProfile = {
    budget: budget.value,
    flavor_preferences: flavor.value,
    health_goals: healthGoal.value,
  }
  localStorage.setItem(PROFILE_KEY, JSON.stringify(profile))
  ElMessage.success('偏好已保存')
}

function reset(): void {
  localStorage.removeItem(PROFILE_KEY)
  budget.value = 20
  flavor.value = ''
  healthGoal.value = ''
  ElMessage.info('已恢复默认')
}

onMounted(load)

defineExpose({ save })
</script>

<template>
  <div class="profile-form">
    <el-form label-width="96px">
      <el-form-item label="每餐预算">
        <el-input-number v-model="budget" :min="1" :max="100" />
        <span class="unit">元</span>
      </el-form-item>

      <el-form-item label="口味偏好">
        <el-input
          v-model="flavor"
          placeholder="如：清淡,辣,甜（逗号分隔）"
          clearable
        />
      </el-form-item>

      <el-form-item label="健康目标">
        <el-select v-model="healthGoal" placeholder="选填" clearable style="width: 200px">
          <el-option v-for="g in GOALS" :key="g" :label="g" :value="g" />
        </el-select>
      </el-form-item>

      <el-form-item>
        <el-button type="primary" @click="save">保存偏好</el-button>
        <el-button @click="reset">重置</el-button>
      </el-form-item>
    </el-form>

    <el-alert
      type="info"
      :closable="false"
      show-icon
      title="提示"
      description="保存的偏好会以自然语言注入对话，例如：请按我的偏好推荐（清淡口味、控油目标、预算 20 元）。"
    />
  </div>
</template>

<style scoped>
.unit {
  margin-left: 8px;
  color: #909399;
}
</style>
