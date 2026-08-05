import { describe, it, expect } from 'vitest'
import { decodeJwtPayload, isTokenExpired } from './jwt'

// 构造 JWT（payload 用 base64url，签名随意——前端只解析 payload）
function makeToken(payload: Record<string, unknown>): string {
  const b64 = (s: string) =>
    btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  const header = b64(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = b64(JSON.stringify(payload))
  return `${header}.${body}.fakesig`
}

describe('jwt utils', () => {
  it('解码 payload', () => {
    const t = makeToken({ sub: '1', username: 'alice', exp: 9999999999 })
    const p = decodeJwtPayload(t)
    expect(p?.username).toBe('alice')
    expect(p?.exp).toBe(9999999999)
  })

  it('无效 token 返回 null', () => {
    expect(decodeJwtPayload('')).toBeNull()
    expect(decodeJwtPayload('a.b')).toBeNull()
    expect(decodeJwtPayload('not-a-jwt')).toBeNull()
  })

  it('过期 token 判定为过期', () => {
    const expired = makeToken({ exp: Math.floor(Date.now() / 1000) - 3600 })
    expect(isTokenExpired(expired)).toBe(true)
  })

  it('未过期 token 判定为有效', () => {
    const future = makeToken({ exp: Math.floor(Date.now() / 1000) + 3600 })
    expect(isTokenExpired(future)).toBe(false)
  })

  it('无 token / 解析失败视为过期', () => {
    expect(isTokenExpired('')).toBe(true)
    expect(isTokenExpired('garbage')).toBe(true)
  })
})
