import { http } from './client'

/** 菜单页菜品（后端 GET /dishes 返回） */
export interface MenuDish {
  id: number
  name: string
  price: number
  calories: number
  protein: number
  carbs: number
  fat: number
  category: string
  flavor_tags: string
  serving_grams?: number
}

/** 获取全部菜品（公开接口，供菜单页展示） */
export async function getDishes(): Promise<MenuDish[]> {
  const { data } = await http.get<MenuDish[]>('/dishes')
  return data
}