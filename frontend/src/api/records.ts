import { http } from './client'
import type { FoodRecordItem, MealRecordItem } from '@/types/chat'

export interface RecordsQuery {
  start_date?: string
  end_date?: string
  meal_time?: string
}

export interface RecordUpdate {
  date?: string
  meal_time?: string
  dish_id?: number
  portion?: number
  grams?: number
}

export async function getRecords(query: RecordsQuery = {}): Promise<MealRecordItem[]> {
  const { data } = await http.get<MealRecordItem[]>('/records', { params: query })
  return data
}

export async function updateRecord(recordId: number, body: RecordUpdate): Promise<void> {
  await http.put(`/records/${recordId}`, body)
}

export async function deleteRecord(recordId: number): Promise<void> {
  await http.delete(`/records/${recordId}`)
}

// ---- 手工饮食记录 CRUD（food_record）----

export interface FoodRecordPayload {
  date: string
  meal_time: string
  name: string
  price?: number
  calories?: number
  protein?: number
  fat?: number
  carbs?: number
  grams?: number
  recommended_grams?: number
  remark?: string
}

export async function getFoodRecords(query: RecordsQuery = {}): Promise<FoodRecordItem[]> {
  const { data } = await http.get<FoodRecordItem[]>('/food-records', { params: query })
  return data
}

export async function createFoodRecord(payload: FoodRecordPayload): Promise<{ id: number }> {
  const { data } = await http.post<{ id: number }>('/food-records', payload)
  return data
}

export async function updateFoodRecord(recordId: number, payload: Partial<FoodRecordPayload>): Promise<void> {
  await http.put(`/food-records/${recordId}`, payload)
}

export async function deleteFoodRecord(recordId: number): Promise<void> {
  await http.delete(`/food-records/${recordId}`)
}
