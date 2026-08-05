<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, FirstAidKit, Location, NoSmoking, Sugar, Wallet } from '@element-plus/icons-vue'
import type { UserProfile } from '@/types/chat'
import { useProfileStore } from '@/stores/profile'
import { getLocation, getLocationByCoords, browserGeoLocation } from '@/api/location'
import TagInput from './TagInput.vue'

const profileStore = useProfileStore()

// 预算范围 [下限, 上限]（双滑块）
const budgetRange = ref<[number, number]>([profileStore.budget_min, profileStore.budget])
const BUDGET_MIN = 1
const BUDGET_MAX = 100
const flavor = ref(profileStore.flavor_preferences)
const healthGoals = ref<string[]>(splitGoals(profileStore.health_goals))
const region = ref(profileStore.region)
const locating = ref(false)

// 口味预设（点击切换，逗号分隔存储；回车可新增自定义预设）
const FLAVOR_PRESETS = ref(['辣', '清淡', '甜', '酸', '鲜', '咸香', '孜然', '蒜香'])

function flavorList(): string[] {
  return flavor.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
}

/** 已选口味数组（只读，展示用） */
const flavorArray = computed<string[]>(() => flavorList())

// 输入框文本（回车添加到已选）
const flavorText = ref('')

/** 输入框回车：添加为已选口味，同时加入预设列表 */
function addFlavorFromInput(): void {
  const item = flavorText.value.trim()
  if (!item) return
  if (!flavorArray.value.includes(item)) {
    flavor.value = [...flavorArray.value, item].join('，')
  }
  if (!FLAVOR_PRESETS.value.includes(item)) {
    FLAVOR_PRESETS.value.push(item)
  }
  flavorText.value = ''
}

/** 移除某个已选口味 */
function removeFlavorItem(item: string): void {
  flavor.value = flavorArray.value.filter((x) => x !== item).join('，')
}

/** 输入框为空时按退格：移除最后一个已选 */
function onFlavorBackspace(): void {
  if (!flavorText.value && flavorArray.value.length) {
    flavor.value = flavorArray.value.slice(0, -1).join('，')
  }
}

function hasFlavor(fp: string): boolean {
  return flavorList().includes(fp)
}

function toggleFlavor(fp: string): void {
  const list = flavorList()
  const idx = list.indexOf(fp)
  if (idx >= 0) {
    list.splice(idx, 1)
  } else {
    list.push(fp)
  }
  flavor.value = list.join('，')
}

/** 移除预设标签：从预设列表移除，同时取消已选中状态 */
function removeFlavorPreset(fp: string): void {
  FLAVOR_PRESETS.value = FLAVOR_PRESETS.value.filter((x) => x !== fp)
  if (hasFlavor(fp)) {
    toggleFlavor(fp)
  }
}

// 已选忌口/过敏（标签输入）
const restrictions = ref<string[]>(
  (profileStore.dietary_restrictions || '')
    .split(/[,，]/)
    .map((s) => s.trim())
    .filter(Boolean),
)

/** 逗号分隔字符串 <-> 数组 */
function splitGoals(s: string): string[] {
  return (s || '').split(/[,，]/).map((g) => g.trim()).filter(Boolean)
}

// 健康目标预设（点击切换）
const GOAL_PRESETS = ref(['高蛋白', '增肌', '控油', '控糖', '减脂'])

function hasGoal(g: string): boolean {
  return healthGoals.value.includes(g)
}

function toggleGoal(g: string): void {
  const i = healthGoals.value.indexOf(g)
  if (i >= 0) healthGoals.value.splice(i, 1)
  else healthGoals.value.push(g)
}

function removeGoalPreset(g: string): void {
  GOAL_PRESETS.value = GOAL_PRESETS.value.filter((x) => x !== g)
  if (hasGoal(g)) toggleGoal(g)
}

// 忌口/过敏预设（点击切换）
const RESTRICTION_PRESETS = ref([
  '不吃辣', '不吃香菜', '不吃葱姜蒜', '不吃猪肉', '不吃牛羊肉',
  '清真', '素食', '海鲜过敏', '花生过敏', '乳糖不耐',
])

function hasRestriction(r: string): boolean {
  return restrictions.value.includes(r)
}

function toggleRestriction(r: string): void {
  const i = restrictions.value.indexOf(r)
  if (i >= 0) restrictions.value.splice(i, 1)
  else restrictions.value.push(r)
}

function removeRestrictionPreset(r: string): void {
  RESTRICTION_PRESETS.value = RESTRICTION_PRESETS.value.filter((x) => x !== r)
  if (hasRestriction(r)) toggleRestriction(r)
}

// 后端画像加载完成 / 重置后，同步到表单
watch(
  () => profileStore.profile,
  (p) => {
    budgetRange.value = [p.budget_min, p.budget]
    flavor.value = p.flavor_preferences
    healthGoals.value = splitGoals(p.health_goals)
    restrictions.value = splitGoals(p.dietary_restrictions)
    region.value = p.region || ''
  },
  { deep: true },
)

async function locate(): Promise<void> {
  locating.value = true
  try {
    // 1) IP 定位优先
    const { city } = await getLocation()
    if (city) {
      region.value = city
      ElMessage.success(`已定位到：${city}`)
      return
    }
    // 2) IP 定位失败 → 浏览器 GPS/WiFi 定位 + 逆地理编码
    try {
      const [lng, lat] = await browserGeoLocation()
      const r = await getLocationByCoords(lng, lat)
      if (r.city) {
        region.value = r.city
        ElMessage.success(`已定位到：${r.city}`)
        return
      }
    } catch {
      // 浏览器定位也失败
    }
    ElMessage.warning('自动定位失败，请手动输入所在城市')
  } catch {
    ElMessage.warning('定位失败，请手动输入所在城市')
  } finally {
    locating.value = false
  }
}

// 预算范围校验：最低 > 最高 为非法（输入框失焦 / 滑块停止拖动时触发）
const budgetError = ref(false)

function validateBudget(): void {
  budgetError.value = budgetRange.value[0] > budgetRange.value[1]
}

async function save(): Promise<void> {
  // 校验失败：禁止保存本次预算、不更新后端、保留用户当前输入，让用户自行调整
  if (budgetRange.value[0] > budgetRange.value[1]) {
    budgetError.value = true
    ElMessage.warning('请重新填写，最低预算不能高于最高预算')
    return
  }
  const profile: UserProfile = {
    budget: budgetRange.value[1],
    budget_min: budgetRange.value[0],
    flavor_preferences: flavor.value,
    health_goals: healthGoals.value.join(','),
    dietary_restrictions: [...new Set(restrictions.value)].join(','),
    region: region.value,
  }
  await profileStore.save(profile)
  ElMessage.success('偏好已保存')
}

function reset(): void {
  profileStore.reset()
  budgetRange.value = [profileStore.budget_min, profileStore.budget]
  flavor.value = ''
  healthGoals.value = []
  region.value = ''
  restrictions.value = []
  ElMessage.info('已恢复默认')
}

defineExpose({ save })
</script>

<template>
  <div class="profile-form">
    <div class="pf-section">
      <div class="pf-title"><el-icon><Wallet /></el-icon>每餐预算范围</div>
      <div class="pf-body budget-row">
        <el-slider
          v-model="budgetRange"
          range
          :min="BUDGET_MIN"
          :max="BUDGET_MAX"
          class="pf-slider"
          @change="validateBudget"
        />
      </div>
      <div class="pf-body budget-inputs">
        <span class="budget-label">最低</span>
        <el-input-number v-model="budgetRange[0]" :min="BUDGET_MIN" :max="BUDGET_MAX" size="small" @blur="validateBudget" />
        <span class="budget-sep">~</span>
        <span class="budget-label">最高</span>
        <el-input-number v-model="budgetRange[1]" :min="BUDGET_MIN" :max="BUDGET_MAX" size="small" @blur="validateBudget" />
        <span class="unit">元</span>
      </div>
      <div v-if="budgetError" class="budget-error">
        请重新填写，最低预算不能高于最高预算
      </div>
    </div>

    <div class="pf-section">
      <div class="pf-title"><el-icon><Sugar /></el-icon>口味偏好</div>
      <div class="pf-body flavor-presets">
        <el-tag
          v-for="fp in FLAVOR_PRESETS"
          :key="fp"
          :class="{ active: hasFlavor(fp) }"
          class="preset-tag"
          :type="hasFlavor(fp) ? 'primary' : 'info'"
          effect="plain"
          closable
          @click="toggleFlavor(fp)"
          @close="removeFlavorPreset(fp)"
        >
          {{ fp }}
        </el-tag>
      </div>
      <div class="pf-body">
        <div class="flavor-input-wrap">
          <template v-for="f in flavorArray" :key="f">
            <el-tag
              size="small"
              closable
              class="flavor-input-tag"
              @close="removeFlavorItem(f)"
            >
              {{ f }}
            </el-tag>
          </template>
          <input
            v-model="flavorText"
            class="flavor-input"
            placeholder="输入口味后回车添加"
            @keydown.enter.prevent="addFlavorFromInput"
            @keydown.backspace="onFlavorBackspace"
          />
        </div>
      </div>
    </div>

    <div class="pf-section">
      <div class="pf-title"><el-icon><FirstAidKit /></el-icon>健康目标</div>
      <div class="pf-body flavor-presets">
        <el-tag
          v-for="g in GOAL_PRESETS"
          :key="g"
          :class="{ active: hasGoal(g) }"
          class="preset-tag"
          :type="hasGoal(g) ? 'primary' : 'info'"
          effect="plain"
          closable
          @click="toggleGoal(g)"
          @close="removeGoalPreset(g)"
        >
          {{ g }}
        </el-tag>
      </div>
      <div class="pf-body">
        <TagInput v-model="healthGoals" placeholder="输入健康目标后回车添加，如：高蛋白、减脂" />
      </div>
    </div>

    <div class="pf-section">
      <div class="pf-title"><el-icon><NoSmoking /></el-icon>忌口 / 过敏</div>
      <div class="pf-body flavor-presets">
        <el-tag
          v-for="r in RESTRICTION_PRESETS"
          :key="r"
          :class="{ active: hasRestriction(r) }"
          class="preset-tag"
          :type="hasRestriction(r) ? 'primary' : 'info'"
          effect="plain"
          closable
          @click="toggleRestriction(r)"
          @close="removeRestrictionPreset(r)"
        >
          {{ r }}
        </el-tag>
      </div>
      <div class="pf-body">
        <TagInput v-model="restrictions" placeholder="输入忌口/过敏后回车添加，如：不吃香菜、花生过敏" />
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

/* 预算上下限输入行 */
.pf-body.budget-inputs {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  flex-wrap: wrap;
}

.budget-label {
  color: #909399;
  font-size: 12px;
  white-space: nowrap;
}

.budget-sep {
  color: #c0c4cc;
}

/* 口味预设按钮 */
.pf-body.flavor-presets {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}

.preset-tag {
  cursor: pointer;
  user-select: none;
  transition: all 0.2s;
}

.preset-tag:hover {
  transform: translateY(-1px);
}

/* 口味偏好：自定义标签输入框（模拟 el-select 外观） */
.flavor-input-wrap {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  min-height: 32px;
  padding: 2px 8px;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  background: #fff;
  transition: border-color 0.2s;
  cursor: text;
}

.flavor-input-wrap:focus-within {
  border-color: var(--el-color-primary);
}

.flavor-input-tag {
  margin: 2px 0;
}

.flavor-input {
  flex: 1;
  min-width: 80px;
  border: none;
  outline: none;
  padding: 4px 2px;
  font-size: 13px;
  color: #303133;
  background: transparent;
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
.budget-error {
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-color-danger);
}
</style>
