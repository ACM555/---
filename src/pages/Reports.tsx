import { DownloadOutlined, FileTextOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Col, Input, message, Progress, Row, Skeleton, Space, Table, Tag, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { downloadAuditPdf } from '@/api/audit'
import { HoverLift } from '@/components/MotionKit'
import ProductEmpty from '@/components/ProductEmpty'
import { getReports, type ReportRecord, type RiskLevel } from '@/api/saas'

const { Paragraph, Text, Title } = Typography

const riskColor: Record<RiskLevel, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
}

function Reports() {
  const navigate = useNavigate()
  const [reports, setReports] = useState<ReportRecord[]>([])
  const [keyword, setKeyword] = useState('')
  const [loading, setLoading] = useState(true)
  const [downloadingTaskId, setDownloadingTaskId] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    getReports()
      .then((data) => {
        if (mounted) setReports(data)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const filtered = useMemo(() => {
    const term = keyword.trim().toLowerCase()
    if (!term) return reports
    return reports.filter((item) =>
      [item.reportId, item.brandName, item.niceClass, item.summary].join(' ').toLowerCase().includes(term),
    )
  }, [keyword, reports])

  const columns: TableColumnsType<ReportRecord> = [
    {
      title: '报告',
      dataIndex: 'reportId',
      key: 'reportId',
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Text strong>{record.reportId}</Text>
          <Text type="secondary">{record.brandName} · {record.niceClass}</Text>
        </Space>
      ),
    },
    {
      title: '国家',
      dataIndex: 'targetCountries',
      key: 'targetCountries',
      render: (items: string[]) => (
        <Space size={[4, 4]} wrap>{items.map((item, index) => <Tag color="blue" key={`${item}-${index}`}>{item}</Tag>)}</Space>
      ),
    },
    {
      title: '风险',
      dataIndex: 'riskScore',
      key: 'riskScore',
      sorter: (a, b) => a.riskScore - b.riskScore,
      render: (value: number, record) => (
        <Space direction="vertical" size={2} style={{ minWidth: 150 }}>
          <Tag color={record.assessmentStatus === 'pending_verification' ? 'orange' : riskColor[record.riskLevel]}>{record.assessmentStatus === 'pending_verification' ? '待核验' : record.riskLevel.toUpperCase()}</Tag>
          {record.assessmentStatus !== 'pending_verification' && <Progress percent={value} size="small" />}
        </Space>
      ),
    },
    {
      title: '摘要',
      dataIndex: 'summary',
      key: 'summary',
      render: (value: string) => <Text type="secondary">{value}</Text>,
    },
    {
      title: '报告时间记录',
      key: 'timestamps',
      render: (_, record) => <Space direction="vertical" size={2}>
        <Text>生成：{record.completedAt || record.createdAt}</Text>
        <Text type="secondary">归档：{record.archivedAt || record.completedAt || record.createdAt}</Text>
        <Text type="secondary">修改：{record.updatedAt}</Text>
        <Text type="secondary">最近查看：{record.lastViewedAt || '尚未查看'}</Text>
      </Space>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button disabled={!record.taskId} onClick={() => navigate(`/report/${record.taskId}`)} size="small">
            查看
          </Button>
          <Button
            disabled={!record.taskId}
            icon={<DownloadOutlined />}
            loading={downloadingTaskId === record.taskId}
            onClick={async () => {
              if (!record.taskId) return
              setDownloadingTaskId(record.taskId)
              try {
                await downloadAuditPdf(record.taskId)
              } catch (reason) {
                message.error(reason instanceof Error ? reason.message : 'PDF 下载失败，请重试。')
              } finally {
                setDownloadingTaskId(null)
              }
            }}
            size="small"
          >
            PDF
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <div className="page-heading">
        <div>
          <Tag icon={<FileTextOutlined />} color="geekblue">Reports</Tag>
          <Title level={2}>报告中心</Title>
          <Paragraph type="secondary">
            所有审查结果在这里归档，可按品牌、类别、风险结论检索，并继续下载 PDF 材料。
          </Paragraph>
        </div>
        <Input
          allowClear
          className="toolbar-search"
          onChange={(event) => setKeyword(event.target.value)}
          placeholder="搜索品牌、报告编号、类别"
          prefix={<SearchOutlined />}
          value={keyword}
        />
      </div>

      <Row gutter={[16, 16]}>
        {filtered.slice(0, 3).map((item) => (
          <Col key={item.reportId} xs={24} lg={8}>
            <HoverLift>
              <Card className={`report-cover-card risk-${item.riskLevel}`}>
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Tag color={item.assessmentStatus === 'pending_verification' ? 'orange' : riskColor[item.riskLevel]}>{item.assessmentStatus === 'pending_verification' ? '待核验' : item.riskLevel.toUpperCase()}</Tag>
                    <Text type="secondary">{item.status}</Text>
                  </Space>
                  <Title level={4}>{item.brandName}</Title>
                  <Paragraph type="secondary">{item.summary}</Paragraph>
                  {item.assessmentStatus !== 'pending_verification' && <Progress percent={item.riskScore} size="small" />}
                  <Button disabled={!item.taskId} onClick={() => navigate(`/report/${item.taskId}`)} type="primary">
                    打开报告
                  </Button>
                </Space>
              </Card>
            </HoverLift>
          </Col>
        ))}
      </Row>

      <Card title="审查报告库" extra={<Text type="secondary">{filtered.length} 份</Text>}>
        {loading ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : filtered.length ? (
          <Table<ReportRecord>
            columns={columns}
            dataSource={filtered}
            pagination={{ pageSize: 8 }}
            rowKey="reportId"
            scroll={{ x: 1100 }}
          />
        ) : (
          <ProductEmpty description="没有匹配的报告，请调整搜索条件。" />
        )}
      </Card>
    </Space>
  )
}

export default Reports
