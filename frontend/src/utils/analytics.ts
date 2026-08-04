import { API_BASE } from '@/api/client'

/**
 * 轻量前端埋点：事件落盘到 localStorage 队列。
 * 仅当配置了 VITE_ANALYTICS_ENDPOINT 时异步批量上报后端（默认本地收集），
 * 保证埋点不阻塞业务、不抛错、无 404 噪音。
 */

export interface TrackEvent {
  event: string
  ts: number
  page?: string
  [k: string]: unknown
}

const QUEUE_KEY = 'canteen.analytics'
// 企业级：配置上报端点后启用（如 '/track'），默认本地收集
const ENDPOINT = import.meta.env.VITE_ANALYTICS_ENDPOINT || ''
const MAX_QUEUE = 200

function readQueue(): TrackEvent[] {
  try {
    const raw = localStorage.getItem(QUEUE_KEY)
    const parsed = raw ? (JSON.parse(raw) as TrackEvent[]) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

function writeQueue(q: TrackEvent[]): void {
  try {
    localStorage.setItem(QUEUE_KEY, JSON.stringify(q))
  } catch {
    // 存储满/不可用时不阻塞业务
  }
}

export function track(event: string, payload: Record<string, unknown> = {}): void {
  const item: TrackEvent = { event, ts: Date.now(), ...payload }
  const q = readQueue()
  q.push(item)
  writeQueue(q.slice(-MAX_QUEUE))
  flush()
}

export function flush(): void {
  const q = readQueue()
  if (!q.length || !ENDPOINT) return
  try {
    fetch(`${API_BASE}${ENDPOINT}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(q),
      keepalive: true,
    })
      .then((res) => {
        if (res.ok) writeQueue([])
      })
      .catch(() => {
        // 静默失败，队列保留待下次上报
      })
  } catch {
    // noop
  }
}
