import axios from 'axios'

export const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export const http = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: { 'Content-Type': 'application/json' },
})
