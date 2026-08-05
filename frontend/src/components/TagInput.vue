<script setup lang="ts">
import { ref, watch } from 'vue'

// 通用标签输入框：输入回车添加，退格删除最后一个，× 移除单个
const props = defineProps<{
  modelValue: string[]
  placeholder?: string
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', v: string[]): void
}>()

const text = ref('')

watch(
  () => props.modelValue,
  () => {
    // 外部变化（加载/重置）时同步
    if (!text.value) return
  },
)

function add(): void {
  const item = text.value.trim()
  if (!item) return
  if (!props.modelValue.includes(item)) {
    emit('update:modelValue', [...props.modelValue, item])
  }
  text.value = ''
}

function remove(item: string): void {
  emit('update:modelValue', props.modelValue.filter((x) => x !== item))
}

function onBackspace(): void {
  if (!text.value && props.modelValue.length) {
    emit('update:modelValue', props.modelValue.slice(0, -1))
  }
}
</script>

<template>
  <div class="tag-input-wrap">
    <el-tag
      v-for="item in modelValue"
      :key="item"
      size="small"
      closable
      class="tag-input-tag"
      @close="remove(item)"
    >
      {{ item }}
    </el-tag>
    <input
      v-model="text"
      class="tag-input"
      :placeholder="placeholder || '输入后回车添加'"
      @keydown.enter.prevent="add"
      @keydown.backspace="onBackspace"
    />
  </div>
</template>

<style scoped>
.tag-input-wrap {
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

.tag-input-wrap:focus-within {
  border-color: var(--el-color-primary);
}

.tag-input-tag {
  margin: 2px 0;
}

.tag-input {
  flex: 1;
  min-width: 80px;
  border: none;
  outline: none;
  padding: 4px 2px;
  font-size: 13px;
  color: #303133;
  background: transparent;
}
</style>
