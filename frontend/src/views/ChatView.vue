<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { chat } from '@/api/chat'
import type { ChatMessage } from '@/types/chat'

const SESSION_KEY = 'canteen.session_id'

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const listRef = ref<HTMLElement>()

function getSessionId(): string {
  return localStorage.getItem(SESSION_KEY) || ''
}

function saveSessionId(id: string): void {
  localStorage.setItem(SESSION_KEY, id)
}

function scrollToBottom(): void {
  nextTick(() => {
    const el = listRef.value
    if (el && typeof el.scrollTo === 'function') {
      el.scrollTo({ top: el.scrollHeight })
    }
  })
}

async function send(): Promise<void> {
  const text = input.value.trim()
  if (!text) {
    ElMessage.warning('请输入要询问的内容')
    return
  }
  if (loading.value) return

  messages.value.push({ role: 'user', content: text })
  input.value = ''
  loading.value = true
  scrollToBottom()

  try {
    const res = await chat({ message: text, session_id: getSessionId() || undefined })
    saveSessionId(res.session_id)
    messages.value.push({ role: 'assistant', content: res.reply })
  } catch (e: unknown) {
    const err = e as { response?: { status?: number }; message?: string }
    ElMessage.error(
      err?.response?.status === 400
        ? '请求参数有误，请检查输入'
        : '服务暂时不可用，请稍后再试',
    )
    messages.value.push({
      role: 'assistant',
      content: '抱歉，系统处理出错，请稍后再试或换一种问法。',
    })
  } finally {
    loading.value = false
    scrollToBottom()
  }
}

function startNewSession(): void {
  localStorage.removeItem(SESSION_KEY)
  messages.value = []
}

function onEnter(): void {
  send()
}
</script>

<template>
  <div class="chat-page">
    <el-card class="chat-card" shadow="never">
      <template #header>
        <div class="chat-header">
          <span class="chat-title">食堂菜品推荐与营养分析 Agent</span>
          <el-button size="small" @click="startNewSession">新会话</el-button>
        </div>
      </template>

      <div ref="listRef" class="chat-list">
        <el-empty
          v-if="messages.length === 0"
          description="你好！我是食堂点餐参谋，可以帮你查菜品营养、按预算推荐、记录摄入。"
        />
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="chat-row"
          :class="msg.role"
        >
          <div class="chat-bubble">{{ msg.content }}</div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="input"
          type="textarea"
          :rows="2"
          placeholder="试试输入：有什么菜？ / 10块钱预算推荐几个菜 / 记录今天午餐吃了红烧肉"
          resize="none"
          @keydown.enter.exact.prevent="onEnter"
        />
        <div class="chat-actions">
          <el-button type="primary" :loading="loading" @click="send">
            发送
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.chat-page {
  max-width: 860px;
  margin: 0 auto;
  height: 100vh;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  padding: 16px;
}

.chat-card {
  display: flex;
  flex-direction: column;
  flex: 1;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-title {
  font-weight: 600;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  min-height: 0;
}

.chat-row {
  display: flex;
  margin-bottom: 12px;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-row.assistant {
  justify-content: flex-start;
}

.chat-bubble {
  max-width: 75%;
  padding: 10px 14px;
  border-radius: 10px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-row.user .chat-bubble {
  background: #409eff;
  color: #fff;
}

.chat-row.assistant .chat-bubble {
  background: #f0f2f5;
  color: #303133;
}

.chat-input {
  border-top: 1px solid #e4e7ed;
  padding-top: 12px;
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 8px;
}
</style>
