import { http } from './client'
import type { MealRecordItem } from '@/types/chat'

export interface RecordsQuery {
  start_date?: string
  end_date?: string
  meal_time?: string
}

export async function getRecords(query: RecordsQuery = {}): Promise<MealRecordItem[]> {
  const { data } = await http.get<MealRecordItem[]>('/records', { params: query })
  return data
}
