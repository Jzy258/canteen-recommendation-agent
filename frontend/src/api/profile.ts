import { http } from './client'

export interface BackendProfile {
  budget: number
  budget_min: number
  flavor_preferences: string
  dietary_restrictions: string
  health_goals: string
}

export async function fetchProfile(): Promise<BackendProfile> {
  const { data } = await http.get<BackendProfile>('/profile')
  return data
}

export async function saveProfile(p: {
  budget: number
  budget_min: number
  flavor_preferences: string
  dietary_restrictions: string
  health_goals: string
}): Promise<void> {
  await http.put('/profile', p)
}
