import { DownloadOutlined, FileTextOutlined, SearchOutlined } from '@ant-design/icons'
import { Button, Card, Col, Input, Progress, Row, Skeleton, Space, Table, Tag, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
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
          <Tag color={riskColor[record.riskLevel]}>{record.riskLevel.toUpperCase()}</Tag>
          <Progress percent={value} size="small" />
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
      title: '归档时间',
      dataIndex: 'updatedAt',
      key: 'updatedAt',
      render: (value: string) => <Text>{value}</Text>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_, record) => (
        <Space>
          <Button disabled={!record.taskId} onClick={() => navigate(`/report/${record.taskId}`)} size="small">
            查看
          </Button>
          <Button disabled={!record.taskId} href={record.taskId ? `/api/audit/report/${record.taskId}/pdf` : undefined} icon={<DownloadOutlined />} size="small">
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
                    <Tag color={riskColor[item.riskLevel]}>{item.riskLevel.toUpperCase()}</Tag>
                    <Text type="secondary">{item.status}</Text>
                  </Space>
                  <Title level={4}>{item.brandName}</Title>
                  <Paragraph type="secondary">{item.summary}</Paragraph>
                  <Progress percent={item.riskScore} size="small" />
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
