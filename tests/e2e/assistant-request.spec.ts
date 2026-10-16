import { expect, test } from '@playwright/test'

test('AI 浮窗按真实业务识别公司提问、连续追问和多国请求', async ({ page }) => {
  await page.goto('/#/experience')
  await page.getByRole('button', { name: '开始体验' }).click()
  await expect(page).toHaveURL(/#\/$/)
  await page.getByRole('button', { name: '拖动或打开 AI 引导' }).click()
  const assistant = page.getByRole('complementary', { name: '合规引导助手' })
  const cases = [
    { question: '我们公司想在新加坡申请商标，需要准备什么材料？', scope: ['目标国家：新加坡（SG）', '业务模块：M5'] },
    { question: '那需要哪些申请材料？', scope: ['目标国家：新加坡（SG）', '业务模块：M5'] },
    { question: '我公司出口设备到越南，报关需要哪些资料？', scope: ['目标国家：越南（VN）', '业务模块：M3'] },
    { question: '那马来西亚和印尼的商标呢？', scope: [] },
  ]
  let sessionId: string | undefined
  for (const item of cases) {
    await assistant.getByPlaceholder('输入你的合规问题').fill(item.question)
    const pendingReply = page.waitForResponse(response => response.url().endsWith('/assistant/chat'))
    await assistant.getByRole('button', { name: '发送问题' }).click()
    const response = await pendingReply
    expect(response.ok(), await response.text()).toBeTruthy()
    const payload = response.request().postDataJSON()
    expect(payload.question).toBe(item.question)
    sessionId ??= payload.session_id
    expect(payload.session_id).toBe(sessionId)
    const reply = await response.json()
    expect(reply.answer_status).toBe('human_review_required')
    expect(reply.scope_and_preconditions).toEqual(item.scope)
    expect(reply.sources).toEqual([])
    await expect(assistant.locator('.ai-assistant__message--assistant').last()).toHaveText(reply.answer)
    if (!item.scope.length) expect(reply.answer).toContain('多个国家')
  }
})
