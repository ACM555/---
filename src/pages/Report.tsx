import { DownloadOutlined } from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  Descriptions,
  Empty,
  Image,
  List,
  message,
  Progress,
  Result,
  Row,
  Skeleton,
  Space,
  Steps,
  Table,
  Tabs,
  Tag,
  Timeline,
  Tooltip,
  Typography,
} from 'antd'
import type { TableColumnsType } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import {
  Legend,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from 'recharts'
import { downloadAuditPdf, getAuditResult } from '@/api/audit'
import HitRuleList from '@/components/HitRuleList'
import LegalReferenceCollapse from '@/components/LegalReferenceCollapse'
import RiskSummaryCard from '@/components/RiskSummaryCard'
import type { AuditResult } from '@/types/audit'

const { Paragraph, Text, Title } = Typography

const reviewSteps = [
  { title: '资料与规则线索整理' },
  { title: '图样辅助比对' },
  { title: '权利线索核验' },
  { title: '场景风险提示' },
  { title: '人工复核清单生成' },
]

const priorityColor = {
  P0: 'red',
  P1: 'orange',
  P2: 'blue',
} as const

type Conflict = AuditResult['relative']['conflicts'][number]

const conflictColumns: TableColumnsType<Conflict> = [
  { title: '品牌名称', dataIndex: 'brandName', key: 'brandName' },
  { title: '注册类别', dataIndex: 'registeredClass', key: 'registeredClass' },
  { title: '注册号', dataIndex: 'registrationNo', key: 'registrationNo' },
  { title: '相似类型', dataIndex: 'similarityType', key: 'similarityType' },
  {
    title: '相似度',
    dataIndex: 'similarityScore',
    key: 'similarityScore',
    render: (score: number) => (
      <Progress percent={score} status={score >= 80 ? 'exception' : 'normal'} size="small" />
    ),
  },
]

type ReportRouteState = {
  taskId?: string
}

function Report() {
  const location = useLocation()
  const navigate = useNavigate()
  const params = useParams<{ taskId?: string }>()
  const taskId = params.taskId ?? (location.state as ReportRouteState | null)?.taskId
  const [result, setResult] = useState<AuditResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [pdfDownloading, setPdfDownloading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<number | null>(null)

  useEffect(() => {
    if (!taskId) {
      setError('缺少任务ID，请从提交页重新进入')
      setLoading(false)
      return undefined
    }

    const clearTimer = () => {
      if (timerRef.current) {
        window.clearTimeout(timerRef.current)
        timerRef.current = null
      }
    }

    const poll = async () => {
      try {
        const nextResult = await getAuditResult(taskId)
        setResult(nextResult)

        if (nextResult.status === 'done') {
          clearTimer()
          setLoading(false)
          return
        }

        if (nextResult.status === 'error') {
          clearTimer()
          setError(`审查失败：${nextResult.errorMessage || nextResult.summary.overallResult || '未知错误'}`)
          setLoading(false)
          return
        }

        timerRef.current = window.setTimeout(poll, 2000)
      } catch {
        clearTimer()
        setError('网络请求失败，请检查后端服务')
        setLoading(false)
      }
    }

    setLoading(true)
    setError(null)
    poll()

    return clearTimer
  }, [taskId])

  if (error) {
    return (
      <Result
        status="error"
        title="审查失败"
        subTitle={error}
        extra={
          <Button type="primary" onClick={() => navigate('/submit')}>
            返回提交页重试
          </Button>
        }
      />
    )
  }

  if (loading && !result) {
    return (
      <Space direction="vertical" size={24} style={{ display: 'flex' }}>
        <Title level={2} style={{ margin: 0 }}>
          M5 风险提示清单
        </Title>
        <Card>
          <Skeleton active paragraph={{ rows: 8 }} />
        </Card>
      </Space>
    )
  }

  if (!result) {
    return <Empty description="暂无审查结果" />
  }

  if (result.status !== 'done') {
    return (
      <Card style={{ margin: '64px auto', maxWidth: 620 }}>
        <Space direction="vertical" size={24} style={{ display: 'flex' }}>
          <Title level={2} style={{ margin: 0 }}>
            AI 合规审查中...
          </Title>
          <Progress percent={result.progress} />
          <Steps current={result.currentStep} direction="vertical" items={reviewSteps} />
          <Paragraph type="secondary" style={{ margin: 0 }}>
            正在获取后端审查结果，页面将每 2 秒自动刷新一次。
          </Paragraph>
        </Space>
      </Card>
    )
  }

  const { absolute, advice, relative, visual } = result
  const { intelligence } = result

  const absoluteTab = (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <HitRuleList hitRules={result.hitRules} />
      <Row gutter={[24, 24]}>
        <Col xs={24} lg={10}>
          <Card title="规则风险信号（非结果概率）" style={{ height: '100%' }}>
            {result.assessmentStatus === 'pending_verification' ? <Alert type="info" showIcon message="待核验，不展示驳回概率或法律风险分值" description="内部规则命中仅用于提示需要补充的材料和人工核对事项。" /> : <div style={{ paddingTop: 24, textAlign: 'center' }}>
              <Progress
                type="dashboard"
                percent={absolute.rejectionProbability}
                strokeColor={absolute.hasRisk ? '#faad14' : '#52c41a'}
                format={(percent) => `${percent}%`}
              />
            </div>}
          </Card>
        </Col>
      </Row>
    </Space>
  )

  const relativeTab = (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <Alert
        message={relative.hasRisk ? '检出需人工复核的权利线索' : '当前本地范围未检出匹配线索'}
        type={relative.hasRisk ? 'warning' : 'info'}
        showIcon
      />
      <Card title="在先权利线索比对">
        {relative.conflicts.length > 0 ? (
          <Table<Conflict>
            columns={conflictColumns}
            dataSource={relative.conflicts}
            pagination={false}
            rowKey={(record) => record.registrationNo || record.brandName}
            scroll={{ x: 900 }}
          />
        ) : (
          <Empty description="暂无可显示的权利线索" />
        )}
      </Card>
      {relative.precedents.length > 0 ? (
        relative.precedents.map((precedent) => (
          <Card key={`${precedent.caseName}-${precedent.date}`} title={<Title level={5}>{precedent.caseName}</Title>}>
            <Paragraph type="secondary">
              {precedent.court} · {precedent.date}
            </Paragraph>
            <Paragraph>判决摘要：{precedent.ruling}</Paragraph>
            <Alert message={`关联性说明：${precedent.relevance}`} type="error" />
          </Card>
        ))
      ) : (
        <Empty description="暂无判例依据" />
      )}
    </Space>
  )

  const referenceTab = (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <Card title="法律依据">
        <LegalReferenceCollapse references={result.references} />
      </Card>
    </Space>
  )

  const visualTab = (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      {visual.radarData.length > 0 ? (
        <Row gutter={[24, 24]}>
          <Col xs={24} lg={14}>
            <Card title="上传图样的视觉特征（不是法律风险）">
              <Alert showIcon type="info" message="复杂度、对称性等仅描述图像；未接入真实在先商标图样比对，不显示虚构对标品牌。" />
              <ResponsiveContainer width="100%" height={320}>
                <RadarChart data={visual.radarData} outerRadius="68%">
                  <PolarGrid />
                  <PolarAngleAxis dataKey="dimension" />
                  <Radar
                    dataKey="target"
                    name="上传商标"
                    stroke="#1677ff"
                    fill="#1677ff"
                    fillOpacity={0.3}
                    isAnimationActive={false}
                  />
                  {result.assessmentStatus !== 'pending_verification' && <Radar
                    dataKey="benchmark"
                    name="对标品牌"
                    stroke="#ff4d4f"
                    fill="#ff4d4f"
                    fillOpacity={0.3}
                    isAnimationActive={false}
                  />}
                  <Legend />
                </RadarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card title="在先权利图样比对" style={{ height: '100%' }}>
              {result.assessmentStatus === 'pending_verification' ? <Empty description="尚未接入真实在先商标图样，不展示虚构品牌或匹配分值" /> : visual.matchedBrands.length > 0 ? (
                <List
                  dataSource={visual.matchedBrands}
                  renderItem={(brand) => (
                    <List.Item>
                      <Space size={16}>
                        <Image alt={brand.name} width={80} preview={false} src={brand.thumbnailUrl} />
                        <Space direction="vertical" size={4}>
                          <Text strong>{brand.name}</Text>
                          <Tag color="orange">匹配分值 {brand.matchScore}</Tag>
                        </Space>
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无匹配品牌" />
              )}
            </Card>
          </Col>
        </Row>
      ) : (
        <Empty description="暂无视觉分析数据" />
      )}
    </Space>
  )

  const adviceTab = (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <Card title="待补事实与建议动作">
        {advice.recommendations.length > 0 ? (
          <List
            dataSource={advice.recommendations}
            renderItem={(recommendation) => (
              <List.Item>
                <Space align="start" size={12}>
                  <Tag color={priorityColor[recommendation.priority]}>{recommendation.priority}</Tag>
                  <div>
                    <Text strong>{recommendation.title}</Text>
                    <Paragraph type="secondary" style={{ margin: '6px 0 0' }}>
                      {recommendation.description}
                    </Paragraph>
                  </div>
                </Space>
              </List.Item>
            )}
          />
        ) : (
          <Empty description="暂无建议" />
        )}
      </Card>
      <Card
        title="M5 风险提示清单（预览）"
        extra={
          <Tooltip title={advice.documentDownloadUrl ? '下载 PDF 合规规划书' : '报告尚未生成'}>
            <Button
              disabled={!advice.documentDownloadUrl}
              icon={<DownloadOutlined />}
              loading={pdfDownloading}
              onClick={async () => {
                if (!taskId || !advice.documentDownloadUrl) return
                setPdfDownloading(true)
                try {
                  await downloadAuditPdf(taskId)
                } catch (reason) {
                  message.error(reason instanceof Error ? reason.message : 'PDF 下载失败，请重试。')
                } finally {
                  setPdfDownloading(false)
                }
              }}
            >
              下载完整文书
            </Button>
          </Tooltip>
        }
      >
        {advice.documentPreview ? (
          advice.documentPreview.split('\n\n').map((paragraph) => (
            <Paragraph key={paragraph} style={{ whiteSpace: 'pre-line' }}>
              {paragraph}
            </Paragraph>
          ))
        ) : (
          <Empty description="暂无文书预览" />
        )}
      </Card>
    </Space>
  )

  const intelligenceTab = (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={8}>
          <Card
            className="insight-card"
            title={intelligence.crossClassShield.title}
            extra={
              <Tag color={intelligence.crossClassShield.triggered ? 'red' : 'green'}>
                {intelligence.crossClassShield.triggered ? '触发复核' : '未触发'}
              </Tag>
            }
          >
            {result.assessmentStatus !== 'pending_verification' && <Progress
              percent={intelligence.crossClassShield.score}
              status={intelligence.crossClassShield.triggered ? 'exception' : 'normal'}
            />}
            <Paragraph>{intelligence.crossClassShield.explanation}</Paragraph>
            <List
              size="small"
              dataSource={intelligence.crossClassShield.protectedElements}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
            <Alert message={intelligence.crossClassShield.suggestedAction} type="warning" showIcon />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card
            className="insight-card"
            title={intelligence.refusalHistory.title}
            extra={
              <Tag color={intelligence.refusalHistory.triggered ? 'volcano' : 'green'}>
                {intelligence.refusalHistory.triggered ? '红牌信号' : '观察'}
              </Tag>
            }
          >
            <Paragraph>{intelligence.refusalHistory.explanation}</Paragraph>
            <List
              size="small"
              header={<Text strong>风险信号</Text>}
              dataSource={intelligence.refusalHistory.redFlags}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
            <List
              size="small"
              header={<Text strong>证据来源</Text>}
              dataSource={intelligence.refusalHistory.evidence}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card className="insight-card" title={intelligence.culturalReview.title}>
            <Descriptions
              column={1}
              items={[
                { key: 'country', label: '目标国家', children: intelligence.culturalReview.country },
                {
                  key: 'status',
                  label: '审查状态',
                  children: intelligence.culturalReview.triggered ? '存在需复核事项' : '未触发高风险禁忌',
                },
              ]}
            />
            <List
              size="small"
              dataSource={intelligence.culturalReview.rules}
              renderItem={(rule) => (
                <List.Item>
                  <Space direction="vertical" size={2}>
                    <Text strong className={`severity-${rule.severity}`}>
                      {rule.label}
                    </Text>
                    <Text type="secondary">{rule.note}</Text>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="跨域注册策略">
            <Descriptions
              column={1}
              items={[
                { key: 'route', label: '推荐路径', children: intelligence.registrationStrategy.route },
                {
                  key: 'markets',
                  label: '覆盖市场',
                  children: `${intelligence.registrationStrategy.marketCount} 个`,
                },
                { key: 'rationale', label: '推荐理由', children: intelligence.registrationStrategy.rationale },
              ]}
            />
            <Timeline
              style={{ marginTop: 18 }}
              items={intelligence.registrationStrategy.timeline.map((item) => ({
                children: (
                  <Space direction="vertical" size={2}>
                    <Text strong>{item.stage}</Text>
                    <Text type="secondary">
                      {item.duration} · {item.output}
                    </Text>
                  </Space>
                ),
              }))}
            />
            <List
              size="small"
              dataSource={intelligence.registrationStrategy.costNotes}
              renderItem={(item) => <List.Item>{item}</List.Item>}
            />
          </Card>
        </Col>
        <Col xs={24} lg={10}>
          <Card title="注册后监控计划">
            <List
              dataSource={intelligence.monitoring}
              renderItem={(item) => (
                <List.Item>
                  <Space direction="vertical" size={4}>
                    <Text strong>{item.name}</Text>
                    <Text type="secondary">
                      {item.cadence} · {item.source}
                    </Text>
                    <Tag color="blue">{item.actionWindow}</Tag>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </Space>
  )

  return (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <Title level={2} style={{ margin: 0 }}>
          M5 商标与技术出海风险提示清单
      </Title>
      <RiskSummaryCard data={result} />
      <Tabs
        className="report-tabs"
        items={[
          { key: 'intelligence', label: '参赛亮点', children: intelligenceTab },
          { key: 'rules', label: '规则命中', children: absoluteTab },
          { key: 'relative', label: '权利线索比对', children: relativeTab },
          { key: 'references', label: '法律依据', children: referenceTab },
          { key: 'visual', label: '图样辅助比对', children: visualTab },
          { key: 'advice', label: '待补事实与建议动作', children: adviceTab },
        ]}
      />
    </Space>
  )
}

export default Report
