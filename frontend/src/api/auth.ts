import { http } from './client'

export interface UserInfo {
  id: number
  username: string
  role: 'admin' | 'user'
  display_name: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserInfo
}

export async function register(
  username: string,
  password: string,
  displayName = '',
): Promise<UserInfo> {
  const { data } = await http.post<AuthResponse>('/auth/register', {
    username,
    password,
    display_name: displayName,
  })
  // 注册成功后自动登录
  return data.user
}

export async function login(username: string, password: string): Promise<AuthResponse> {
  const { data } = await http.post<AuthResponse>('/auth/login', { username, password })
  return data
}

export async function fetchMe(): Promise<UserInfo> {
  const { data } = await http.get<UserInfo>('/auth/me')
  return data
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await http.post('/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}
