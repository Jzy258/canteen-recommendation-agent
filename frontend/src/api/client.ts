import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

declare module 'axios' {
  interface InternalAxiosRequestConfig {
    __retryCount?: number
  }
}

/** 归一化后的 API 错误，附带 HTTP 状态与响应体 */
export interface ApiError extends Error {
  isApiError: true
  apiStatus: number
  apiData: unknown
}

const MAX_RETRY = 2

export const http = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})

// 请求拦截器：统一注入登录 token
http.interceptors.request.use((config) => {
  try {
    // 从 localStorage 读取 token（避免循环依赖 auth store）
    const raw = localStorage.getItem('canteen.auth')
    if (raw) {
      const parsed = JSON.parse(raw)
      const token = parsed?.token
      if (token) config.headers.Authorization = `Bearer ${token}`
    }
  } catch {
    // ignore malformed storage
  }
  return config
})

// 响应拦截器：统一错误归一化 + 幂等 GET 网络重试 + 401 自动跳登录
http.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    const config = error.config as InternalAxiosRequestConfig | undefined
    const isNetwork = !error.response && error.code !== 'ECONNABORTED'
    if (config && isNetwork && (config.__retryCount ?? 0) < MAX_RETRY && config.method === 'get') {
      config.__retryCount = (config.__retryCount ?? 0) + 1
      return http(config)
    }

    // 401 未授权 / token 过期：清除登录态并跳转登录页（auth 接口本身除外，避免登录失败误跳）
    const status = error.response?.status
    const url = config?.url ?? ''
    const isAuthEndpoint = /\/auth\/(login|register|me|change-password)/.test(url)
    if (status === 401 && !isAuthEndpoint) {
      try {
        localStorage.removeItem('canteen.auth')
      } catch {
        // ignore
      }
      // 避免重复跳转（已在登录页则仅清理）
      const base = import.meta.env.BASE_URL || '/'
      if (!window.location.pathname.endsWith(`${base}login`)) {
        const redirect = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `${base}login?redirect=${redirect}`
      }
    }

    const apiErr = new Error(error.message) as ApiError
    apiErr.isApiError = true
    apiErr.apiStatus = status ?? 0
    apiErr.apiData = error.response?.data
    apiErr.name = 'ApiError'
    return Promise.reject(apiErr)
  },
)
