import { assetPath } from '@/utils/assetPath'

export function apiBasePath() {
  return new URL(assetPath('/api'), window.location.href).pathname
}

export function deploymentStorageKey(legacyKey: string) {
  const basePath = new URL(import.meta.env.BASE_URL, window.location.href).pathname
  return basePath === '/' ? legacyKey : `asean_legal:${basePath}:${legacyKey}`
}
