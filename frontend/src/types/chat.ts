export interface ChatRequest {
  message: string
  session_id?: string
}

export interface ChatResponse {
  reply: string
  session_id: string
}

export interface Dish {
  id?: number
  name: string
  calories: number
  protein: number
  carbs: number
  fat: number
  price: number
  category: string
  flavor_tags?: string
  source?: string
}

export interface StreamSessionEvent {
  type: 'session'
  session_id: string
}

export interface StreamDeltaEvent {
  type: 'delta'
  content: string
}

export interface StreamDoneEvent {
  type: 'done'
}

export interface StreamDishesEvent {
  type: 'dishes'
  dishes: ParsedDish[]
}

export interface StreamComboEvent {
  type: 'combo'
  combo: ComboMeal
}

export type StreamEvent =
  | StreamSessionEvent
  | StreamDeltaEvent
  | StreamDoneEvent
  | StreamDishesEvent
  | StreamComboEvent

export interface ParsedDish {
  name: string
  price: number
  reason?: string
  calories?: number
  protein?: number
  carbs?: number
  fat?: number
  /** 菜品类别：荤菜/素菜/汤/主食/水果/饮品（后端推荐工具返回） */
  category?: string
}

/** 组合优化结果（optimize_meal_tool 输出，用于组合卡渲染） */
export interface ComboMeal {
  dishes: ParsedDish[]
  total_price: number
  total_calories: number
  total_protein: number
  total_carbs: number
  total_fat: number
  categories: Record<string, number>
  budget: number
  calorie_limit: number
  balance_ok: boolean
  reason: string
}

/** 历史饮食记录（后端 GET /records 返回） */
export interface MealRecordItem {
  id: number
  date: string
  meal_time: string
  dish_id: number
  portion: number
  confirmed: number
  created_at: string
  dish_name: string
  calories: number
  protein: number
  carbs: number
  fat: number
  price: number
  category: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  time?: string
  dishes?: ParsedDish[]
  /** 组合优化推荐（后端 combo 事件），渲染组合卡 */
  combo?: ComboMeal
}

export interface TrendPoint {
  date: string
  total_calories: number
  total_protein: number
  total_carbs: number
  total_fat: number
  dish_count: number
}

export interface UserProfile {
  budget: number
  /** 预算下限（元/餐），v1.3 预算范围 */
  budget_min: number
  flavor_preferences: string
  health_goals: string
  /** 忌口/过敏，逗号分隔（如：不吃辣,香菜,猪肉） */
  dietary_restrictions: string
  /** 所在地区（城市），用于天气推荐 */
  region?: string
}
