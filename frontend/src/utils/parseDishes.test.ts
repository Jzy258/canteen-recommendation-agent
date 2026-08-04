import { describe, it, expect } from 'vitest'
import { parseDishes } from './parseDishes'

describe('parseDishes', () => {
  it('解析数字列表 + 加粗菜名 + 价格', () => {
    const text = `为您推荐：
1.  **宫保鸡丁** (10元)
    *   **推荐理由**：经典川菜，蛋白质25g。
2.  **花卷** (1元)
    *   **推荐理由**：实惠主食。`
    const dishes = parseDishes(text)
    expect(dishes).toHaveLength(2)
    expect(dishes[0].name).toBe('宫保鸡丁')
    expect(dishes[0].price).toBe(10)
    expect(dishes[0].reason).toContain('经典川菜')
    expect(dishes[1].name).toBe('花卷')
    expect(dishes[1].price).toBe(1)
  })

  it('解析 emoji + 加粗菜名 + 单行格式（含营养）', () => {
    const text = '🍗 **宫保鸡丁** - 10元 - 营养：蛋白质25g | 热量350kcal - 推荐理由：高蛋白'
    const dishes = parseDishes(text)
    expect(dishes).toHaveLength(1)
    expect(dishes[0].name).toBe('宫保鸡丁')
    expect(dishes[0].protein).toBe(25)
    expect(dishes[0].calories).toBe(350)
    expect(dishes[0].reason).toContain('高蛋白')
  })

  it('解析数字列表 + 菜名 + 冒号 + 行内价格', () => {
    const text = '为您推荐：\n1. 宫保鸡丁：这是一道辣味菜品，价格10元。\n2. 花卷：主食，仅1元。'
    const dishes = parseDishes(text)
    expect(dishes).toHaveLength(2)
    expect(dishes[0].name).toBe('宫保鸡丁')
    expect(dishes[0].price).toBe(10)
    expect(dishes[1].name).toBe('花卷')
    expect(dishes[1].price).toBe(1)
  })

  it('组合建议行（含 +）不误判为菜品', () => {
    const text = '1.  **宫保鸡丁** (10元)\n    *   **推荐理由**：下饭。\n组合建议：宫保鸡丁(10元) + 花卷(1元) = 11元'
    const dishes = parseDishes(text)
    expect(dishes).toHaveLength(1)
    expect(dishes[0].name).toBe('宫保鸡丁')
  })

  it('普通文本不误判', () => {
    const text = '你好！我可以帮你查菜品营养、按预算推荐、记录摄入。'
    expect(parseDishes(text)).toHaveLength(0)
  })
})
