import { http } from './client'

export interface LocationResult {
  city: string
}

/** 调用后端 IP 定位，返回当前所在城市名 */
export async function getLocation(): Promise<LocationResult> {
  const { data } = await http.get<LocationResult>('/location')
  return data
}

/** 用浏览器坐标反查城市（后端逆地理编码） */
export async function getLocationByCoords(lng: number, lat: number): Promise<LocationResult> {
  const { data } = await http.get<LocationResult>('/location', {
    params: { lng, lat },
  })
  return data
}

/** 浏览器 HTML5 定位：返回 [lng, lat]；失败/拒绝抛错 */
export function browserGeoLocation(): Promise<[number, number]> {
  return new Promise((resolve, reject) => {
    if (!('geolocation' in navigator)) {
      reject(new Error('geolocation not supported'))
      return
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve([pos.coords.longitude, pos.coords.latitude]),
      (err) => reject(new Error(`geolocation: ${err.message}`)),
      { timeout: 10000, maximumAge: 60000 },
    )
  })
}
