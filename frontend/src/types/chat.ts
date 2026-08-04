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

export type StreamEvent = StreamSessionEvent | StreamDeltaEvent | StreamDoneEvent

export interface ParsedDish {
  name: string
  price: number
  reason?: string
  calories?: number
  protein?: number
  carbs?: number
  fat?: number
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
}
