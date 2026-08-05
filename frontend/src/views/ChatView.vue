<script setup lang="ts">
import { nextTick, onActivated, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChatDotRound, Delete, Plus, User } from '@element-plus/icons-vue'
import { chat, chatStream, listSessions, getSessionMessages, deleteSession, type ChatSessionItem } from '@/api/chat'
import { parseDishes } from '@/utils/parseDishes'
import { track } from '@/utils/analytics'
import DishCard from '@/components/DishCard.vue'
import { useChatStore } from '@/stores/chat'
import { useProfileStore } from '@/stores/profile'
import type { ChatMessage } from '@/types/chat'

const chatStore = useChatStore()
const profileStore = useProfileStore()

const QUICK_PROMPTS = [
  { label: '有什么菜？', icon: '🍽️' },
  { label: '10 元预算推荐', icon: '💰' },
  { label: '记录今天午餐', icon: '📝' },
]

const messages = ref<ChatMessage[]>([])
const input = ref('')
const loading = ref(false)
const streaming = ref(false)
const listRef = ref<HTMLElement>()
let abortController: AbortController | null = null

// ---- 历史对话（v1.3） ----
const sessions = ref<ChatSessionItem[]>([])
const showHistory = ref(false)
const historyLoading = ref(false)

function buildPrompt(text: string): string {
  const prefix = profileStore.injectedPrompt
  return prefix ? `${prefix}${text}` : text
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

function nowTime(): string {
  return new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

function pushUserMessage(text: string): void {
  messages.value.push({ role: 'user', content: text, time: nowTime() })
}

function finishAssistant(): void {
  const last = messages.value[messages.value.length - 1]
  if (!last || last.role !== 'assistant') return
  if (!last.time) last.time = nowTime()
  // 结构化菜品数据（来自流式 dishes 事件）优先；否则从文本解析兜底
  if (!last.dishes?.length) last.dishes = parseDishes(last.content)
  if (last.dishes.length) {
    track('dish_expose', { count: last.dishes.length })
  }
}

function fillPrompt(text: string): void {
  input.value = text
}

function fmtSessionTime(ts: string): string {
  if (!ts) return ''
  const d = new Date(ts.replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadSessionList(): Promise<void> {
  historyLoading.value = true
  try {
    sessions.value = await listSessions()
  } catch {
    // 列表加载失败不阻塞聊天
  } finally {
    historyLoading.value = false
  }
}

async function loadHistory(): Promise<void> {
  if (!chatStore.sessionId) return
  try {
    const items = await getSessionMessages(chatStore.sessionId)
    messages.value = items.map((m) => ({
      role: m.role,
      content: m.content,
      time: m.created_at ? new Date(m.created_at.replace(' ', 'T')).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) : undefined,
    }))
    scrollToBottom()
  } catch {
    // 历史加载失败则空会话
  }
}

async function switchSession(sid: string): Promise<void> {
  if (loading.value) stop()
  chatStore.setSession(sid)
  showHistory.value = false
  await loadHistory()
}

async function removeSession(sid: string): Promise<void> {
  try {
    await ElMessageBox.confirm('确定删除该历史对话吗？', '删除会话', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await deleteSession(sid)
    sessions.value = sessions.value.filter((s) => s.session_id !== sid)
    if (chatStore.sessionId === sid) {
      chatStore.clearSession()
      messages.value = []
    }
    ElMessage.success('会话已删除')
  } catch {
    ElMessage.error('删除失败')
  }
}

async function sendByStream(text: string): Promise<'ok' | 'aborted' | 'failed'> {
  const sid = chatStore.sessionId || undefined
  const prompt = buildPrompt(text)
  abortController = new AbortController()
  let succeeded = false
  try {
    await chatStream(
      { message: prompt, session_id: sid },
      (event) => {
        if (event.type === 'session') {
          chatStore.setSession(event.session_id)
        } else if (event.type === 'delta') {
          appendAssistant(event.content)
        } else if (event.type === 'dishes') {
          // 结构化菜品数据：优先于文本解析，含完整营养信息
          const msg = currentAssistant()
          if (event.dishes?.length) {
            msg.dishes = event.dishes
          }
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

  const startedAt = Date.now()
  track('chat_send', { text })
  pushUserMessage(text)
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
      const res = await chat({ message: buildPrompt(text), session_id: chatStore.sessionId || undefined })
      chatStore.setSession(res.session_id)
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
  finishAssistant()
  track('chat_reply', { status, durationMs: Date.now() - startedAt })
  // 新会话产生后刷新历史列表
  loadSessionList()
}

function stop(): void {
  abortController?.abort()
  streaming.value = false
  loading.value = false
}

function startNewSession(): void {
  if (loading.value) stop()
  chatStore.clearSession()
  messages.value = []
}

function onEnter(): void {
  send()
}

// 页面挂载：恢复当前会话历史 + 加载历史会话列表
onMounted(async () => {
  loadSessionList()
  if (chatStore.sessionId) {
    await loadHistory()
  }
})

// keep-alive 激活：从其他标签页返回时滚动到底部，保持聊天视图
onActivated(() => {
  scrollToBottom()
})
</script>

<template>
  <div class="chat-page">
    <el-card class="chat-card" shadow="never">
      <template #header>
        <div class="chat-header">
          <div class="chat-title">
            <el-icon class="title-icon"><ChatDotRound /></el-icon>
            <span>食堂菜品推荐与营养分析 Agent</span>
          </div>
          <div class="chat-header-actions">
            <el-button size="small" @click="showHistory = !showHistory; if (showHistory) loadSessionList()">
              历史对话
            </el-button>
            <el-button size="small" @click="startNewSession">
              <el-icon style="margin-right: 4px"><Plus /></el-icon>
              新会话
            </el-button>
          </div>
        </div>
      </template>

      <!-- 历史会话列表（v1.3） -->
      <div v-if="showHistory" class="chat-history-panel">
        <div v-if="historyLoading" class="history-tip">加载中…</div>
        <template v-else-if="sessions.length">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="history-item"
            :class="{ active: s.session_id === chatStore.sessionId }"
            @click="switchSession(s.session_id)"
          >
            <div class="history-item-main">
              <div class="history-title">{{ s.title || '未命名会话' }}</div>
              <div class="history-time">{{ fmtSessionTime(s.updated_at) }}</div>
            </div>
            <el-button
              size="small"
              text
              type="danger"
              :icon="Delete"
              @click.stop="removeSession(s.session_id)"
            />
          </div>
        </template>
        <el-empty v-else description="暂无历史对话" :image-size="60" />
      </div>

      <div ref="listRef" class="chat-list">
        <!-- 欢迎引导卡（B8） -->
        <div v-if="messages.length === 0" class="chat-welcome">
          <div class="welcome-title">你好！我是食堂点餐参谋 👋</div>
          <div class="welcome-sub">
            帮你查菜品营养、按预算推荐、记录每日摄入，点下方入口或直接输入
          </div>
          <div class="welcome-cards">
            <div
              v-for="q in QUICK_PROMPTS"
              :key="q.label"
              class="welcome-card"
              @click="fillPrompt(q.label)"
            >
              <span class="welcome-icon">{{ q.icon }}</span>
              <span class="welcome-label">{{ q.label }}</span>
            </div>
          </div>
        </div>

        <!-- 消息流（B6 头像 + 时间戳） -->
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="chat-row"
          :class="msg.role"
        >
          <div v-if="msg.role === 'assistant'" class="chat-avatar assistant">🤖</div>
          <div class="chat-body">
            <div class="chat-time">{{ msg.time }}</div>
            <div class="chat-bubble">{{ msg.content }}</div>
            <div v-if="msg.dishes && msg.dishes.length" class="dish-grid">
              <DishCard v-for="d in msg.dishes" :key="d.name" :dish="d" />
            </div>
          </div>
          <div v-if="msg.role === 'user'" class="chat-avatar user">
            <el-icon :size="17"><User /></el-icon>
          </div>
        </div>

        <!-- 回复过程态（B9） -->
        <div v-if="streaming" class="chat-thinking">
          <span class="thinking-dot" />
          <span>正在思考…</span>
        </div>
      </div>

      <div class="chat-input">
        <!-- 快捷提问 chips（B7）：初始对话后才动态出现 -->
        <div v-if="messages.length > 0" class="chat-quick">
          <button
            v-for="q in QUICK_PROMPTS"
            :key="q.label"
            type="button"
            class="quick-chip"
            @click="fillPrompt(q.label)"
          >
            {{ q.label }}
          </button>
        </div>

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
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  padding: 16px;
  width: 100%;
}

.chat-card {
  display: flex;
  flex-direction: column;
  flex: 1;
  border-radius: 16px;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.chat-header-actions {
  display: flex;
  gap: 8px;
}

/* 历史会话列表（v1.3） */
.chat-history-panel {
  border-bottom: 1px solid #e4e7ed;
  max-height: 220px;
  overflow-y: auto;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.history-tip {
  color: #909399;
  font-size: 13px;
  padding: 8px;
}

.history-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;
}

.history-item:hover {
  background: var(--el-color-primary-light-9);
}

.history-item.active {
  background: var(--el-color-primary-light-8);
  border-color: var(--el-color-primary-light-6);
}

.history-item-main {
  flex: 1;
  min-width: 0;
}

.history-title {
  font-size: 13px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}

.chat-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  font-size: 16px;
}

.title-icon {
  color: var(--el-color-primary);
  font-size: 18px;
}

.chat-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  min-height: 0;
}

/* 欢迎引导卡（B8） */
.chat-welcome {
  text-align: center;
  padding: 32px 8px 16px;
}

.welcome-title {
  font-size: 18px;
  font-weight: 700;
  color: #303133;
}

.welcome-sub {
  margin: 8px 0 20px;
  color: #909399;
  font-size: 13px;
}

.welcome-cards {
  display: flex;
  justify-content: center;
  gap: 14px;
  flex-wrap: wrap;
}

.welcome-card {
  width: 150px;
  padding: 18px 12px;
  border-radius: 14px;
  border: 1px solid var(--el-color-primary-light-8);
  background: #fff;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.welcome-card:hover {
  border-color: var(--el-color-primary);
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(50, 177, 108, 0.18);
}

.welcome-icon {
  font-size: 26px;
}

.welcome-label {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

/* 消息行（B6） */
.chat-row {
  display: flex;
  margin-bottom: 16px;
  align-items: flex-end;
  gap: 10px;
}

.chat-row.user {
  justify-content: flex-end;
}

.chat-row.assistant {
  justify-content: flex-start;
}

.chat-avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.chat-avatar.assistant {
  background: var(--el-color-primary-light-9);
  border: 1px solid var(--el-color-primary-light-8);
}

.chat-avatar.user {
  background: var(--el-color-primary);
  color: #fff;
}

.chat-body {
  display: flex;
  flex-direction: column;
  max-width: 78%;
}

.chat-row.user .chat-body {
  align-items: flex-end;
}

.chat-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-bottom: 4px;
  padding: 0 4px;
}

.chat-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}

.chat-row.user .chat-bubble {
  background: linear-gradient(135deg, #32b16c, #288e56);
  color: #fff;
  border-bottom-right-radius: 4px;
}

.chat-row.assistant .chat-bubble {
  background: #f0f2f5;
  color: #303133;
  border-bottom-left-radius: 4px;
}

/* 菜品卡片网格（B5） */
.dish-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 12px;
  margin-top: 8px;
}

/* 回复过程态（B9） */
.chat-thinking {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 4px;
  color: #909399;
  font-size: 13px;
}

.thinking-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
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

/* 快捷提问 chips（B7） */
.chat-quick {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.quick-chip {
  border: 1px solid var(--el-color-primary-light-8);
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.2s;
}

.quick-chip:hover {
  background: var(--el-color-primary);
  color: #fff;
  border-color: var(--el-color-primary);
}

.chat-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 8px;
}
</style>
