import { describe, expect, it, vi } from 'vitest'
import request from './request'
import { askAssistant, type AssistantReply } from './assistant'

vi.mock('./request', () => ({
  default: {
    post: vi.fn(),
  },
}))

describe('askAssistant', () => {
  it('uses the already-unwrapped response returned by the common request interceptor', async () => {
    const reply: AssistantReply = {
      answer: '请先补充品牌素材。',
      answer_status: 'human_review_required',
      sources: [{
        id: 'guide',
        title: '提交指引',
        excerpt: '上传素材后开始审查。',
        prerequisites: [],
        non_inferences: [],
        review_triggers: [],
        passages: [],
      }],
      scope_and_preconditions: [],
      facts_to_confirm: ['目标国家'],
      suggested_actions: ['补充品牌资产'],
      human_review_reasons: ['资料不足'],
      disclaimer: '本内容不构成律师法律意见。',
    }
    vi.mocked(request.post).mockResolvedValueOnce(reply)

    await expect(askAssistant('下一步做什么？', '/submit', 'test-session')).resolves.toEqual(reply)
    expect(request.post).toHaveBeenCalledWith('/assistant/chat', {
      question: '下一步做什么？',
      page: '/submit',
      session_id: 'test-session',
      image_data_url: undefined,
    }, { timeout: 120_000 })
  })
})
