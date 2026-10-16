import { useEffect, useRef, useState, type PointerEvent as ReactPointerEvent } from 'react'
import { RobotOutlined, SendOutlined, CloseOutlined, FileTextOutlined, PaperClipOutlined } from '@ant-design/icons'
import { Button, Input, Spin, Tag, Typography } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'
import { askAssistant, type AssistantReply } from '@/api/assistant'
import { createClientId } from '@/utils/clientId'

interface ChatMessage {
  role: 'assistant' | 'user'
  text: string
}

interface AssistantPosition {
  x: number
  y: number
}

interface DragState {
  pointerId: number
  startX: number
  startY: number
  originX: number
  originY: number
  moved: boolean
}

const launcherSize = 64
const viewportPadding = 16

function getInitialPosition(): AssistantPosition {
  if (typeof window === 'undefined') {
    return { x: 0, y: 0 }
  }

  return {
    x: window.innerWidth - launcherSize - 28,
    y: window.innerHeight - launcherSize - 28,
  }
}

function clampPosition(position: AssistantPosition): AssistantPosition {
  if (typeof window === 'undefined') return position

  return {
    x: Math.min(Math.max(position.x, viewportPadding), window.innerWidth - launcherSize - viewportPadding),
    y: Math.min(Math.max(position.y, viewportPadding), window.innerHeight - launcherSize - viewportPadding),
  }
}

const answerStatusTags: Record<string, { color: string; label: string }> = {
  source_backed: { color: 'green', label: '已审来源参考' },
  guidance: { color: 'blue', label: '使用引导' },
  out_of_scope: { color: 'default', label: '不在服务范围' },
}

const answerStatusTag = (status: string) => answerStatusTags[status] ?? { color: 'orange', label: '需人工复核' }

const pageActions: Record<string, string> = {
  '新建智能审查': '/submit',
  '查看品牌资产': '/assets',
  '浏览规则库': '/rules',
  '补充品牌资产': '/assets',
  '前往智能审查': '/submit',
  '检查提交材料': '/submit',
  '查看规则库': '/rules',
  '查看审查进度': '/reviewing',
  '查看报告中心': '/reports',
  '查看审查报告': '/reports',
}

export default function AiAssistant() {
  const location = useLocation()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [imageDataUrl, setImageDataUrl] = useState<string>()
  const [sessionId] = useState(createClientId)
  const [position, setPosition] = useState<AssistantPosition>(() => clampPosition(getInitialPosition()))
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: 'assistant', text: '我是合规引导助手。可以协助你准备材料、理解风险和定位系统规则。' },
  ])
  const [reply, setReply] = useState<AssistantReply | null>(null)
  const dragRef = useRef<DragState | null>(null)
  const suppressClickRef = useRef(false)
  const panelClassName = [
    'ai-assistant__panel',
    position.x < 380 ? 'ai-assistant__panel--from-left' : '',
    position.y < 380 ? 'ai-assistant__panel--drop-down' : '',
  ].filter(Boolean).join(' ')

  useEffect(() => {
    const handleResize = () => setPosition((current) => clampPosition(current))
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      const drag = dragRef.current
      if (!drag || event.pointerId !== drag.pointerId) return

      const deltaX = event.clientX - drag.startX
      const deltaY = event.clientY - drag.startY
      if (Math.abs(deltaX) + Math.abs(deltaY) > 4) {
        drag.moved = true
      }

      setPosition(clampPosition({ x: drag.originX + deltaX, y: drag.originY + deltaY }))
    }

    const handlePointerUp = (event: PointerEvent) => {
      const drag = dragRef.current
      if (!drag || event.pointerId !== drag.pointerId) return

      suppressClickRef.current = drag.moved
      dragRef.current = null
    }

    window.addEventListener('pointermove', handlePointerMove)
    window.addEventListener('pointerup', handlePointerUp)
    window.addEventListener('pointercancel', handlePointerUp)

    return () => {
      window.removeEventListener('pointermove', handlePointerMove)
      window.removeEventListener('pointerup', handlePointerUp)
      window.removeEventListener('pointercancel', handlePointerUp)
    }
  }, [])

  const send = async () => {
    const text = question.trim()
    if (!text || loading) return
    setQuestion('')
    setMessages((current) => [...current, { role: 'user', text }])
    setLoading(true)
    try {
      const nextReply = await askAssistant(text, location.pathname, sessionId, imageDataUrl)
      setReply(nextReply)
      setMessages((current) => [...current, { role: 'assistant', text: nextReply.answer }])
      setImageDataUrl(undefined)
    } catch {
      setMessages((current) => [...current, { role: 'assistant', text: '暂时无法连接 AI 服务，请稍后重试。' }])
    } finally {
      setLoading(false)
    }
  }

  const attachImage = (file: File | undefined) => {
    if (!file || !file.type.startsWith('image/') || file.size > 4 * 1024 * 1024) return
    const reader = new FileReader()
    reader.onload = () => setImageDataUrl(typeof reader.result === 'string' ? reader.result : undefined)
    reader.readAsDataURL(file)
  }

  const startDrag = (event: ReactPointerEvent<HTMLButtonElement>) => {
    dragRef.current = {
      pointerId: event.pointerId,
      startX: event.clientX,
      startY: event.clientY,
      originX: position.x,
      originY: position.y,
      moved: false,
    }
  }

  const togglePanel = () => {
    if (suppressClickRef.current) {
      suppressClickRef.current = false
      return
    }
    setOpen((value) => !value)
  }

  return (
    <aside className={`ai-assistant ${open ? 'ai-assistant--open' : ''}`} style={{ left: position.x, top: position.y }} aria-label="合规引导助手">
      {open && (
        <section className={panelClassName}>
          <header className="ai-assistant__header">
            <div>
              <Typography.Text strong>合规引导助手</Typography.Text>
              <Typography.Text type="secondary">基于已授权资料回答</Typography.Text>
            </div>
            <Button type="text" icon={<CloseOutlined />} onClick={() => setOpen(false)} aria-label="收起助手" />
          </header>
          <div className="ai-assistant__dialogue">
            {messages.map((message, index) => (
              <p className={`ai-assistant__message ai-assistant__message--${message.role}`} key={`${message.role}-${index}`}>
                {message.text}
              </p>
            ))}
            {loading && (
              <div className="ai-assistant__loading">
                <Spin size="small" />
                <Typography.Text>正在检索已授权资料…</Typography.Text>
              </div>
            )}
            {reply && (
              <div className="ai-assistant__evidence">
                <Tag color={answerStatusTag(reply.answer_status).color}>{answerStatusTag(reply.answer_status).label}</Tag>
                {reply.sources.map((source) => (
                  <div key={source.id}>
                    {source.source_url ? <a href={source.source_url} target="_blank" rel="noreferrer"><Tag icon={<FileTextOutlined />}>{source.country_code} · {source.legal_module} · {source.title}</Tag></a> : <Tag icon={<FileTextOutlined />}>{source.title}</Tag>}
                    <Typography.Paragraph type="secondary">资料等级：{source.evidence_level ?? '未标注'}；语种：{source.source_language ?? '未标注'}；最近核验：{source.verified_at ?? '未标注'}{source.effective_at ? `；生效：${source.effective_at}` : ''}</Typography.Paragraph>
                    {source.prerequisites.length > 0 && <Typography.Paragraph type="secondary">资料适用前提：{source.prerequisites.join('；')}</Typography.Paragraph>}
                    {source.non_inferences.length > 0 && <Typography.Paragraph type="secondary">不能推断：{source.non_inferences.join('；')}</Typography.Paragraph>}
                    {source.review_triggers.length > 0 && <Typography.Paragraph type="secondary">复核触发：{source.review_triggers.join('；')}</Typography.Paragraph>}
                    {source.passages.map((passage) => <Typography.Paragraph type="secondary" key={`${source.id}-${passage.locator}`}>原文章节：{passage.locator}{passage.effective_at ? `；章节生效：${passage.effective_at}` : ''}<br />原文摘录：{passage.original_text}{passage.chinese_text ? <><br />工作译文（非官方翻译）：{passage.chinese_text}</> : null}</Typography.Paragraph>)}
                  </div>
                ))}
                {reply.scope_and_preconditions.length > 0 && <Typography.Paragraph type="secondary">适用前提：{reply.scope_and_preconditions.join('；')}</Typography.Paragraph>}
                {reply.facts_to_confirm.length > 0 && <Typography.Paragraph type="secondary">仍需确认：{reply.facts_to_confirm.join('；')}</Typography.Paragraph>}
                {reply.human_review_reasons.length > 0 && <Typography.Paragraph type="secondary">人工复核：{reply.human_review_reasons.join('；')}</Typography.Paragraph>}
                <Typography.Paragraph type="secondary">{reply.disclaimer}</Typography.Paragraph>
                <div className="ai-assistant__actions">
                  {reply.suggested_actions.map((action) => (
                    <Button key={action} size="small" onClick={() => navigate(pageActions[action] ?? '/')}>{action}</Button>
                  ))}
                </div>
              </div>
            )}
          </div>
          <div className="ai-assistant__composer">
            <div className="ai-assistant__input-stack">
              <Input.TextArea value={question} onChange={(event) => setQuestion(event.target.value)} onPressEnter={(event) => { if (!event.shiftKey) { event.preventDefault(); void send() } }} placeholder="输入你的合规问题" autoSize={{ minRows: 2, maxRows: 4 }} />
              <label className="ai-assistant__attachment">
                <PaperClipOutlined /> {imageDataUrl ? '图样已附加' : '附加图样（限 4MB）'}
                <input type="file" accept="image/*" onChange={(event) => attachImage(event.target.files?.[0])} />
              </label>
            </div>
            <Button type="primary" icon={<SendOutlined />} onClick={() => void send()} loading={loading} aria-label="发送问题" />
          </div>
        </section>
      )}
      <Button className="ai-assistant__launcher" type="primary" icon={<RobotOutlined />} onPointerDown={startDrag} onClick={togglePanel} aria-label="拖动或打开 AI 引导">
        <span>AI</span>
      </Button>
    </aside>
  )
}
