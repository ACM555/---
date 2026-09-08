import request from './request'

export interface AssistantSource {
  id: string
  title: string
  excerpt: string
  source_url?: string
  country_code?: string
  legal_module?: string
  evidence_level?: string
  source_type?: string
  source_language?: string
  verified_at?: string
  effective_at?: string
  prerequisites: string[]
  non_inferences: string[]
  review_triggers: string[]
  passages: Array<{
    locator: string
    original_text: string
    chinese_text?: string
    effective_at?: string
  }>
}

export interface AssistantReply {
  answer: string
  answer_status: string
  sources: AssistantSource[]
  scope_and_preconditions: string[]
  facts_to_confirm: string[]
  suggested_actions: string[]
  human_review_reasons: string[]
  disclaimer: string
}

export async function askAssistant(question: string, page: string, sessionId: string, imageDataUrl?: string): Promise<AssistantReply> {
  const response = await request.post(
    '/assistant/chat',
    { question, page, session_id: sessionId, image_data_url: imageDataUrl },
    { timeout: 120_000 },
  )
  // `request` 的响应拦截器已经返回了解包后的业务对象；此处不能再次读取 `.data`。
  return response as unknown as AssistantReply
}
