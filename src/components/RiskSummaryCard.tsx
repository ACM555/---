import { Alert, Badge, Card, Col, Divider, Row, Skeleton, Tag, Typography } from 'antd'
import type { AuditResult } from '@/types/audit'

const { Text, Title } = Typography

interface RiskSummaryCardProps {
  data: AuditResult | null
  loading?: boolean
}

const riskConfig = {
  high: { label: '高危', color: '#cf1322', alertType: 'error' as const },
  medium: { label: '中危', color: '#d48806', alertType: 'warning' as const },
  low: { label: '低危', color: '#389e0d', alertType: 'success' as const },
}

function RiskSummaryCard({ data, loading = false }: RiskSummaryCardProps) {
  if (loading || !data) {
    return (
      <Card style={{ marginBottom: 24 }}>
        <Skeleton active paragraph={{ rows: 3 }} />
      </Card>
    )
  }

  const brandName = data.brandName || data.summary.brandName || '未命名品牌'
  const niceClass = data.niceClass || data.summary.niceClass || '未选择分类'
  const goodsServices = data.goodsServices || '暂无商品服务描述'
  const riskLevel = data.riskLevel || data.summary.riskLevel || 'low'
  const riskScore = data.riskScore ?? data.summary.riskScore ?? 0
  const overallResult = data.overallResult || data.summary.overallResult || '暂无审查结论'
  const cfg = riskConfig[riskLevel]

  return (
    <Card
      style={{
        borderLeft: `4px solid ${cfg.color}`,
        marginBottom: 24,
      }}
    >
      <Row align="middle" gutter={[16, 12]}>
        <Col>
          <Title level={4} style={{ margin: 0 }}>
            {brandName}
          </Title>
        </Col>
        <Col>
          <Tag color="blue">{niceClass}</Tag>
        </Col>
        <Col span={24}>
          <Text type="secondary">商品服务：{goodsServices}</Text>
        </Col>
      </Row>

      <Row align="middle" gutter={[24, 16]} style={{ marginTop: 16 }}>
        <Col>
          <div style={{ textAlign: 'center' }}>
            <Text style={{ display: 'block', fontSize: 12 }} type="secondary">
              风险等级
            </Text>
            <Tag color={cfg.color} style={{ fontSize: 16, marginTop: 6, padding: '4px 16px' }}>
              {cfg.label}
            </Tag>
          </div>
        </Col>
        <Col>
          <div aria-label={`风险分值 ${riskScore}，风险等级${cfg.label}`} style={{ textAlign: 'center' }}>
            <Text style={{ display: 'block', fontSize: 12 }} type="secondary">
              风险分值
            </Text>
            <Text strong style={{ color: cfg.color, fontSize: 32 }}>
              {riskScore}
            </Text>
            <Text style={{ fontSize: 14 }} type="secondary">
              /100
            </Text>
          </div>
        </Col>
        <Col>
          {data.manualReviewRequired ? (
            <Badge status="warning" text="建议人工复核" />
          ) : (
            <Badge status="success" text="无需人工复核" />
          )}
        </Col>
      </Row>

      <Divider style={{ margin: '16px 0' }} />
      <Alert message={overallResult} showIcon type={cfg.alertType} />
    </Card>
  )
}

export default RiskSummaryCard
