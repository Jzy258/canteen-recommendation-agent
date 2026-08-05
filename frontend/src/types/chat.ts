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

export type StreamEvent = StreamSessionEvent | StreamDeltaEvent | StreamDoneEvent | StreamDishesEvent

export interface ParsedDish {
  name: string
  price: number
  reason?: string
  calories?: number
  protein?: number
  carbs?: number
  fat?: number
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
  flavor_preferences: string
  health_goals: string
  /** 忌口/过敏，逗号分隔（如：不吃辣,香菜,猪肉） */
  dietary_restrictions: string
  /** 所在地区（城市），用于天气推荐 */
  region?: string
}
