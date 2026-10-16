export function assetPath(path: string) {
  const basePath = new URL(import.meta.env.BASE_URL, window.location.href).pathname
  return `${basePath}${path.replace(/^\/+/, '')}`
}
