import {
  AppstoreOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import { Button, Card, Col, Empty, Progress, Row, Skeleton, Space, Table, Tag, Typography } from 'antd'
import type { TableColumnsType } from 'antd'
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { HoverLift, MotionItem, StaggerGroup } from '@/components/MotionKit'
import ProductEmpty from '@/components/ProductEmpty'
import { getBrandAssets, type BrandAsset, type RiskLevel } from '@/api/saas'

const { Paragraph, Text, Title } = Typography

const riskColor: Record<RiskLevel, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
}

const riskLabel: Record<RiskLevel, string> = {
  high: '高风险',
  medium: '中风险',
  low: '低风险',
}

function BrandAssets() {
  const navigate = useNavigate()
  const [assets, setAssets] = useState<BrandAsset[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let mounted = true
    getBrandAssets()
      .then((data) => {
        if (mounted) setAssets(data)
      })
      .finally(() => {
        if (mounted) setLoading(false)
      })
    return () => {
      mounted = false
    }
  }, [])

  const columns: TableColumnsType<BrandAsset> = [
    {
      title: '品牌组合',
      dataIndex: 'name',
      key: 'name',
      render: (_, record) => (
        <Space direction="vertical" size={2}>
          <Text strong>{record.name}</Text>
          <Text type="secondary">{record.englishName} · {record.owner}</Text>
        </Space>
      ),
    },
    {
      title: '类别',
      dataIndex: 'niceClasses',
      key: 'niceClasses',
      render: (items: string[]) => (
        <Space size={[4, 4]} wrap>{items.map((item, index) => <Tag key={`${item}-${index}`}>{item}</Tag>)}</Space>
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
      title: '风险分',
      dataIndex: 'riskScore',
      key: 'riskScore',
      sorter: (a, b) => a.riskScore - b.riskScore,
      render: (value: number, record) => (
        <Space direction="vertical" size={2} style={{ minWidth: 160 }}>
          <Tag color={riskColor[record.riskLevel]}>{riskLabel[record.riskLevel]}</Tag>
          <Progress percent={value} size="small" />
        </Space>
      ),
    },
    {
      title: '状态',
      dataIndex: 'portfolioStatus',
      key: 'portfolioStatus',
      render: (value: string) => <Tag color={value === '可提交' ? 'green' : value === '待改稿' ? 'red' : 'gold'}>{value}</Tag>,
    },
    {
      title: '下一步',
      dataIndex: 'nextAction',
      key: 'nextAction',
      render: (value: string) => <Text type="secondary">{value}</Text>,
    },
  ]

  return (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <div className="page-heading">
        <div>
          <Tag icon={<AppstoreOutlined />} color="blue">Portfolio</Tag>
          <Title level={2}>品牌资产库</Title>
          <Paragraph type="secondary">
            把单次审查升级成品牌组合管理：按类别、国家、风险分和下一步动作持续跟踪。
          </Paragraph>
        </div>
        <Button icon={<ArrowRightOutlined />} onClick={() => navigate('/submit')} type="primary">
          新增审查
        </Button>
      </div>

      <StaggerGroup>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <MotionItem><HoverLift><Card className="metric-card neon-card">
            <Space>
              <SafetyCertificateOutlined className="metric-icon" />
              <StatisticBlock label="资产总数" value={`${assets.length} 组`} />
            </Space>
          </Card></HoverLift></MotionItem>
        </Col>
        <Col xs={24} md={8}>
          <MotionItem><HoverLift><Card className="metric-card neon-card">
            <Space>
              <ExclamationCircleOutlined className="metric-icon danger" />
              <StatisticBlock label="待改稿/复核" value={`${assets.filter((item) => item.riskLevel !== 'low').length} 组`} />
            </Space>
          </Card></HoverLift></MotionItem>
        </Col>
        <Col xs={24} md={8}>
          <MotionItem><HoverLift><Card className="metric-card neon-card">
            <Space>
              <CheckCircleOutlined className="metric-icon success" />
              <StatisticBlock label="可直接推进" value={`${assets.filter((item) => item.portfolioStatus === '可提交').length} 组`} />
            </Space>
          </Card></HoverLift></MotionItem>
        </Col>
      </Row>
      </StaggerGroup>

      <Row gutter={[16, 16]}>
        {assets.map((item) => (
          <Col key={item.brandId} xs={24} lg={12} xl={6}>
            <HoverLift>
              <Card className={`asset-orbit-card risk-${item.riskLevel}`}>
                <Space direction="vertical" size={12} style={{ width: '100%' }}>
                  <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                    <Text strong>{item.name}</Text>
                    <Tag color={riskColor[item.riskLevel]}>{riskLabel[item.riskLevel]}</Tag>
                  </Space>
                  <div className="asset-orbit">
                    <span />
                    <strong>{item.riskScore}</strong>
                  </div>
                  <Text type="secondary">{item.englishName}</Text>
                  <Text>{item.nextAction}</Text>
                </Space>
              </Card>
            </HoverLift>
          </Col>
        ))}
      </Row>

      <Card title="资产明细" extra={<Text type="secondary">可按风险分排序</Text>}>
        {loading ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : assets.length ? (
          <Table<BrandAsset>
            columns={columns}
            dataSource={assets}
            pagination={{ pageSize: 8 }}
            rowKey="brandId"
            scroll={{ x: 980 }}
          />
        ) : (
          <ProductEmpty description="暂无品牌资产，完成审查后会自动沉淀到资产库。" />
        )}
      </Card>
    </Space>
  )
}

function StatisticBlock({ label, value }: { label: string; value: string }) {
  return (
    <Space direction="vertical" size={0}>
      <Text type="secondary">{label}</Text>
      <Text className="big-number">{value}</Text>
    </Space>
  )
}

export default BrandAssets
