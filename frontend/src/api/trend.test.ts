import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getTrend } from './trend'

vi.mock('@/api/client', () => ({
  http: { get: vi.fn() },
}))

import { http } from '@/api/client'

const mockedGet = vi.mocked(http.get)

describe('trend api', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('调用 /trend 并透传 days 与 end_date', async () => {
    mockedGet.mockResolvedValue({
      data: [
        { date: '2026-07-28', total_calories: 0, total_protein: 0, total_carbs: 0, total_fat: 0, dish_count: 0 },
        { date: '2026-07-29', total_calories: 500, total_protein: 20, total_carbs: 10, total_fat: 35, dish_count: 1 },
      ],
    })

    const res = await getTrend(7)

    const call = mockedGet.mock.calls[0]
    const config = call[1] as { params?: { days?: number; end_date?: string } }
    expect(call[0]).toBe('/trend')
    expect(config.params?.days).toBe(7)
    expect(config.params?.end_date).toMatch(/^\d{4}-\d{2}-\d{2}$/)
    expect(res).toHaveLength(2)
    expect(res[1].total_calories).toBe(500)
  })
})
