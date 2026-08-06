import { http } from './client'
import type { CustomDishItem } from '@/types/chat'

export interface CustomDishPayload {
  name: string
  calories?: number
  protein?: number
  carbs?: number
  fat?: number
  price?: number
  category?: string
  serving_grams?: number
}

/** 我的自定义菜品列表（后端按当前登录用户隔离） */
export async function getCustomDishes(): Promise<CustomDishItem[]> {
  const { data } = await http.get<CustomDishItem[]>('/custom-dishes')
  return data
}

export async function createCustomDish(payload: CustomDishPayload): Promise<{ id: number }> {
  const { data } = await http.post<{ id: number }>('/custom-dishes', payload)
  return data
}

export async function updateCustomDish(dishId: number, payload: Partial<CustomDishPayload>): Promise<void> {
  await http.put(`/custom-dishes/${dishId}`, payload)
}

export async function deleteCustomDish(dishId: number): Promise<void> {
  await http.delete(`/custom-dishes/${dishId}`)
}
