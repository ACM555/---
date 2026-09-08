import { DatabaseOutlined, LinkOutlined } from '@ant-design/icons'
import { Alert, Card, Col, Empty, Row, Select, Skeleton, Space, Tag, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { getLegalSources, type EvidenceLevel, type LegalSource } from '@/api/legal'

const { Paragraph, Text, Title } = Typography

function RulesLibrary() {
  const [sources, setSources] = useState<LegalSource[]>([])
  const [loading, setLoading] = useState(true)
  const [country, setCountry] = useState<string>()
  const [module, setModule] = useState<string>()
  const [level, setLevel] = useState<EvidenceLevel>()

  useEffect(() => {
    let mounted = true
    getLegalSources({ country_code: country, legal_module: module, evidence_level: level })
      .then((data) => {
        if (mounted) setSources(data)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [country, level, module])

  return (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <div className="page-heading">
        <div>
          <Tag icon={<DatabaseOutlined />} color="cyan">已审核资料</Tag>
          <Title level={2}>东盟法律资料库</Title>
          <Paragraph type="secondary">
            仅展示已审核资料。A 级可支持有限事实说明；B 级仅用于官方入口、补问和风险提示。
          </Paragraph>
          <Space wrap><Select allowClear placeholder="国家" onChange={setCountry} options={[{value:'VN',label:'越南'},{value:'TH',label:'泰国'}]} /><Select allowClear placeholder="模块" onChange={setModule} options={['M1','M2','M3','M4','M5','M6'].map(value=>({value,label:value}))} /><Select allowClear placeholder="资料等级" onChange={setLevel} options={[{value:'A',label:'A 级'},{value:'B',label:'B 级'}]} /></Space>
        </div>
      </div>

      <Alert type="info" showIcon message="资料不足时，系统将提示需人工复核；资料建设中的国家或模块不输出法律结论。" />

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
