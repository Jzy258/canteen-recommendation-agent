/**
 * JWT 解析工具（仅本地解码 payload，不验签——签名由后端校验）。
 * 用于前端在渲染前判断 token 是否过期，避免过期 token 加载页面后才被 401 踢回。
 */

/** 解码 JWT 的 payload 部分（base64url）。失败返回 null。 */
export function decodeJwtPayload(token: string): Record<string, unknown> | null {
  if (!token) return null
  const parts = token.split('.')
  if (parts.length !== 3) return null
  try {
    const payload = parts[1]
    // base64url → base64
    let b64 = payload.replace(/-/g, '+').replace(/_/g, '/')
    while (b64.length % 4 !== 0) b64 += '='
    const json = decodeURIComponent(
      atob(b64)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join(''),
    )
    return JSON.parse(json) as Record<string, unknown>
  } catch {
    return null
  }
}

/**
 * 判断 token 是否已过期。
 * - 无 token / 无法解析 → 视为无效（false 表示不有效，由调用方决定）
 * - exp 为 Unix 秒，默认预留少量缓冲避免边界抖动
 */
export function isTokenExpired(token: string, skewSeconds = 30): boolean {
  if (!token) return true
  const payload = decodeJwtPayload(token)
  if (!payload) return true
  const exp = payload.exp
  if (typeof exp !== 'number') return true
  const now = Math.floor(Date.now() / 1000)
  return now >= exp - skewSeconds
}
