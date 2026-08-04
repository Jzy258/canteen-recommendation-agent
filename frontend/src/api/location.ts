import { http } from './client'

export interface LocationResult {
  city: string
}

/** 调用后端 IP 定位，返回当前所在城市名 */
export async function getLocation(): Promise<LocationResult> {
  const { data } = await http.get<LocationResult>('/location')
  return data
}
