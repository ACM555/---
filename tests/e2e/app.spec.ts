import AxeBuilder from '@axe-core/playwright'
import { expect, test, type Page } from '@playwright/test'

const fourfoldLogo = Buffer.from(
  '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',
  'base64',
)

const lowRiskLogo = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAPAAAADwCAIAAACxN37FAAAEaklEQVR4nO3dC05jRxBAUTqa/W/ZUUREJsCAsd+vb5+zASO4KrXrtc243W4vUPHX2T8AbEnQpAiaFEGTImhSBE2KoEkRNCmCJkXQpAiaFEGTImhSBE2KoEkRNCmCJkXQpAiaFEGTImhSBE2KoEkRNCmCJkXQpAiaFEGTImhSBE2KoEkRNCmCJkXQpAiaFEGTImhSBE2KoEkRNCmCZi9jjJfDCZodaz6+aUGzvd87PrhpQbOxjwUf2fSvw16JvHHGofkdE5ojaj6sdUGzgXt6PaZpQfOs+0s9oGlB85SfNrp304LmcQ/UebvdXvYkaDo1C5pUzfbQdFJ+ZULTqVnQpGoWNKmaBU2qZkGTqlnQpGq2tmPjZ9Tn1ixoIoP5jSMHnZoFTapmQZOqWdCkahY0qZoFTapma7vVjVDKr0zodY1czYJe1yjWLOhFjWjNgl7R6NYs6OWMdM2CXsuo12xtt4ox513QBwi6bywwmN84csSNlWoWdNxYrGZBl431ahZ01liyZkE3jVVrFnTQWLhma7uUsXbKr0zoCDW/EnSBmt8Ienpq/p2g56bmdwQ9MTV/JOhZqflT1nbzWecu6AMEPRmD+WuOHDNR87cEPQ0130PQc1DznQQ9ATXfT9BXp+YfEfSlqfmnrO0uSsqPMaGvSM0PE/TlqPkZgr4WNT9J0Bei5ucJ+irUvAlBX4Kat2JtdzJ3Qbcl6DMZzJtz5DiNmvcg6HOoeSeCPoGa9yPoo6l5V4I+lJr3JujjqPkA1nZHkPJhTOjdqflIgt6Xmg8m6B2p+XiC3ouaTyHoXaj5LILenppPZG23JXdBTyfozRjMV+DIsQ01X4SgN6Dm6xD0s9R8KYJ+ipqvRtCPU/MFCfpBar4ma7sfk/KVmdA/o+aLE/QPqPn6BH0vNU9B0HdR8ywE/T01T0TQ31DzXKzt/shd0BkJ+nMG86QcOT6h5nkJ+j01T03Q/6Pm2Qn6P2oOEPS/1Nwg6H+oOWP1tZ2UY5ae0GruWTdoNSctGrSaq1YMWs1hywWt5ra1glZz3rjIH+yxu5qnu8hvj0UnNHmCJkXQpAiaFEGTImhSBE3Kr9Kid7/nJpOuyRfUmdCeAtIJWs10glYznaDVTCdoNdMJWs3Mt7b7lO8FpRO0wUznyKFmOkGrmU7QaqYTtJrpBK1mOkGrmfja7gtS5uoT+n5qphO0mukErWY6QauZTtBqphO0mrni2s5dUDpBe25C58ihZjpBq5lO0GqmE7Sa6QStZjpBq5nI2s63d9KZ0GqmE7Sa6QStZlJBe0tH7cihaWpvCjVNbQ/9ddOKJ3J9VMrM+qTwY7tqZu4Jfbvd3hZ5/kEghctJrx2bzXSuj6qZ/Uz8qW/4SNCkCJoUQZMiaFKGnQMlJjQpgiZF0KQImhRBkyJoUgRNiqBJETQpgiZF0KQImhRBkyJoUgRNiqBJETQpgiZF0KQImhRBkyJoUgRNiqBJETQpgiZF0KQImhRBkyJoUgRNiqBJETQvJX8DHS2+JBhTaDcAAAAASUVORK5CYII=',
  'base64',
)

async function submitAudit(
  page: Page,
  input: {
    brandName: string
    englishName?: string
    niceClass: string
    goodsServices: string
    fileName: string
    logo: Buffer
  },
) {
  await page.goto('/submit')
  await page.getByLabel('商标名称').fill(input.brandName)
  if (input.englishName) {
    await page.getByLabel('英文名称').fill(input.englishName)
  }
  await page.getByLabel('尼斯分类').fill(input.niceClass)
  await page.getByLabel('尼斯分类').press('Enter')
  await page.getByLabel('商品或服务描述').fill(input.goodsServices)
  await page.locator('input[type="file"]').setInputFiles({
    name: input.fileName,
    mimeType: 'image/png',
    buffer: input.logo,
  })
  const auditResponsePromise = page.waitForResponse(
    (response) => response.url().endsWith('/api/audit') && response.request().method() === 'POST',
  )
  await page.getByRole('button', { name: '提交并开始审查' }).click()
  const auditResponse = await auditResponsePromise
  const submittedLogo = auditResponse.request().postDataJSON().logo as string
  expect(Buffer.from(submittedLogo, 'base64')).toEqual(input.logo)
  expect(auditResponse.ok(), await auditResponse.text()).toBeTruthy()
  await expect(page).toHaveURL(/\/reviewing\?taskId=/)
  await page.waitForURL(/\/report\/[^/]+$/, { timeout: 30000 })
}

test('完成高风险审查、报告展示和 PDF 接口验证', async ({ page, request }) => {
  await submitAudit(page, {
    brandName: '墨兰奶白',
    niceClass: '第43类-餐饮服务',
    goodsServices: '茶饮及餐饮服务',
    fileName: 'fourfold.png',
    logo: fourfoldLogo,
  })

  await expect(page.getByRole('heading', { name: '商标合规审查报告' })).toBeVisible()
  await expect(page.getByText('高危', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '下载 PDF 报告' })).toBeEnabled()

  const taskId = page.url().split('/').pop()
  const pdfResponse = await request.get(`http://127.0.0.1:8000/api/audit/report/${taskId}/pdf`)
  expect(pdfResponse.ok()).toBeTruthy()
  expect(pdfResponse.headers()['content-type']).toContain('application/pdf')
  expect((await pdfResponse.body()).subarray(0, 4).toString()).toBe('%PDF')
})

test('完成低风险审查并展示低危结论', async ({ page }) => {
  await submitAudit(page, {
    brandName: 'Mộc Lan',
    englishName: 'Moc Lan',
    niceClass: '第25类-服装鞋帽',
    goodsServices: '原创服装品牌',
    fileName: 'low-risk.png',
    logo: lowRiskLogo,
  })

  await expect(page.getByText('低危', { exact: true })).toBeVisible()
  await expect(page.getByText('可继续推进', { exact: true })).toBeVisible()
})

test('拒绝不支持的 SVG 文件', async ({ page }) => {
  await page.goto('/submit')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'unsafe.svg',
    mimeType: 'image/svg+xml',
    buffer: Buffer.from('<svg xmlns="http://www.w3.org/2000/svg"></svg>'),
  })
  await expect(page.getByText('仅支持 JPG / PNG 格式')).toBeVisible()
})

test('四档视口下首页和提交页没有页面级横向溢出', async ({ page }) => {
  for (const width of [1440, 1024, 768, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
    for (const route of ['/', '/submit']) {
      await page.goto(route)
      await expect(page.locator('#main-content')).toBeVisible()
      const hasNoOverflow = await page.locator('html').evaluate(
        (element) => element.scrollWidth <= element.clientWidth,
      )
      expect(hasNoOverflow, `${route} 在 ${width}px 下不应横向溢出`).toBeTruthy()
    }
  }
})

test('首页和提交页没有严重无障碍问题', async ({ page }) => {
  for (const route of ['/', '/submit']) {
    await page.goto(route)
    await expect(page.locator('#main-content')).toBeVisible()
    const results = await new AxeBuilder({ page }).analyze()
    const seriousViolations = results.violations.filter(
      ({ impact }) => impact === 'critical' || impact === 'serious',
    )
    expect(seriousViolations, `${route} 存在严重无障碍问题`).toEqual([])
  }
})
