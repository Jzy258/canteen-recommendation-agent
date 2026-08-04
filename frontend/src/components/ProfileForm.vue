<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, FirstAidKit, Location, Sugar, Wallet } from '@element-plus/icons-vue'
import type { UserProfile } from '@/types/chat'
import { useProfileStore } from '@/stores/profile'
import { getLocation } from '@/api/location'

const profileStore = useProfileStore()

const budget = ref(profileStore.budget)
const flavor = ref(profileStore.flavor_preferences)
const healthGoal = ref(profileStore.health_goals)
const region = ref(profileStore.region)
const locating = ref(false)

const GOALS = ['高蛋白', '增肌', '控油', '控糖', '减脂']

async function locate(): Promise<void> {
  locating.value = true
  try {
    const { city } = await getLocation()
    if (city) {
      region.value = city
      ElMessage.success(`已定位到：${city}`)
    } else {
      ElMessage.warning('定位失败，请手动输入所在城市')
    }
  } catch {
    ElMessage.warning('定位失败，请手动输入所在城市')
  } finally {
    locating.value = false
  }
}

function save(): void {
  const profile: UserProfile = {
    budget: budget.value,
    flavor_preferences: flavor.value,
    health_goals: healthGoal.value,
    region: region.value,
  }
  profileStore.save(profile)
  ElMessage.success('偏好已保存')
}

function reset(): void {
  profileStore.reset()
  budget.value = profileStore.budget
  flavor.value = ''
  healthGoal.value = ''
  region.value = ''
  ElMessage.info('已恢复默认')
}

defineExpose({ save })
</script>

<template>
  <div class="profile-form">
    <div class="pf-section">
      <div class="pf-title"><el-icon><Wallet /></el-icon>每餐预算</div>
      <div class="pf-body budget-row">
        <el-slider v-model="budget" :min="1" :max="100" class="pf-slider" />
        <el-input-number v-model="budget" :min="1" :max="100" size="small" />
        <span class="unit">元</span>
      </div>
    </div>

    <div class="pf-section">
      <div class="pf-title"><el-icon><Sugar /></el-icon>口味偏好</div>
      <div class="pf-body">
        <el-input
          v-model="flavor"
          placeholder="如：清淡,辣,甜（逗号分隔）"
          clearable
        />
      </div>
    </div>

    <div class="pf-section">
      <div class="pf-title"><el-icon><FirstAidKit /></el-icon>健康目标</div>
      <div class="pf-body">
        <el-select v-model="healthGoal" placeholder="选填" clearable style="width: 220px">
          <el-option v-for="g in GOALS" :key="g" :label="g" :value="g" />
        </el-select>
      </div>
    </div>

    <div class="pf-section">
      <div class="pf-title"><el-icon><Location /></el-icon>所在地区</div>
      <div class="pf-body region-row">
        <el-input
          v-model="region"
          placeholder="如：北京 / 上海（用于天气推荐）"
          clearable
        />
        <el-button :loading="locating" @click="locate">
          <el-icon style="margin-right: 4px"><Aim /></el-icon>
          使用定位
        </el-button>
      </div>
    </div>

    <div class="pf-actions">
      <el-button type="primary" @click="save">保存偏好</el-button>
      <el-button @click="reset">重置</el-button>
    </div>

  </div>
</template>

<style scoped>
.profile-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.pf-section {
  border: 1px solid var(--el-color-primary-light-8);
  border-radius: 14px;
  padding: 16px 18px;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.pf-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: #303133;
  margin-bottom: 14px;
}

.pf-title .el-icon {
  color: var(--el-color-primary);
  font-size: 18px;
}

.pf-body.budget-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pf-slider {
  flex: 1;
}

.unit {
  color: #909399;
  white-space: nowrap;
}

.region-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.region-row .el-input {
  flex: 1;
}

.pf-actions {
  display: flex;
  gap: 10px;
}
</style>
