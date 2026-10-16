import { CheckCircleOutlined, ExclamationCircleOutlined, WarningOutlined } from '@ant-design/icons'
import { Card, Col, List, Progress, Row, Space, Statistic, Tag, Typography } from 'antd'
import type { AuditResult } from '@/types/audit'

const { Paragraph, Text } = Typography

interface ReportActionPanelProps {
  result: AuditResult
}

const riskMeta = {
  high: { label: '高风险', color: '#cf1322', icon: <ExclamationCircleOutlined /> },
  medium: { label: '中风险', color: '#d48806', icon: <WarningOutlined /> },
  low: { label: '低风险', color: '#389e0d', icon: <CheckCircleOutlined /> },
} as const

function ReportActionPanel({ result }: ReportActionPanelProps) {
  const pending = result.assessmentStatus === 'pending_verification'
  const meta = pending ? { label: '待核验', color: '#d48806', icon: <WarningOutlined /> } : riskMeta[result.riskLevel]
  const triggeredRules = result.hitRules.filter((rule) => rule.applicable)
  const topActions = result.advice.recommendations.slice(0, 3)

  return (
    <Card
      title="报告行动摘要"
      style={{
        borderTop: `4px solid ${meta.color}`,
      }}
    >
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={8}>
          <Space direction="vertical" size={16} style={{ display: 'flex' }}>
            <Statistic
              prefix={<span style={{ color: meta.color }}>{meta.icon}</span>}
              title={pending ? '核验状态' : '综合风险分'}
              value={pending ? '待核验' : result.riskScore}
              suffix={pending ? undefined : '/100'}
              valueStyle={{ color: meta.color, fontWeight: 700 }}
            />
            {!pending && <Progress percent={result.riskScore} strokeColor={meta.color} />}
            <Space wrap>
              <Tag color={meta.color}>{meta.label}</Tag>
              {result.manualReviewRequired && <Tag color="orange">建议人工复核</Tag>}
              <Tag color="blue">命中 {triggeredRules.length} 项规则</Tag>
            </Space>
          </Space>
        </Col>
        <Col xs={24} lg={16}>
          <Paragraph style={{ fontSize: 15, lineHeight: 1.8 }}>{result.overallResult}</Paragraph>
          <List
            dataSource={topActions}
            locale={{ emptyText: '暂无行动建议' }}
            renderItem={(item) => (
              <List.Item style={{ paddingLeft: 0, paddingRight: 0 }}>
                <Space align="start">
                  <Tag color={item.priority === 'P0' ? 'red' : item.priority === 'P1' ? 'orange' : 'blue'}>
                    {item.priority}
                  </Tag>
                  <div>
                    <Text strong>{item.title}</Text>
                    <Paragraph type="secondary" style={{ margin: '4px 0 0' }}>
                      {item.description}
                    </Paragraph>
                  </div>
                </Space>
              </List.Item>
            )}
          />
        </Col>
      </Row>
    </Card>
  )
}

export default ReportActionPanel
