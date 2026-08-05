import { describe, it, expect, beforeEach } from 'vitest'
import router from './index'

// 生成一个含未过期 exp 的假 JWT（payload 需可被 isTokenExpired 解析）
function validToken(): string {
  const b64 = (s: string) =>
    btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  const header = b64(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const body = b64(JSON.stringify({ sub: '1', username: 'alice', exp: Math.floor(Date.now() / 1000) + 3600 }))
  return `${header}.${body}.fakesig`
}

function login(): void {
  localStorage.setItem('canteen.auth', JSON.stringify({
    token: validToken(),
    user: { id: 1, username: 'alice', role: 'user', display_name: '' },
  }))
}

describe('router auth guard', () => {
  beforeEach(() => {
    localStorage.clear()
    // 回到首页，避免跨用例状态
    return router.push('/').catch(() => null)
  })

  it('未登录访问受保护页面被重定向到 login', async () => {
    await router.push('/trend').catch(() => null)
    expect(router.currentRoute.value.name).toBe('login')
    expect(router.currentRoute.value.query.redirect).toBe('/trend')
  })

  it('登录后受保护页面可访问', async () => {
    login()
    await router.push('/trend').catch(() => null)
    expect(router.currentRoute.value.path).toBe('/trend')
  })

  it('已登录访问 /login 被送回首页', async () => {
    login()
    await router.push('/login').catch(() => null)
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('过期 token 访问受保护页面被重定向到 login 并清除', async () => {
    const b64 = (s: string) => btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
    const expired = b64(JSON.stringify({ sub: '1', exp: Math.floor(Date.now() / 1000) - 3600 }))
    localStorage.setItem('canteen.auth', JSON.stringify({ token: `h.${expired}.s`, user: { id: 1 } }))
    await router.push('/trend').catch(() => null)
    expect(router.currentRoute.value.name).toBe('login')
    expect(localStorage.getItem('canteen.auth')).toBeNull()
  })
})
