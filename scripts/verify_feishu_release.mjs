import { chromium, expect } from '@playwright/test'
import { mkdir, readFile, writeFile } from 'node:fs/promises'
import { setTimeout as delay } from 'node:timers/promises'
import path from 'node:path'

const base = process.env.ASEAN_VERIFY_URL || 'http://154.40.45.149/asean-legal/'
const artifacts = process.env.ASEAN_VERIFY_OUTPUT || '/root/Downloads/东盟飞书修复验收-20261015'
await mkdir(artifacts, { recursive: true })
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({ viewport: { width: 1440, height: 960 }, acceptDownloads: true })
const page = await context.newPage()
const pageErrors = []
page.on('pageerror', error => pageErrors.push(error.message))
const results = { checkedAt: new Date().toISOString(), base, cases: [] }

try {
  await page.goto(base + '#/experience')
  await page.getByRole('button', { name: '开始体验' }).click()
  await expect(page).toHaveURL(base + '#/')
  const storageKey = `asean_legal:${new URL(base).pathname}:outbound_guard_token`
  const token = await page.evaluate(key => localStorage.getItem(key), storageKey)
  expect(token).toBeTruthy()
  const headers = { Authorization: `Bearer ${token}` }
  const api = async (endpoint, options = {}) => {
    const response = await context.request.fetch(new URL('api/' + endpoint, base).href, { headers, ...options })
    expect(response.ok(), `${endpoint}: ${response.status()}`).toBeTruthy()
    return response.json()
  }
  results.health = await api('health')
  results.dataSources = (await api('data-sources/status')).data
  // 当前仅 data.gov.sg 的 IPOS 开放数据为在线真实接入；原 IPOS 网页采集已按条款暂停。
  const onlineSources = results.dataSources.filter(source => source.status === 'online')
  expect(onlineSources).toHaveLength(1)
  expect(onlineSources[0].name).toContain('IPOS')
  expect(new URL(onlineSources[0].sourceUrl).hostname).toBe('data.gov.sg')
  // 未接入的 11 国全量注册库必须显式标为未接入，不能冒充在线数据源。
  expect(results.dataSources.some(source => source.name.includes('11 国全量'))).toBeTruthy()
  const alerts = (await api('monitoring/alerts')).data
  expect(alerts.length).toBeGreaterThan(0)
  expect(alerts.every(alert => alert.isDemo === false && new URL(alert.sourceUrl).hostname.endsWith('.gov.sg'))).toBeTruthy()
  results.monitoring = { visibleCount: alerts.length, noDemoRecords: true, samples: alerts.slice(0, 3) }
  // 现行架构：IPOS 网页索引已按缓存/提取条款暂停对外展示，官方指针可能为空；
  // 新加坡 M5 主场景改由官方指南核对包（scenario-checklists）承载。
  results.legalPointers = await api('legal/official-pointers?country_code=SG&legal_module=M5')
  expect(results.legalPointers.every(pointer => (pointer.sourceUrl || '').startsWith('http'))).toBeTruthy()
  results.scenarioChecklists = await api('legal/scenario-checklists?country_code=SG&legal_module=M5')
  expect(results.scenarioChecklists).toHaveLength(1)
  expect(results.scenarioChecklists[0].checks.length).toBeGreaterThanOrEqual(5)
  expect(results.scenarioChecklists[0].approvalStatus).not.toBe('approved')
  const denied = await context.request.post(new URL('api/monitoring/sync', base).href, { headers })
  expect(denied.status()).toBe(403)
  await page.goto(base + '#/monitoring')
  await expect(page.getByRole('link', { name: '查看官方原文' }).first()).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, 'PC-真实官方监控.png'), fullPage: false })
  await page.goto(base + '#/rules')
  await expect(page.getByText('新加坡 M5 · 普通商标本国申请资料核对', { exact: true })).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, 'PC-新加坡官方指南核对包.png'), fullPage: false })

  const testSource = await readFile('tests/e2e/app.spec.ts', 'utf8')
  const flowerLogo = testSource.match(/const fourfoldLogo = Buffer.from\(\s*'([^']+)'/)[1]
  const plainLogo = testSource.match(/const lowRiskLogo = Buffer.from\(\s*'([^']+)'/)[1]
  const cases = [
    { name: '云环原创', englishName: 'Cloudring Original', niceClass: '第25类-服装鞋帽', goodsServices: '原创几何图样服装', logo: flowerLogo },
    { name: '松原工坊', englishName: '', niceClass: '第35类-广告销售', goodsServices: '原创工艺品零售服务', logo: plainLogo },
    { name: 'Asterloom Workshop', englishName: 'Asterloom Workshop', niceClass: '第25类-服装鞋帽', goodsServices: '原创服饰和生活用品', logo: plainLogo },
  ]
  for (const sample of cases) {
    const created = await api('audit', { method: 'POST', data: { brandName: sample.name, englishName: sample.englishName, niceClass: sample.niceClass, goodsServices: sample.goodsServices, logo: sample.logo, targetMarkets: ['越南'] } })
    const taskId = created.data.taskId
    let report
    for (let attempt = 0; attempt < 40; attempt += 1) {
      report = (await api(`audit/result/${taskId}`)).data
      if (report.status === 'done') break
      expect(report.status).not.toBe('error')
      await delay(500)
    }
    expect(report.status).toBe('done')
    expect(report.assessmentStatus).toBe('pending_verification')
    expect(report.manualReviewRequired).toBe(true)
    expect(report.references.some(reference => reference.sourceKind === 'official_pointer' && /^https?:\/\//.test(reference.sourceUrl))).toBeTruthy()
    if (sample.name === '云环原创') {
      expect(report.hitRules.some(rule => rule.ruleId === 'VN-INFO-004')).toBeTruthy()
      expect(report.riskScore).toBe(18)
    }
    const pdf = await context.request.get(new URL(`api/audit/report/${taskId}/pdf`, base).href, { headers })
    expect(pdf.ok()).toBeTruthy()
    const bytes = await pdf.body()
    expect(bytes.length).toBeGreaterThan(1000)
    expect(bytes.subarray(0, 5).toString()).toBe('%PDF-')
    await writeFile(path.join(artifacts, `${sample.name}-报告.pdf`), bytes)
    results.cases.push({ brandName: sample.name, taskId, status: report.status, assessmentStatus: report.assessmentStatus, pdfBytes: bytes.length, featureOnlyExcludedFromRisk: sample.name === '云环原创', officialReferenceCount: report.references.filter(reference => reference.sourceKind === 'official_pointer').length })
  }

  const firstTask = results.cases[0].taskId
  const before = (await api('reports')).data.find(report => report.taskId === firstTask)
  await page.goto(base + '#/reviewing')
  const row = page.getByRole('row').filter({ hasText: '云环原创' })
  await row.getByRole('button', { name: '查看进度' }).click()
  await expect(page).toHaveURL(new RegExp(`taskId=${firstTask}`))
  await page.reload()
  await expect(page).toHaveURL(base + '#/report/' + firstTask)
  await expect(page.getByText('待核验', { exact: true })).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, 'PC-原创图样待核验.png'), fullPage: false })
  await page.getByRole('tab', { name: '图样辅助比对' }).click()
  await expect(page.getByText('尚未接入真实在先商标图样，不展示虚构品牌或匹配分值')).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, 'PC-视觉特征与法律风险分离.png'), fullPage: false })
  await page.getByRole('tab', { name: '待补事实与建议动作' }).click()
  const interceptedPdf = `**/api/audit/report/${firstTask}/pdf`
  await page.route(interceptedPdf, route => route.fulfill({ status: 204, body: '' }))
  await page.getByRole('button', { name: '下载完整文书' }).click()
  await expect(page.getByText('PDF 下载失败：服务器返回了空文件，请稍后重试。')).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, 'PC-PDF失败提示.png'), fullPage: false })
  await page.unroute(interceptedPdf)
  const downloaded = page.waitForEvent('download')
  await page.getByRole('button', { name: '下载完整文书' }).click()
  await (await downloaded).saveAs(path.join(artifacts, '云环原创-浏览器下载.pdf'))
  await expect(page.getByText('PDF 下载失败：服务器返回了空文件，请稍后重试。')).toHaveCount(0, { timeout: 10000 })
  const after = (await api('reports')).data.find(report => report.taskId === firstTask)
  for (const key of ['createdAt', 'completedAt', 'archivedAt', 'updatedAt']) expect(after[key]).toBe(before[key])
  expect(after.lastViewedAt).toBeTruthy()
  results.timestamps = { before, after, stable: true }

  // antd Select 的下拉项可能被表单标签遮挡，改用 输入 + 回车 选中，避免点击被拦截。
  const selectOption = async (label, option) => {
    const combo = page.getByRole('combobox', { name: label })
    await combo.click({ force: true }).catch(() => undefined)
    await combo.fill(option)
    await page.waitForTimeout(350)
    await page.keyboard.press('Enter')
    await page.waitForTimeout(450)
  }

  await page.goto(base + '#/engineering-screening?module=M5')
  await selectOption('目标国家', '新加坡')
  await page.getByLabel('业务场景与当前阶段').fill('原创服饰商标申请前资料核对')
  await page.getByLabel('已知事实与待核对材料').fill('申请主体为企业，需核对图样、类别及官方近似检索记录')
  const assistantResponse = page.waitForResponse(response => response.url().endsWith('/api/assistant/chat') && response.request().method() === 'POST', { timeout: 120000 })
  await page.getByRole('button', { name: '生成核验清单', exact: true }).click()
  await expect(page.getByRole('button', { name: '生成核验清单', exact: true })).toHaveAttribute('aria-busy', 'false', { timeout: 120000 })
  const answerResponse = await assistantResponse
  expect(answerResponse.ok(), `筛查助手 HTTP ${answerResponse.status()}`).toBeTruthy()
  const answer = await answerResponse.json()
  // 新加坡 M5 已有已审核来源：应基于已审核资料作答，而不是无来源拒答。
  expect(answer.answer_status).toBe('source_backed')
  expect(answer.sources.length).toBeGreaterThan(0)
  results.assistant = { answerStatus: answer.answer_status, sourceCount: answer.sources.length, factsToConfirm: answer.facts_to_confirm, humanReviewReasons: answer.human_review_reasons }
  await expect(page.getByText('筛查未完成，请重试', { exact: true })).toHaveCount(0)
  await expect(page.getByText('新加坡 M5 · 普通商标本国申请资料核对', { exact: true })).toBeVisible()
  await expect(page.getByText('当前没有匹配的已审核资料', { exact: true })).toHaveCount(0)
  await page.screenshot({ path: path.join(artifacts, 'PC-筛查场景与正式审核边界.png'), fullPage: false })

  // 引导类问题不是法律问题：不能被「未明确单一目标国家」拦下，也不能走模型。
  const guide = await api('assistant/chat', { method: 'POST', data: { question: '你是谁？', page: '/', session_id: 'release-guide-' + Date.now() } })
  expect(guide.answer_status).toBe('guidance')
  expect(guide.sources).toHaveLength(0)
  expect(guide.answer).not.toContain('未明确单一目标国家')
  expect(guide.answer).toContain('合规引导助手')
  // 覆盖范围外的法域要说明「不在覆盖范围」，而不是让用户以为自己没说清国家。
  const outOfScope = await api('assistant/chat', { method: 'POST', data: { question: '阿联酋商标怎么注册？', page: '/', session_id: 'release-scope-' + Date.now() } })
  expect(outOfScope.answer).toContain('不在当前覆盖的东盟国家范围内')
  expect(outOfScope.answer).not.toContain('未明确单一目标国家')
  results.guide = { status: guide.answer_status, outOfScopeStatus: outOfScope.answer_status }
  // 非合规输入（问时间是典型）不能被判成「未明确单一目标国家」。
  const nonCompliance = await api('assistant/chat', { method: 'POST', data: { question: '现在是几点钟？', page: '/', session_id: 'release-noncompliance-' + Date.now() } })
  expect(nonCompliance.answer_status).toBe('out_of_scope')
  expect(nonCompliance.answer).toContain('不在我的处理范围')
  expect(nonCompliance.answer).not.toContain('未明确单一目标国家')
  // 合规问题缺国家时仍必须追问国家——范围判断不能顺手把这道闸门放松。
  const needsCountry = await api('assistant/chat', { method: 'POST', data: { question: '商标注册需要什么材料？', page: '/', session_id: 'release-needs-country-' + Date.now() } })
  expect(needsCountry.answer_status).toBe('clarification_needed')
  expect(needsCountry.answer).toContain('未明确单一目标国家')
  expect(needsCountry.sources).toHaveLength(0)
  results.scopeGate = { nonCompliance: nonCompliance.answer_status, needsCountry: needsCountry.answer_status }

  // 审核门槛边界：越南 M1 尚无已审核来源，必须拒绝作答并要求人工复核。
  await selectOption('目标国家', '越南')
  await selectOption('业务模块', '外商投资')
  await page.getByLabel('业务场景与当前阶段').fill('拟设立合资公司')
  await page.getByLabel('已知事实与待核对材料').fill('尚未确定主体类型与股权比例')
  const gateResponse = page.waitForResponse(response => response.url().endsWith('/api/assistant/chat') && response.request().method() === 'POST', { timeout: 120000 })
  await page.getByRole('button', { name: '生成核验清单', exact: true }).click()
  await expect(page.getByRole('button', { name: '生成核验清单', exact: true })).toHaveAttribute('aria-busy', 'false', { timeout: 120000 })
  const gateAnswer = await (await gateResponse).json()
  expect(gateAnswer.answer_status).toBe('human_review_required')
  expect(gateAnswer.sources).toHaveLength(0)
  await expect(page.getByText('当前没有匹配的已审核资料', { exact: true })).toBeVisible()
  results.reviewGate = { answerStatus: gateAnswer.answer_status, sourceCount: gateAnswer.sources.length }
  await page.screenshot({ path: path.join(artifacts, 'PC-审核门槛边界-VN-M1.png'), fullPage: false })

  await page.getByLabel('业务场景与当前阶段').fill('改为合同条款整理')
  await expect(page.getByText('输入已修改，原筛查结果已清除，请重新生成核验清单。')).toBeVisible()
  await expect(page.getByText('当前没有匹配的已审核资料', { exact: true })).toHaveCount(0)
  results.screeningInvalidation = true

  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto(base + '#/')
  await page.getByRole('button', { name: '查看报告中心', exact: true }).click()
  await expect(page).toHaveURL(base + '#/reports')
  await page.screenshot({ path: path.join(artifacts, '移动端390-报告中心入口.png'), fullPage: false })
  await page.goto(base + '#/report/' + firstTask)
  await page.getByRole('tab', { name: '图样辅助比对' }).click()
  await expect(page.getByRole('tab', { name: '图样辅助比对' })).toHaveAttribute('aria-selected', 'true')
  await expect(page.getByText('尚未接入真实在先商标图样，不展示虚构品牌或匹配分值')).toBeVisible()
  await page.screenshot({ path: path.join(artifacts, '移动端390-报告页签可点击.png'), fullPage: false })
  expect(pageErrors).toEqual([])
  results.pageErrors = pageErrors
  results.passed = true
  await writeFile(path.join(artifacts, '线上验收结果.json'), JSON.stringify(results, null, 2))
  console.log(JSON.stringify({ passed: true, cases: results.cases, monitoringCount: alerts.length, archiveTimesStable: true, pageErrors: [] }, null, 2))
} catch (error) {
  results.passed = false
  results.error = error.message
  await writeFile(path.join(artifacts, '线上验收结果.json'), JSON.stringify(results, null, 2))
  await page.screenshot({ path: path.join(artifacts, '线上验收失败.png'), fullPage: false }).catch(() => undefined)
  throw error
} finally {
  await browser.close()
}
