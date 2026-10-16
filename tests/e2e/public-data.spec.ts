import { expect, test } from '@playwright/test'

const record = {
  applicationNumber: 'TEST001', markName: 'Asterloom Workshop', classes: ['Class 25'],
  goodsServices: ['Clothing'], goodsServicesTruncated: false, status: 'Registered',
  officialModifiedAt: '2026-10-01', fetchedAt: '2026-10-15T01:00:00Z',
  sourceUrl: 'https://data.gov.sg/api/action/datastore_search', datasetUrl: 'https://data.gov.sg/',
  licenceUrl: 'https://data.gov.sg/open-data-licence', attribution: 'Singapore Open Data Licence', isDemo: false,
}

test.beforeEach(async ({ page, request }) => {
  const response = await request.post('http://127.0.0.1:8390/api/auth/guest')
  const token = (await response.json()).data.token
  await page.addInitScript(value => localStorage.setItem('outbound_guard_token', value), token)
})

test('真实数据检索界面、翻译、关注与输入失效在桌面和移动端可用', async ({ page }) => {
  let watches: typeof record[] = []
  await page.route('**/api/trademarks/watches', route => route.fulfill({ json: { code: 0, data: watches } }))
  await page.route('**/api/trademarks/search?**', route => route.fulfill({ json: { code: 0, data: {
    query: 'Asterloom', records: [record], total: 1, offset: 0, limit: 10, hasMore: false,
    fetchedAt: record.fetchedAt, cached: false, boundary: '无结果不表示不存在冲突。',
    sourceUrl: record.datasetUrl, licenceUrl: record.licenceUrl, attribution: record.attribution,
  } } }))
  await page.route('**/api/trademarks/TEST001/watch', route => {
    watches = route.request().method() === 'POST' ? [record] : []
    return route.fulfill({ json: { code: 0, data: { watching: watches.length > 0 } } })
  })
  await page.route('**/api/trademarks/TEST001/explain', route => route.fulfill({ json: { code: 0, data: {
    applicationNumber: 'TEST001', translations: [{ field: 'status', original: 'Registered', chinese: '已注册' }],
    aiStatus: 'translated', message: 'AI 辅助翻译，未经法律审核。', provider: 'deepseek', model: 'deepseek-flash', boundary: '需人工复核',
  } } }))
  await page.goto('/#/monitoring')
  const input = page.getByRole('searchbox', { name: '新加坡商标关键词' })
  await input.fill('Asterloom')
  await page.getByRole('button', { name: '检索官方数据', exact: true }).click()
  await expect(page.getByText('Asterloom Workshop', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'AI 辅助翻译', exact: true }).click()
  await expect(page.getByText('Registered → 已注册')).toBeVisible()
  await page.getByRole('button', { name: '关注状态变化' }).click()
  await expect(page.getByText('Asterloom Workshop · TEST001', { exact: true })).toBeVisible()
  await input.fill('Cloudring')
  await expect(page.getByText('Registered → 已注册')).toHaveCount(0)
  await expect(page.getByText('Asterloom Workshop', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: '取消关注', exact: true }).click()
  await expect(page.getByText('Asterloom Workshop · TEST001', { exact: true })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBeTruthy()
})
