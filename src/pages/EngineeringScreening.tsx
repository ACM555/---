import { FileSearchOutlined } from '@ant-design/icons'
import { Alert, Button, Card, Form, Input, Result, Select, Space, Tag, Typography } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { askAssistant, type AssistantReply } from '@/api/assistant'
import { getLegalSources, getOfficialPointers, getScenarioChecklists, type LegalSource, type OfficialLegalPointer, type ScenarioChecklist } from '@/api/legal'
import ScenarioChecklistCard from '@/components/ScenarioChecklistCard'
import { createClientId } from '@/utils/clientId'

const countries = [
  ['BN', '文莱'], ['KH', '柬埔寨'], ['ID', '印尼'], ['LA', '老挝'], ['MY', '马来西亚'],
  ['MM', '缅甸'], ['PH', '菲律宾'], ['SG', '新加坡'], ['TH', '泰国'], ['TL', '东帝汶'], ['VN', '越南'],
].map(([value, label]) => ({ value, label }))

const modules = [
  ['M1', '外商投资准入与公司设立'], ['M2', '跨境商事合同审查与违约风险防控'], ['M3', '跨境货物运输与贸易合规'],
  ['M4', '东盟劳动用工与签证合规'], ['M5', '知识产权布局与技术出海保护'], ['M6', '跨境争议解决与货款追偿'],
].map(([value, label]) => ({ value, label }))

const followUps: Record<string, string[]> = {
  M1: ['主体类型、拟从事行业及项目地点。', '股权与控制权安排、是否涉及许可或受监管活动。'],
  M2: ['合同主体、交易标的、适用法和争议解决约定。', '已发生或可能发生的违约事实、通知和证据。'],
  M3: ['货物、贸易术语、运输路线和清关主体。', '原产地、许可证、单证和交付责任安排。'],
  M4: ['雇主、岗位、工作地点、国籍和工作期限。', '签证/工作许可路径、劳动合同及社会保障安排。'],
  M5: ['拟保护的商标、专利、技术或商业秘密及目标市场。', '权利归属、申请/注册状态、许可或研发合作安排。'],
  M6: ['合同争议解决条款、仲裁地/法院和适用法。', '欠款、资产所在地、送达与已保全的证据材料。'],
}

type ScreeningValues = { country: string; legalModule: string; scenario: string; facts?: string }

function renderInline(value: string) {
  return value.split('**').map((part, index) => index % 2 === 1 ? <strong key={`${part}-${index}`}>{part}</strong> : part)
}

function StructuredAnswer({ answer }: { answer: string }) {
  const normalized = answer
    .replace(/(?:^|\s)(#{1,3}\s+)/g, '\n$1')
    .replace(/\s(?=\d+\.\s+\*\*)/g, '\n')
    .replace(/\s(?=-\s+\*\*)/g, '\n')
  const lines = normalized.split('\n').map(line => line.trim()).filter(Boolean)

  return <Space direction="vertical" size={12} style={{ display: 'flex', marginTop: 12 }}>
    {lines.map((line, index) => {
      const heading = line.match(/^#{1,3}\s+(.+)$/)
      const numbered = line.match(/^(\d+)\.\s+(.+)$/)
      if (heading) return <Typography.Title level={5} key={`${line}-${index}`} style={{ margin: '12px 0 0' }}>{renderInline(heading[1])}</Typography.Title>
      if (numbered) return <div key={`${line}-${index}`} style={{ display: 'flex', gap: 10, lineHeight: 1.8 }}><Typography.Text strong>{`${numbered[1]}.`}</Typography.Text><Typography.Text>{renderInline(numbered[2])}</Typography.Text></div>
      return <Typography.Paragraph key={`${line}-${index}`} style={{ lineHeight: 1.9, margin: 0 }}>{renderInline(line)}</Typography.Paragraph>
    })}
  </Space>
}

export default function EngineeringScreening() {
  const [searchParams] = useSearchParams()
  const requestedModule = searchParams.get('module')
  const initialModule = requestedModule && /^M[1-6]$/.test(requestedModule) ? requestedModule : undefined
  return <EngineeringScreeningForm key={initialModule ?? 'unselected'} initialModule={initialModule} />
}

function EngineeringScreeningForm({ initialModule }: { initialModule?: string }) {
  const [sources, setSources] = useState<LegalSource[] | null>(null)
  const [reply, setReply] = useState<AssistantReply | null>(null)
  const [submitted, setSubmitted] = useState<ScreeningValues | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [inputChanged, setInputChanged] = useState(false)
  const [pointers, setPointers] = useState<OfficialLegalPointer[]>([])
  const [checklists, setChecklists] = useState<ScenarioChecklist[]>([])
  const [form] = Form.useForm<ScreeningValues>()
  const requestGeneration = useRef(0)
  useEffect(() => () => { requestGeneration.current += 1 }, [])
  const submit = async (values: ScreeningValues) => {
    const generation = ++requestGeneration.current
    setSubmitted(values)
    setSources(null)
    setReply(null)
    setLoading(true)
    setError('')
    setInputChanged(false)
    setPointers([])
    setChecklists([])
    try {
      const sourceRows = await getLegalSources({ country_code: values.country, legal_module: values.legalModule })
      if (generation !== requestGeneration.current) return
      setSources(sourceRows)
      const officialPointers = await getOfficialPointers({ country_code: values.country, legal_module: values.legalModule })
      if (generation !== requestGeneration.current) return
      setPointers(officialPointers)
      const scenarioRows = await getScenarioChecklists({ country_code: values.country, legal_module: values.legalModule })
      if (generation !== requestGeneration.current) return
      setChecklists(scenarioRows)
      const countryLabel = countries.find(item => item.value === values.country)?.label ?? values.country
      const moduleLabel = modules.find(item => item.value === values.legalModule)?.label ?? values.legalModule
      const question = `${values.legalModule} 模块：${countryLabel}${moduleLabel}。业务场景：${values.scenario}。已知事实：${values.facts?.trim() || '尚未提供'}。请仅基于已审核资料列出核验事项、事实缺口和人工复核原因。`
      const assistantReply = await askAssistant(question, '/engineering-screening', createClientId())
      if (generation !== requestGeneration.current) return
      setReply(assistantReply)
    } catch (reason) {
      if (generation === requestGeneration.current) setError(reason instanceof Error ? reason.message : '筛查服务暂时不可用')
    } finally { if (generation === requestGeneration.current) setLoading(false) }
  }
  const items = submitted ? followUps[submitted.legalModule] ?? [] : []
  return <Space direction="vertical" size={24} style={{ display: 'flex' }}>
    <div className="page-heading"><Tag icon={<FileSearchOutlined />} color="cyan">M1 · M2 · M3 · M4 · M5 · M6</Tag><Typography.Title level={2}>跨境商事基础合规筛查</Typography.Title><Typography.Paragraph type="secondary">系统只输出来源、风险提示和待补事实；不判断是否违法、不承诺许可、胜诉、执行或回款结果。</Typography.Paragraph></div>
    <Card><Form form={form} layout="vertical" onFinish={submit} initialValues={{ legalModule: initialModule }} onValuesChange={() => {
      requestGeneration.current += 1
      if (submitted) setInputChanged(true)
      setSubmitted(null)
      setSources(null)
      setReply(null)
      setError('')
      setLoading(false)
      setPointers([])
      setChecklists([])
    }}>
      <Form.Item name="country" label="目标国家" rules={[{ required: true, message: '请选择目标国家' }]}><Select showSearch optionFilterProp="label" options={countries} /></Form.Item>
      <Form.Item name="legalModule" label="业务模块" rules={[{ required: true, message: '请选择业务模块' }]}><Select showSearch optionFilterProp="label" options={modules} /></Form.Item>
      <Form.Item name="scenario" label="业务场景与当前阶段" rules={[{ required: true, message: '请填写业务场景' }]}><Input placeholder="例如：向当地经销商销售设备；已签约待发货" /></Form.Item>
      <Form.Item name="facts" label="已知事实与待核对材料"><Input.TextArea placeholder="合同、货物、投资结构、人员、知识产权或争议事实；资料不足将提示人工复核" /></Form.Item>
      <Button type="primary" htmlType="submit" aria-label="生成核验清单" aria-busy={loading} loading={loading}>生成核验清单</Button>
    </Form></Card>
    {inputChanged && <Alert showIcon type="warning" message="输入已修改，原筛查结果已清除，请重新生成核验清单。" />}
    {checklists.map(checklist => <ScenarioChecklistCard key={checklist.id} checklist={checklist} />)}
    {pointers.length > 0 && <Card title="可验证的官方原文入口（不代替法律内容审核）"><Space direction="vertical" size={12} style={{ display: 'flex' }}>{pointers.map(pointer => <div key={pointer.id}>
      <a href={pointer.sourceUrl} target="_blank" rel="noreferrer">{pointer.title}</a>
      <Typography.Paragraph>{pointer.scope}</Typography.Paragraph>
      <Typography.Text type="secondary">索引回查时间：{pointer.lastCheckedAt}；法规版本以原文显示为准。</Typography.Text>
      <Typography.Paragraph>适用条件：{pointer.prerequisites.join('；')}</Typography.Paragraph>
    </div>)}</Space></Card>}
    {loading && <Alert showIcon type="info" message="正在检索已审核资料并生成受控风险提示" description="复杂场景通常需要 20–40 秒。请勿重复点击；系统不会在无来源或高风险事实下生成确定性结论。" />}
    {error && <Alert showIcon type="error" message="筛查未完成，请重试" description={error} action={<Button onClick={() => form.submit()}>重新生成核验清单</Button>} />}
    {sources !== null && <Card title="筛查结果：来源、待补事实与人工复核">
      <Alert type="warning" showIcon message="初步风险提示，不构成律师法律意见或主管机关决定。关键事实、版本和适用条件须人工复核。" />
      <Typography.Title level={4}>必须进一步确认</Typography.Title>
      <ul>{items.map(item => <li key={item}>{item}</li>)}{reply?.facts_to_confirm.map(item => <li key={item}>{item}</li>)}<li>资料版本、生效/核验时间及来源之间是否存在冲突。</li></ul>
      {reply && <><Typography.Title level={4}>受控风险提示</Typography.Title><StructuredAnswer answer={reply.answer} />
        {reply.human_review_reasons.length > 0 && <Alert type="warning" showIcon message={`人工复核：${reply.human_review_reasons.join('；')}`} />}
      </>}
      {sources.length ? <><Typography.Title level={4}>已审核来源</Typography.Title>{sources.map(source => <Card size="small" key={source.source_id} style={{ marginBottom: 10 }}>
        <Space wrap><Tag>{source.legal_module}</Tag><Tag color={source.evidence_level === 'A' ? 'green' : 'gold'}>{source.evidence_level}级</Tag><Typography.Text strong>{source.title}</Typography.Text></Space>
        <Typography.Paragraph style={{ lineHeight: 1.8 }}>{source.supported_fact}</Typography.Paragraph>
        <Space direction="vertical" size={4} style={{ display: 'flex' }}>
          <Typography.Text type="secondary">适用前提：{source.prerequisites.join('；')}</Typography.Text>
          <Typography.Text type="secondary">不得推断：{source.non_inferences.join('；')}</Typography.Text>
          <a href={source.source_url} target="_blank" rel="noreferrer">查看原文</a>
        </Space>
      </Card>)}</> : <Result status="warning" title="当前没有匹配的已审核资料" subTitle="系统不会据无来源或不匹配的资料作答；请补充事实并转人工复核。" />}
    </Card>}
  </Space>
}
