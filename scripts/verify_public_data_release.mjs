import { chromium, expect } from '@playwright/test'
import { mkdir, writeFile } from 'node:fs/promises'
import path from 'node:path'

const base = 'http://154.40.45.149/asean-legal/'
const artifacts = '/root/Downloads/东盟开放数据验收-20261015'
await mkdir(artifacts, { recursive: true })
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 960 } })
const page = await context.newPage()
const errors = []
page.on('pageerror', error => errors.push(error.message))
const report = { health: {}, searches: [], checks: {}, pageErrors: errors }
let cleanup

try {
  const guest = await context.request.post(base + 'api/auth/guest')
  expect(guest.ok()).toBeTruthy()
  const session = (await guest.json()).data
  const headers = { Authorization: `Bearer ${session.token}` }
  const api = async (address, options = {}) => {
    const response = await context.request.fetch(base + 'api/' + address, { headers, timeout: 150000, ...options })
    expect(response.ok(), `API ${address} status ${response.status()}`).toBeTruthy()
    return response.json()
  }
  report.health = await api('health')
  const sources = (await api('data-sources/status')).data
  const source = sources.find(item => item.name === 'IPOS 商标申请开放数据')
  expect(source.status).toBe('online')
  expect(source.recordCount).toBeGreaterThanOrEqual(25)
  expect(sources.filter(item => item.name.startsWith('IPOS 官方') || item.name === 'IPOS 商标通告').every(item => item.lastSync === '已暂停')).toBeTruthy()
  report.checks.source = source
  let selected
  for (const query of ['Cloudring', 'Asterloom', 'ventilatoren']) {
    const result = (await api('trademarks/search?q=' + encodeURIComponent(query))).data
    expect(result.isDemo).toBe(false)
    expect(result.attribution).toContain('Singapore Open Data Licence')
    expect(result.boundary).toContain('无结果不表示不存在冲突')
    expect(result.records.every(record => record.isDemo === false && record.applicationNumber && record.sourceUrl.startsWith('https://data.gov.sg/'))).toBeTruthy()
    report.searches.push({ query, total: result.total, displayedRecords: result.records.length, fetchedAt: result.fetchedAt, cached: result.cached })
    if (query === 'ventilatoren') selected = result.records[0]
  }
  expect(selected?.applicationNumber).toBeTruthy()
  await api(`trademarks/${selected.applicationNumber}/watch`, { method: 'POST' })
  cleanup = () => api(`trademarks/${selected.applicationNumber}/watch`, { method: 'DELETE' })
  expect((await api('trademarks/watches')).data.some(record => record.applicationNumber === selected.applicationNumber)).toBeTruthy()
  await page.addInitScript(token => localStorage.setItem('asean_legal:/asean-legal/:outbound_guard_token', token), session.token)
  await page.goto(base + '#/monitoring')
  const input = page.getByRole('searchbox', { name: '新加坡商标关键词' })
  await input.fill('ventilatoren')
  await page.getByRole('button', { name: '检索官方数据', exact: true }).click()
  await expect(page.getByText('核对官方原始记录').first()).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, 'PC-真实商标开放数据检索.png'), fullPage: false })
  const explanationPromise = page.waitForResponse(response => response.url().endsWith('/explain'), { timeout: 150000 })
  await page.getByRole('button', { name: 'AI 辅助翻译', exact: true }).first().click()
  const explanation = (await (await explanationPromise).json()).data
  expect(explanation.aiStatus).toBe('translated')
  expect(explanation.reviewRequired).toBe(true)
  await expect(page.getByText(explanation.message, { exact: true })).toBeVisible()
  report.checks.ai = { provider: explanation.provider, model: explanation.model, aiStatus: explanation.aiStatus, originalStatus: explanation.record.status, translatedFields: explanation.translations.length }
  await page.screenshot({ path: path.join(artifacts, 'PC-官方原始字段与AI辅助翻译.png'), fullPage: false })
  await input.fill('Cloudring')
  await expect(page.getByRole('button', { name: 'AI 辅助翻译', exact: true })).toHaveCount(0)
  report.checks.inputInvalidation = true
  const assistant = await api('assistant/chat', { method: 'POST', data: { question: '新加坡商标数据查询：ventilatoren', page: '/monitoring', session_id: 'public-data-live-20261015' } })
  expect(assistant.answer_status).toBe('public_data_reference')
  expect(assistant.sources.length).toBeGreaterThan(0)
  report.checks.assistant = { status: assistant.answer_status, sourceCount: assistant.sources.length, sourceType: assistant.sources[0].source_type }
  await page.setViewportSize({ width: 390, height: 844 })
  await page.reload()
  await input.fill('ventilatoren')
  await page.getByRole('button', { name: '检索官方数据', exact: true }).click()
  await expect(page.getByText('核对官方原始记录').first()).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth + 2)).toBeTruthy()
  await page.screenshot({ path: path.join(artifacts, '移动端-真实商标检索与关注.png'), fullPage: false })
  report.checks.mobile390 = true
  await api(`trademarks/${selected.applicationNumber}/watch`, { method: 'DELETE' })
  expect((await api('trademarks/watches')).data).toHaveLength(0)
  report.checks.watchAddRemove = true
  const alerts = (await api('monitoring/alerts')).data
  expect(alerts.length).toBeGreaterThan(0)
  expect(alerts.every(alert => !alert.isDemo && alert.source === 'IPOS / data.gov.sg 开放数据')).toBeTruthy()
  report.checks.alerts = alerts.length
  expect(errors).toHaveLength(0)
  report.success = true
} finally {
  if (cleanup) await cleanup()
  await writeFile(path.join(artifacts, '线上真实数据验收.json'), JSON.stringify(report, null, 2))
  await browser.close()
}
console.log(JSON.stringify(report, null, 2))
