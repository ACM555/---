import { expect, test } from '@playwright/test'

test('登录页展示二维码，可免注册进入东盟体验', async ({ page }) => {
  await page.goto('/#/login?from=%2F')
  const qr = page.getByRole('img', { name: '东盟跨境商事法律 AI 助手体验二维码' })
  await expect(qr).toBeVisible()
  await expect.poll(() => qr.evaluate((image: HTMLImageElement) => image.naturalWidth)).toBeGreaterThan(0)
  await expect(page.getByRole('link', { name: '下载二维码' })).toHaveAttribute('download', '东盟法律AI助手-体验二维码.png')
  await page.getByRole('button', { name: '打开体验入口' }).click()
  await expect(page).toHaveURL(/#\/experience$/)
  const guestResponse = page.waitForResponse(response => response.url().endsWith('/api/auth/guest') && response.request().method() === 'POST')
  await page.getByRole('button', { name: '开始体验' }).click()
  const result = await (await guestResponse).json()
  expect(result.data.user.role).toBe('user')
  await expect(page).toHaveURL(/#\/$/)
  await expect(page.locator('#main-content')).toBeVisible()
})

test('二维码入口和体验页在窄屏下没有横向溢出', async ({ page }) => {
  for (const width of [320, 390]) {
    await page.setViewportSize({ width, height: 844 })
    for (const route of ['/#/login', '/#/experience']) {
      await page.goto(route)
      await expect(page.getByText('老师体验入口 · 无需注册').or(page.getByText('老师扫码体验 · 无需注册'))).toBeVisible()
      expect(await page.locator('html').evaluate(element => element.scrollWidth <= element.clientWidth)).toBeTruthy()
    }
  }
})
