<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { chat, chatStream } from '@/api/chat'
import type { ChatMessage } from '@/types/chat'

const SESSION_KEY = 'canteen.session_id'

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const streaming = ref(false)
const listRef = ref<HTMLElement>()
let abortController: AbortController | null = null

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

function currentAssistant(): ChatMessage {
  let last = messages.value[messages.value.length - 1]
  if (!last || last.role !== 'assistant') {
    last = { role: 'assistant', content: '' }
    messages.value.push(last)
  }
  return last
}

function appendAssistant(text: string): void {
  const msg = currentAssistant()
  msg.content += text
  scrollToBottom()
}

async function sendByStream(text: string): Promise<'ok' | 'aborted' | 'failed'> {
  const sid = getSessionId() || undefined
  abortController = new AbortController()
  let succeeded = false
  try {
    await chatStream(
      { message: text, session_id: sid },
      (event) => {
        if (event.type === 'session') {
          saveSessionId(event.session_id)
        } else if (event.type === 'delta') {
          appendAssistant(event.content)
        } else if (event.type === 'done') {
          succeeded = true
        }
      },
      abortController.signal,
    )
    return succeeded ? 'ok' : 'failed'
  } catch (e: unknown) {
    if ((e as Error).name === 'AbortError') return 'aborted'
    return 'failed'
  }
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

  let status: 'ok' | 'aborted' | 'failed' = 'failed'
  streaming.value = true
  try {
    status = await sendByStream(text)
  } catch {
    status = 'failed'
  }

  // 用户中止：保留已输出内容，不追加错误文案
  if (status === 'aborted') {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant' && last.content) {
      last.content += '（已停止）'
    }
    loading.value = false
    streaming.value = false
    abortController = null
    scrollToBottom()
    return
  }

  // 流式失败：回退到非流式 /chat
  if (status === 'failed') {
    try {
      const res = await chat({ message: text, session_id: getSessionId() || undefined })
      saveSessionId(res.session_id)
      currentAssistant().content = res.reply
      status = 'ok'
    } catch (e: unknown) {
      const err = e as { response?: { status?: number } }
      if (err?.response?.status !== 400) {
        ElMessage.warning('流式通道不可用，切换为普通模式')
      }
      status = 'failed'
    }
  }

  loading.value = false
  streaming.value = false
  abortController = null
  scrollToBottom()

  if (status === 'failed') {
    const msg = currentAssistant()
    if (!msg.content) {
      msg.content = '抱歉，系统处理出错，请稍后再试或换一种问法。'
      ElMessage.error('服务暂时不可用，请稍后再试')
    }
  }
}

function stop(): void {
  abortController?.abort()
  streaming.value = false
  loading.value = false
}

function startNewSession(): void {
  if (loading.value) stop()
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
        <div v-if="streaming" class="chat-cursor">▍</div>
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
          <el-button v-if="loading" type="warning" plain @click="stop">
            停止
          </el-button>
          <el-button type="primary" :loading="loading && !streaming" @click="send">
            {{ loading && streaming ? '回复中…' : '发送' }}
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

.chat-cursor {
  padding: 10px 14px;
  color: #409eff;
  animation: blink 1s step-start infinite;
}

@keyframes blink {
  50% {
    opacity: 0;
  }
}

.chat-input {
  border-top: 1px solid #e4e7ed;
  padding-top: 12px;
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
