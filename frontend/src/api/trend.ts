import { http } from './client'
import type { TrendPoint } from '@/types/chat'

export async function getTrend(days = 7): Promise<TrendPoint[]> {
  const { data } = await http.get<TrendPoint[]>('/trend', {
    params: { days, end_date: new Date().toISOString().slice(0, 10) },
  })
  return data
}
