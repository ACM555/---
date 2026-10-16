import { randomUUID } from 'node:crypto'
import { expect, test, type Page } from '@playwright/test'

const backend = 'http://127.0.0.1:8390/api'

async function openAsGuest(page: Page) {
  await page.goto('/#/experience')
  await page.getByRole('button', { name: '开始体验' }).click()
  await expect(page).toHaveURL(/#\/$/)
  await expect(page.locator('#main-content')).toBeVisible()
}

async function selectOption(page: Page, label: string, option: string) {
  await page.getByRole('combobox', { name: label }).press('ArrowDown')
  await page.getByRole('combobox', { name: label }).fill(option)
  await expect(page.getByRole('combobox', { name: label })).toHaveValue(option)
  await page.locator('.ant-select-dropdown:visible .ant-select-item-option-content').filter({ hasText: option }).click()
}

async function openModule(page: Page, module: string) {
  await page.goto('/#/')
  await expect(page.locator('.portal-hero-cn')).toBeVisible()
  const card = page.locator('.seu-channel-card').filter({ has: page.getByText(module, { exact: true }) })
  const title = await card.getByRole('heading').innerText()
  await card.click()
  await expect(page).toHaveURL(new RegExp(`#/engineering-screening\\?module=${module}$`))
  await expect(page.locator('.ant-select-selection-item')).toContainText(title)
}

test('注册、退出、重新登录和普通用户权限隔离', async ({ page, request, isMobile }) => {
  const username = `accept_${randomUUID().slice(0, 8)}`
  const password = 'Acceptance-only-2026'
  await page.goto('/#/register')
  await page.getByLabel('用户名', { exact: true }).fill(username)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByLabel('企业/团队').fill('自动化验收团队')
  await page.getByRole('button', { name: '注册并进入系统' }).click()
  await expect(page).toHaveURL(/#\/$/)
  const token = await page.evaluate(() => localStorage.getItem('outbound_guard_token'))
  expect(token).toBeTruthy()
  const denied = await request.get(`${backend}/admin/users`, { headers: { Authorization: `Bearer ${token}` } })
  expect(denied.status()).toBe(403)
  await page.goto('/#/admin')
  await expect(page).toHaveURL(/#\/$/)
  await expect(page.locator('.portal-hero-cn')).toBeVisible()
  if (isMobile) {
    await page.getByRole('button', { name: '打开导航菜单' }).click()
    const drawer = page.locator('.mobile-nav-drawer')
    await expect(drawer).toBeVisible()
    await drawer.getByRole('button', { name: '退出当前账号' }).click()
  } else {
    await page.getByRole('button', { name: '退出登录', exact: true }).click()
  }
  await expect(page).toHaveURL(/#\/login/)
  expect((await request.get(`${backend}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })).status()).toBe(401)
  await page.getByLabel('用户名', { exact: true }).fill(username)
  await page.getByLabel('密码', { exact: true }).fill(password)
  await page.getByRole('button', { name: /^登\s*录$/ }).click()
  await expect(page).toHaveURL(/#\/$/)
  await page.reload()
  await expect(page.locator('#main-content')).toBeVisible()
})

test('主要页面、法律资料筛选和六模块入口均可用', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await openAsGuest(page)
  for (const [route, heading] of [
    ['assets', '品牌资产库'], ['reports', '报告中心'], ['monitoring', '监控预警中心'],
    ['rules', '东盟法律资料库'], ['legal-library', '东盟法律资料库'],
    ['engineering-screening', '跨境商事基础合规筛查'],
  ]) {
    await page.goto(`/#/${route}`)
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible()
  }
  await page.goto('/#/rules')
  await expect(page.getByRole('heading', { name: '东盟法律资料库', exact: true })).toBeVisible()
  const filterResponse = page.waitForResponse(response => response.url().includes('/legal/sources?') && response.url().includes('country_code=VN'))
  await selectOption(page, '国家', '越南')
  expect((await filterResponse).ok()).toBeTruthy()
  await selectOption(page, '模块', 'M2')
  await selectOption(page, '资料等级', 'B 级')
  for (const module of ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']) {
    await openModule(page, module)
  }
  expect(errors).toEqual([])
})

test('六模块筛查保留模块范围并在资料不足时安全返回', async ({ page }) => {
  await openAsGuest(page)
  for (const module of ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']) {
    await openModule(page, module)
    await selectOption(page, '目标国家', '越南')
    await page.getByLabel('业务场景与当前阶段').fill('验收项目：正在整理材料')
    await page.getByLabel('已知事实与待核对材料').fill('合同、投资、运输与争议资料均需核验')
    const replyPromise = page.waitForResponse(response => response.url().endsWith('/assistant/chat'))
    await page.getByRole('button', { name: '生成核验清单' }).click()
    const response = await replyPromise
    expect(response.ok(), await response.text()).toBeTruthy()
    expect(response.request().postDataJSON().question).toContain(`${module} 模块`)
    const reply = await response.json()
    expect(reply.answer_status).toBe('human_review_required')
    expect(reply.facts_to_confirm.length).toBeGreaterThan(0)
    await expect(page.getByText('当前没有匹配的已审核资料', { exact: true })).toBeVisible()
  }
})

test('筛查请求失败可重试，AI 浮窗可正常问答', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await openAsGuest(page)
  await page.goto('/#/engineering-screening?module=M2')
  await expect(page.getByRole('heading', { name: '跨境商事基础合规筛查', exact: true })).toBeVisible()
  await expect(page.locator('.ant-select-selection-item')).toContainText('跨境商事合同审查与违约风险防控')
  await selectOption(page, '目标国家', '越南')
  await page.getByLabel('业务场景与当前阶段').fill('整理合同主体资料')
  await page.route('**/api/assistant/chat', route => route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: '验收模拟服务短暂不可用' }) }))
  await page.getByRole('button', { name: '生成核验清单', exact: true }).click()
  await expect(page.getByText('筛查未完成，请重试', { exact: true })).toBeVisible()
  await page.unroute('**/api/assistant/chat')
  await page.getByRole('button', { name: '重新生成核验清单' }).click()
  await expect(page.getByRole('heading', { name: '受控风险提示' })).toBeVisible()
  await expect(page.getByText('筛查未完成，请重试', { exact: true })).toHaveCount(0)
  await page.getByRole('button', { name: '拖动或打开 AI 引导' }).click()
  const assistant = page.getByRole('complementary', { name: '合规引导助手' })
  await expect(assistant.locator('.ai-assistant__panel')).toBeInViewport({ ratio: 1 })
  await assistant.getByPlaceholder('输入你的合规问题').fill('向东盟出口设备需要核验哪些资料？')
  await expect(assistant.getByRole('button', { name: '发送问题' })).toBeInViewport({ ratio: 1 })
  await assistant.getByRole('button', { name: '发送问题' }).click()
  await expect(assistant.getByText('需人工复核', { exact: true })).toBeVisible()
  await expect(assistant).toContainText('目标国家')
  expect(errors).toEqual([])
})

test('管理员登录、系统状态和资料审核闭环', async ({ page, request }, testInfo) => {
  await page.goto('/#/login')
  await page.getByLabel('用户名', { exact: true }).fill('e2e_admin')
  await page.getByLabel('密码', { exact: true }).fill('e2e-only-not-for-production')
  await page.getByRole('button', { name: /^登\s*录$/ }).click()
  await expect(page).toHaveURL(/#\/admin$/)
  await expect(page.getByRole('heading', { name: '超级管理员控制台' })).toBeVisible()
  await expect(page.getByText('数据库在线', { exact: true })).toBeVisible()
  const token = await page.evaluate(() => localStorage.getItem('outbound_guard_token'))
  const headers = { Authorization: `Bearer ${token}` }
  const draftResponse = await request.get(`${backend}/legal/admin/sources`, { headers })
  const candidateId = testInfo.project.name === 'desktop-chromium' ? 'vn-m2-commercial-law-index-2026' : 'th-m4-labour-protection-2026'
  const candidatesResponse = await request.get(`${backend}/legal/admin/sources?approval_status=retired`, { headers })
  const drafts = [...await draftResponse.json(), ...await candidatesResponse.json()]
  const candidate = drafts.find((source: { source_id: string }) => source.source_id === candidateId)
  expect(candidate).toBeTruthy()
  const detailButton = page.getByRole('button', { name: '核验详情', exact: true }).first()
  await detailButton.click()
  await expect(page.getByText('来源溯源（审核前逐项打开核对）', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: 'Close', exact: true }).click()
  try {
    const approved = await request.post(`${backend}/legal/admin/sources/${candidate.source_id}/approval`, { headers, data: { approval_status: 'approved' } })
    expect(approved.ok(), await approved.text()).toBeTruthy()
    await page.goto('/#/rules')
    await expect(page.getByText(candidate.title, { exact: true })).toBeVisible()
    const sources = await request.get(`${backend}/legal/sources?country_code=${candidate.country_code}&legal_module=${candidate.legal_module}`, { headers })
    expect((await sources.json()).some((source: { source_id: string }) => source.source_id === candidate.source_id)).toBeTruthy()
  } finally {
    const retired = await request.post(`${backend}/legal/admin/sources/${candidate.source_id}/approval`, { headers, data: { approval_status: 'retired' } })
    expect(retired.ok()).toBeTruthy()
  }
  const removed = await request.get(`${backend}/legal/sources?country_code=${candidate.country_code}&legal_module=${candidate.legal_module}`, { headers })
  expect((await removed.json()).some((source: { source_id: string }) => source.source_id === candidate.source_id)).toBeFalsy()
})
