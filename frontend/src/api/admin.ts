import { http } from './client'

/** 后台管理接口（/admin/*，需 admin 角色） */

export interface AdminStats {
  user_count: number
  dish_count: number
  menu_count: number
  record_count: number
  today_record_count: number
}

export interface AdminUser {
  id: number
  username: string
  role: 'admin' | 'user'
  display_name: string
  status: number
  created_at: string
  last_login_at?: string | null
}

export interface AdminDish {
  id: number
  name: string
  calories: number
  protein: number
  carbs: number
  fat: number
  price: number
  category: string
  flavor_tags: string
  source: string
  serving_grams?: number
}

// ===== 概览 =====
export async function getAdminStats(): Promise<AdminStats> {
  const { data } = await http.get<AdminStats>('/admin/stats')
  return data
}

// ===== 用户管理 =====
export async function listAdminUsers(keyword = '', limit = 50, offset = 0) {
  const { data } = await http.get<{ items: AdminUser[]; count: number }>('/admin/users', {
    params: { keyword, limit, offset },
  })
  return data
}

export async function updateAdminUser(
  userId: number,
  payload: { role?: string; status?: number; display_name?: string },
) {
  const { data } = await http.patch(`/admin/users/${userId}`, payload)
  return data
}

export async function resetUserPassword(userId: number, newPassword: string): Promise<void> {
  await http.post(`/admin/users/${userId}/reset-password`, { new_password: newPassword })
}

// ===== 菜品管理 =====
export async function listAdminDishes(keyword = '', category = '', page = 1, pageSize = 50) {
  const offset = (page - 1) * pageSize
  const { data } = await http.get<{ items: AdminDish[]; total: number; count: number }>('/admin/dishes', {
    params: { keyword, category, limit: pageSize, offset },
  })
  return data
}

export interface DishPayload {
  name: string
  calories: number
  protein: number
  carbs: number
  fat: number
  price: number
  category: string
  flavor_tags: string
  source: string
}

export async function createAdminDish(payload: DishPayload) {
  const { data } = await http.post<{ id: number }>('/admin/dishes', payload)
  return data
}

export async function updateAdminDish(dishId: number, payload: Partial<DishPayload>): Promise<void> {
  await http.patch(`/admin/dishes/${dishId}`, payload)
}

export async function deleteAdminDish(dishId: number): Promise<void> {
  await http.delete(`/admin/dishes/${dishId}`)
}

// ===== Token 用量 =====
export interface AdminTokenUsageItem {
  id: number
  username: string
  display_name: string
  role: string
  status: number
  tokens: number
}

export async function getAdminTokenUsage() {
  const { data } = await http.get<{ items: AdminTokenUsageItem[]; total_tokens: number }>('/admin/token-usage')
  return data
}

// ===== 反馈管理 =====
export interface AdminFeedbackItem {
  id: number
  content: string
  contact: string
  user_id: number | null
  username: string | null
  display_name: string | null
  created_at: string
}

export async function listAdminFeedback(keyword = '', limit = 100, offset = 0) {
  const { data } = await http.get<{ items: AdminFeedbackItem[]; count: number }>('/admin/feedback', {
    params: { keyword, limit, offset },
  })
  return data
}

export async function deleteAdminFeedback(feedbackId: number): Promise<void> {
  await http.delete(`/admin/feedback/${feedbackId}`)
}
