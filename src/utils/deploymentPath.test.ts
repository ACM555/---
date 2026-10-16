import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiBasePath, deploymentStorageKey } from '@/utils/deploymentPath'
import { assetPath } from '@/utils/assetPath'

describe('deploymentPath', () => {
  beforeEach(() => vi.stubEnv('BASE_URL', './'))
  afterEach(() => {
    window.history.replaceState({}, '', '/')
    vi.unstubAllEnvs()
  })

  it('保留原端口入口的 API 路径和登录状态', () => {
    window.history.replaceState({}, '', '/#/experience')
    expect(apiBasePath()).toBe('/api')
    expect(deploymentStorageKey('outbound_guard_token')).toBe('outbound_guard_token')
    expect(assetPath('/assets/photos/cross-border-business.webp')).toBe('/assets/photos/cross-border-business.webp')
  })

  it('子路径入口将 API 请求发往东盟代理，而非其他项目', () => {
    window.history.replaceState({}, '', '/asean-legal/#/login?from=%2F')
    expect(apiBasePath()).toBe('/asean-legal/api')
    expect(assetPath('/assets/photos/cross-border-business.webp')).toBe('/asean-legal/assets/photos/cross-border-business.webp')
  })

  it('子路径入口隔离登录状态和本地审查记录', () => {
    window.history.replaceState({}, '', '/asean-legal/#/')
    for (const legacyKey of ['outbound_guard_token', 'outbound_guard_audit_history', 'outbound_guard_current_task_id']) {
      expect(deploymentStorageKey(legacyKey)).toBe(`asean_legal:/asean-legal/:${legacyKey}`)
      expect(deploymentStorageKey(legacyKey)).not.toBe(legacyKey)
    }
  })

  it('兼容明确指定的部署前缀', () => {
    vi.stubEnv('BASE_URL', '/asean-legal/')
    window.history.replaceState({}, '', '/asean-legal/#/experience')
    expect(apiBasePath()).toBe('/asean-legal/api')
    expect(deploymentStorageKey('outbound_guard_token')).toBe('asean_legal:/asean-legal/:outbound_guard_token')
  })
})
