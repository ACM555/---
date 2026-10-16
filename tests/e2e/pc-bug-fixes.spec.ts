import { readFile } from 'node:fs/promises'
import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const backend = 'http://127.0.0.1:8390/api'
const controlledReply = {
  answer: '验收场景：仅列出资料核对事项，不作法律结论。', answer_status: 'human_review_required', sources: [],
  scope_and_preconditions: [], facts_to_confirm: ['核对申请主体及商标权属'], suggested_actions: [],
  human_review_reasons: ['正式法源尚未批准'], disclaimer: '待人工核验',
}

test.beforeEach(async ({ page, request }) => {
  const response = await request.post(`${backend}/auth/guest`)
  const token = (await response.json()).data.token as string
  await page.addInitScript(value => localStorage.setItem('outbound_guard_token', value), token)
})

async function selectOption(page: Page, label: string, option: string) {
  const input = page.getByRole('combobox', { name: label })
  await input.fill(option)
  await page.locator('.ant-select-dropdown:visible .ant-select-item-option-content').filter({ hasText: option }).click()
}

async function createCompletedTask(page: Page, request: APIRequestContext) {
  await page.goto('/#/')
  const session = await page.evaluate(() => {
    const canvas = document.createElement('canvas')
    canvas.width = 96
    canvas.height = 96
    const context = canvas.getContext('2d')!
    context.fillStyle = '#fff'
    context.fillRect(0, 0, 96, 96)
    context.fillStyle = '#2574b0'
    context.fillRect(24, 24, 48, 48)
    return { token: localStorage.getItem('outbound_guard_token'), logo: canvas.toDataURL('image/png').split(',')[1] }
  })
  const headers = { Authorization: `Bearer ${session.token}` }
  const response = await request.post(`${backend}/audit`, { headers, data: {
    brandName: '云环原创验收', englishName: 'Original Cloudring Acceptance', niceClass: '第25类-服装鞋帽',
    goodsServices: '原创几何图样服装', targetCountries: ['越南'], logo: session.logo,
  } })
  expect(response.ok(), await response.text()).toBeTruthy()
  const taskId = (await response.json()).data.taskId as string
  await expect.poll(async () => (await (await request.get(`${backend}/audit/result/${taskId}`, { headers })).json()).data.status, { timeout: 30000 }).toBe('done')
  return { taskId, headers }
}

test('移动首页的报告按钮不被浮动面板遮挡，三个窄屏均可点击', async ({ page }) => {
  for (const width of [320, 390, 640]) {
    await page.setViewportSize({ width, height: 844 })
    await page.goto('/#/')
    await page.getByRole('button', { name: '查看报告中心', exact: true }).click()
    await expect(page).toHaveURL(/#\/reports$/)
  }
})

test('筛查更换国家、模块、场景和事实均清空旧结果', async ({ page }) => {
  await page.route('**/api/assistant/chat', route => route.fulfill({ json: controlledReply }))
  await page.goto('/#/engineering-screening?module=M5')
  await selectOption(page, '目标国家', '越南')
  await page.getByLabel('业务场景与当前阶段').fill('原创服装商标资料核对')
  const regenerate = async () => {
    await page.getByRole('button', { name: '生成核验清单', exact: true }).click()
    await expect(page.getByText(controlledReply.answer, { exact: true })).toBeVisible()
    await expect(page.getByRole('button', { name: '生成核验清单', exact: true })).toHaveAttribute('aria-busy', 'false')
  }
  const verifyCleared = async () => {
    await expect(page.getByText('输入已修改，原筛查结果已清除，请重新生成核验清单。')).toBeVisible()
    await expect(page.getByText(controlledReply.answer, { exact: true })).toHaveCount(0)
    await expect(page.getByText('筛查结果：来源、待补事实与人工复核', { exact: true })).toHaveCount(0)
  }
  await regenerate()
  await selectOption(page, '目标国家', '新加坡')
  await verifyCleared()
  await regenerate()
  await expect(page.getByText('新加坡 M5 · 普通商标本国申请资料核对', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '回查官方指南原文' })).toHaveAttribute('href', 'https://www.ipos.gov.sg/about-ip/trade-marks/how-to-register/')
  await expect(page.getByText('当前没有匹配的已审核资料', { exact: true })).toBeVisible()
  await selectOption(page, '业务模块', '跨境商事合同审查与违约风险防控')
  await verifyCleared()
  await expect(page.getByText('新加坡 M5 · 普通商标本国申请资料核对', { exact: true })).toHaveCount(0)
  await regenerate()
  await page.getByLabel('业务场景与当前阶段').fill('修改后的合同履约资料核对')
  await verifyCleared()
  await regenerate()
  await page.getByLabel('已知事实与待核对材料').fill('补充主体身份及权属文件')
  await verifyCleared()
})

test('输入变化后迟到的筛查响应不能恢复旧结果', async ({ page }) => {
  let releaseResponse: () => void = () => undefined
  const gate = new Promise<void>(resolve => { releaseResponse = resolve })
  await page.route('**/api/assistant/chat', async route => {
    await gate
    await route.fulfill({ json: controlledReply })
  })
  await page.goto('/#/engineering-screening?module=M5')
  await selectOption(page, '目标国家', '越南')
  await page.getByLabel('业务场景与当前阶段').fill('初始场景')
  const started = page.waitForRequest('**/api/assistant/chat')
  await page.getByRole('button', { name: '生成核验清单', exact: true }).click()
  await started
  await page.getByLabel('业务场景与当前阶段').fill('请求期间改成另一场景')
  const responded = page.waitForResponse('**/api/assistant/chat')
  releaseResponse()
  await responded
  await expect(page.getByText('输入已修改，原筛查结果已清除，请重新生成核验清单。')).toBeVisible()
  await expect(page.getByText(controlledReply.answer, { exact: true })).toHaveCount(0)
})

test('任务菜单可进入本人已完成任务，查看与刷新不改变生成归档修改时间', async ({ page, request }) => {
  const { taskId, headers } = await createCompletedTask(page, request)
  const before = (await (await request.get(`${backend}/reports`, { headers })).json()).data.find((row: { taskId: string }) => row.taskId === taskId)
  await page.goto('/#/reviewing')
  const row = page.getByRole('row').filter({ hasText: '云环原创验收' })
  await expect(row).toBeVisible()
  await row.getByRole('button', { name: '查看进度' }).click()
  await expect(page).toHaveURL(new RegExp(`taskId=${taskId}`))
  await page.reload()
  await expect(page).toHaveURL(new RegExp(`#/report/${taskId}$`))
  await page.reload()
  await expect(page.getByText('待核验', { exact: true })).toBeVisible()
  const after = (await (await request.get(`${backend}/reports`, { headers })).json()).data.find((entry: { taskId: string }) => entry.taskId === taskId)
  for (const key of ['createdAt', 'completedAt', 'archivedAt', 'updatedAt']) expect(after[key]).toBe(before[key])
  expect(after.lastViewedAt).toBeTruthy()
})

test('报告提示空 PDF 错误、真实文件非零，并区分内部规则和官方原文', async ({ page, request }) => {
  const { taskId } = await createCompletedTask(page, request)
  await page.goto(`/#/report/${taskId}`)
  await expect(page.getByText('待核验', { exact: true })).toBeVisible()
  await page.getByRole('tab', { name: '图样辅助比对' }).click()
  await expect(page.getByText('尚未接入真实在先商标图样，不展示虚构品牌或匹配分值')).toBeVisible()
  await expect(page.getByText('对标品牌', { exact: true })).toHaveCount(0)
  await page.getByRole('tab', { name: '待补事实与建议动作' }).click()
  await expect(page.getByText(/官方原文回查入口（法律内容待审核）/).first()).toBeVisible()
  const pdfPath = `**/api/audit/report/${taskId}/pdf`
  await page.route(pdfPath, route => route.fulfill({ status: 204, body: '' }))
  await page.getByRole('button', { name: '下载完整文书' }).click()
  await expect(page.getByText('PDF 下载失败：服务器返回了空文件，请稍后重试。')).toBeVisible()
  await page.unroute(pdfPath)
  const downloaded = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载完整文书' }).click()
  const download = await downloaded
  const filePath = await download.path()
  expect(filePath).toBeTruthy()
  const bytes = await readFile(filePath!)
  expect(bytes.length).toBeGreaterThan(1000)
  expect(bytes.subarray(0, 5).toString()).toBe('%PDF-')
})
