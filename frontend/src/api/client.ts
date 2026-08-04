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

// 请求拦截器：统一注入（预留认证 token）、请求标识
http.interceptors.request.use((config) => {
  // 企业级预留：从认证 store 注入 Authorization
  // config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截器：统一错误归一化 + 幂等 GET 网络重试
http.interceptors.response.use(
  (res) => res,
  (error: AxiosError) => {
    const config = error.config as InternalAxiosRequestConfig | undefined
    const isNetwork = !error.response && error.code !== 'ECONNABORTED'
    if (config && isNetwork && (config.__retryCount ?? 0) < MAX_RETRY && config.method === 'get') {
      config.__retryCount = (config.__retryCount ?? 0) + 1
      return http(config)
    }
    const apiErr = new Error(error.message) as ApiError
    apiErr.isApiError = true
    apiErr.apiStatus = error.response?.status ?? 0
    apiErr.apiData = error.response?.data
    apiErr.name = 'ApiError'
    return Promise.reject(apiErr)
  },
)
