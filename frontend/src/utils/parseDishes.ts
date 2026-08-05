import type { ParsedDish } from '@/types/chat'

/**
 * 从助手回复文本中解析推荐的菜品列表。
 * 支持常见格式，例如：
 *   1.  **宫保鸡丁** (10元)
 *       *   **推荐理由**：经典川菜……每份含蛋白质25g。
 *   2.  花卷（1元）
 * 无法识别营养信息时对应字段保持 undefined，由卡片显示 "--"。
 */

const NUTRI_RE = {
  calories: /热量[^\d]{0,8}(\d+(?:\.\d+)?)\s*(?:kcal|千卡|大卡|卡路里)/i,
  protein: /蛋白质?[^\d]{0,4}[（(]?(\d+(?:\.\d+)?)\s*g/i,
  carbs: /碳水(?:化合物)?[^\d]{0,4}[（(]?(\d+(?:\.\d+)?)\s*g/i,
  fat: /脂肪[^\d]{0,4}[（(]?(\d+(?:\.\d+)?)\s*g/i,
}

// 加粗菜名：**宫保鸡丁** 或 **宫保鸡丁(10元)**
const NAME_RE = /\*\*([^*()（）\n]+?)\*\*/
// 数字列表 + 菜名 + 冒号（如 "1. 宫保鸡丁：..."）
const PLAIN_RE = /^\s*(\d+)[.、]\s*(.+?)[:：]\s*/
// 价格：10元 / (10元) / - 10元
const PRICE_RE = /(\d+(?:\.\d+)?)\s*元/
// 理由：推荐理由：xxx
const REASON_RE = /推荐理由\s*[:：]?\s*(.+)/i

function extractNutrition(dish: ParsedDish, text: string): void {
  const pick = (re: RegExp, key: 'calories' | 'protein' | 'carbs' | 'fat') => {
    if (dish[key] !== undefined) return
    const m = text.match(re)
    if (m) dish[key] = parseFloat(m[1])
  }
  pick(NUTRI_RE.calories, 'calories')
  pick(NUTRI_RE.protein, 'protein')
  pick(NUTRI_RE.carbs, 'carbs')
  pick(NUTRI_RE.fat, 'fat')
}

/**
 * 从助手回复中解析推荐菜品列表。
 * 兼容多种常见格式：
 *   1. **宫保鸡丁** (10元)  + 下一行 * **推荐理由**：...
 *   🍗 **宫保鸡丁** - 10元 - 营养：... | 热量350kcal ... - 推荐理由：...
 *   1. 宫保鸡丁：这是一道辣味……价格10元……
 */
export function parseDishes(text: string): ParsedDish[] {
  const lines = text.split(/\r?\n/)
  const dishes: ParsedDish[] = []
  let current: ParsedDish | null = null

  for (const raw of lines) {
    const line = raw.trim()
    if (!line) continue

    const nameM = line.match(NAME_RE)
    const plainM = line.match(PLAIN_RE)
    const priceM = line.match(PRICE_RE)
    const isCombine = line.includes('+')

    // 1) 加粗菜名 + 价格（如 **宫保鸡丁** - 10元 / 1. **宫保鸡丁** (10元)）
    const isBoldItem = !!nameM && !!priceM && !isCombine
    // 2) 数字列表 + 菜名 + 冒号 + 行内含价格（如 "1. 宫保鸡丁：…价格10元"）
    const isPlainItem =
      !isBoldItem && !!plainM && !!priceM && !isCombine && !/建议|总结|搭配|注意/.test(plainM[2])
    // 3) 同一行顿号/逗号分隔的多道菜（如 "花卷(1元)、豆浆(2元)、苹果(2元)"）
    const inlineRe = /(?:^|[、，,])\s*([^、，,()（）\n]+?)\s*[（(]?\s*(\d+(?:\.\d+)?)\s*元\s*[)）]?/g
    const inlineM = line.match(inlineRe)

    if (isBoldItem || isPlainItem) {
      if (current) dishes.push(current)
      const rawName = isBoldItem ? (nameM![1] as string) : (plainM![2] as string)
      current = {
        name: rawName.replace(/[（(]\d+(?:\.\d+)?\s*元[)）]/g, '').trim(),
        price: priceM ? parseFloat(priceM[1]) : 0,
      }
      extractNutrition(current, line)
      // 理由：优先 "推荐理由："，否则取 "菜名：" 后的正文
      const reasonM = line.match(REASON_RE)
      if (reasonM) {
        current.reason = reasonM[1].trim()
      } else if (isPlainItem) {
        const sepIdx = line.search(/[:：]/)
        if (sepIdx !== -1) current.reason = line.slice(sepIdx + 1).trim()
      }
    } else if (inlineM && !isCombine) {
      // 行内多菜：逐个解析菜名 + 价格（菜名前允许有引导语，如"建议您尝尝："）
      const singleRe = /([^、，,()（）\n]+?)\s*[（(]?\s*(\d+(?:\.\d+)?)\s*元\s*[)）]?/g
      let m: RegExpExecArray | null
      while ((m = singleRe.exec(line)) !== null) {
        const rawName = m[1].trim()
        if (!rawName) continue
        const price = parseFloat(m[2])
        // 过滤引导语/说明性片段
        let cleaned = rawName.replace(
          /^.*?(建议您尝尝|尝尝|推荐您尝尝|推荐|以下是|为您推荐|建议|预算内共|共|总价|参考自|小计)/,
          '',
        )
        cleaned = cleaned.replace(/^[:：\s]+/, '').trim()
        if (!cleaned || /建议|推荐|尝尝|预算|参考自|总价|共|备注|注意|天气/.test(cleaned)) continue
        const dish: ParsedDish = { name: cleaned, price }
        extractNutrition(dish, line)
        dishes.push(dish)
      }
    } else if (current) {
      extractNutrition(current, line)
      const reasonM = line.match(REASON_RE)
      if (reasonM) {
        current.reason = current.reason ? `${current.reason} ${reasonM[1].trim()}` : reasonM[1].trim()
      } else if (/^[-*]/.test(line) && !nameM) {
        const txt = line.replace(/^[-*\s]+/, '').trim()
        if (txt && !/^(营养|热量|蛋白质|碳水|脂肪)/.test(txt)) {
          current.reason = current.reason ? `${current.reason} ${txt}` : txt
        }
      }
    }
  }

  if (current) dishes.push(current)
  return dishes
}
