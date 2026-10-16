import { DatabaseOutlined, LinkOutlined } from '@ant-design/icons'
import { Alert, Card, Col, Empty, Row, Select, Skeleton, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { getLegalSources, getOfficialPointers, getScenarioChecklists, type EvidenceLevel, type LegalSource, type OfficialLegalPointer, type ScenarioChecklist } from '@/api/legal'
import ScenarioChecklistCard from '@/components/ScenarioChecklistCard'

const { Paragraph, Text, Title } = Typography

const countryOptions = [
  ['BN', '文莱'], ['KH', '柬埔寨'], ['ID', '印度尼西亚'], ['LA', '老挝'],
  ['MY', '马来西亚'], ['MM', '缅甸'], ['PH', '菲律宾'], ['SG', '新加坡'],
  ['TH', '泰国'], ['TL', '东帝汶'], ['VN', '越南'],
].map(([value, label]) => ({ value, label }))

function RulesLibrary() {
  const [sources, setSources] = useState<LegalSource[]>([])
  const [pointers, setPointers] = useState<OfficialLegalPointer[]>([])
  const [checklists, setChecklists] = useState<ScenarioChecklist[]>([])
  const [loading, setLoading] = useState(true)
  const [country, setCountry] = useState<string>()
  const [module, setModule] = useState<string>()
  const [level, setLevel] = useState<EvidenceLevel>()
  const [error, setError] = useState(false)

  useEffect(() => {
    let mounted = true
    setLoading(true)
    setError(false)
    getLegalSources({ country_code: country, legal_module: module, evidence_level: level })
      .then((data) => {
        if (mounted) setSources(data)
      })
      .catch(() => {
        if (mounted) {
          setSources([])
          setError(true)
        }
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [country, level, module])
  useEffect(() => {
    let active = true
    setPointers([])
    setChecklists([])
    getOfficialPointers({ country_code: country, legal_module: module }).then(items => { if (active) setPointers(items) }).catch(() => { if (active) setPointers([]) })
    getScenarioChecklists({ country_code: country, legal_module: module }).then(items => { if (active) setChecklists(items) }).catch(() => { if (active) setChecklists([]) })
    return () => { active = false }
  }, [country, module])

  return (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <div className="page-heading">
        <div>
          <Tag icon={<DatabaseOutlined />} color="cyan">已审核资料</Tag>
          <Title level={2}>东盟法律资料库</Title>
          <Paragraph type="secondary">
            仅展示已审核资料。A 级可支持有限事实说明；B 级仅用于官方入口、补问和风险提示。
          </Paragraph>
          <Space className="library-filters" wrap>
            <Select aria-label="国家" showSearch optionFilterProp="label" allowClear placeholder="国家" onChange={setCountry} options={countryOptions} />
            <Select aria-label="模块" showSearch optionFilterProp="label" allowClear placeholder="模块" onChange={setModule} options={['M1','M2','M3','M4','M5','M6'].map(value=>({value,label:value}))} />
            <Select aria-label="资料等级" showSearch optionFilterProp="label" allowClear placeholder="资料等级" onChange={setLevel} options={[{value:'A',label:'A 级'},{value:'B',label:'B 级'}]} />
          </Space>
        </div>
      </div>

      <Alert type="info" showIcon message="资料不足时，系统将提示需人工复核；资料建设中的国家或模块不输出法律结论。" />
      {checklists.map(checklist => <ScenarioChecklistCard key={checklist.id} checklist={checklist} />)}
      {pointers.length > 0 && <Card title="已回查的官方法源入口 · 新加坡 M5 商标资料核验">
        <Space direction="vertical" size={16} style={{ display: 'flex' }}>{pointers.map(pointer => <div key={pointer.id}>
          <a href={pointer.sourceUrl} target="_blank" rel="noreferrer">{pointer.title}</a>
          <Paragraph>{pointer.scope}</Paragraph>
          <Text type="secondary">官方索引最近核验：{pointer.lastCheckedAt}；采集快照：{pointer.snapshotVersion.slice(0, 16)}（不是法规版本号）</Text>
          <Paragraph>适用条件：{pointer.prerequisites.join('；')}</Paragraph>
          <Paragraph type="secondary">边界：{pointer.nonInferences.join('；')}</Paragraph>
        </div>)}</Space>
      </Card>}
      {error && <Alert type="error" showIcon message="法律资料加载失败，请重新选择筛选条件或刷新页面重试。" />}

      {loading ? (
        <Card><Skeleton active paragraph={{ rows: 8 }} /></Card>
      ) : sources.length ? (
        <Row gutter={[16, 16]}>
          {sources.map((source) => (
            <Col key={source.source_id} xs={24} md={12} xl={8}>
              <Card className="rule-card country-map-card">
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Space align="center" style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Title level={4}>{source.country_code} · {source.legal_module}</Title>
                    <Tag color={source.evidence_level === 'A' ? 'green' : 'gold'}>{source.evidence_level} 级</Tag>
                  </Space>
                  <Text strong>{source.title}</Text><Text type="secondary">{source.source_type} · {source.source_language}</Text>
                  <Paragraph>{source.supported_fact}</Paragraph><Text type="secondary">核验：{source.verified_at}；适用前提：{source.prerequisites.join('；')}</Text>
                  <a href={source.source_url} target="_blank" rel="noreferrer"><LinkOutlined /> 查看原文</a>
                </Space>
              </Card>
            </Col>
          ))}
        </Row>
      ) : (
        <Empty description="当前筛选条件下没有已审核资料，需人工复核或等待资料建设。" />
      )}
    </Space>
  )
}

export default RulesLibrary
