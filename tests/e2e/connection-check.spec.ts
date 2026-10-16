import { expect, test } from '@playwright/test'

test('诊断页检查资源并验证体验页启动，不创建游客账号', async ({ page }) => {
  let guestRequests = 0
  page.on('request', request => {
    if (request.url().endsWith('/api/auth/guest')) guestRequests += 1
  })
  await page.goto('/connection-check.html')
  await expect(page.locator('#summary')).toContainText('检测全部通过', { timeout: 45000 })
  await expect(page.locator('#results')).toContainText('通过｜主脚本下载')
  await expect(page.locator('#results')).toContainText('通过｜页面实际启动')
  expect(guestRequests).toBe(0)
})

test('脚本被拦截时展示具体失败项，而非继续显示加载中', async ({ page }) => {
  await page.route('**/src/main.tsx', route => route.fulfill({ status: 403, contentType: 'text/plain', body: 'blocked' }))
  await page.goto('/connection-check.html')
  await expect(page.locator('#summary')).toContainText('项失败', { timeout: 45000 })
  await expect(page.locator('#results')).toContainText('失败｜主脚本下载｜HTTP 403')
  await expect(page.locator('#results')).toContainText('失败｜页面实际启动｜资源加载失败')
})

test('体验页启动资源出错时提供诊断链接', async ({ page }) => {
  await page.route('**/src/main.tsx', route => route.abort())
  await page.goto('/#/experience')
  await expect(page.locator('#boot-status')).toContainText('资源加载失败')
  await expect(page.getByRole('link', { name: '打开连接诊断' })).toHaveAttribute('href', './connection-check.html')
})
