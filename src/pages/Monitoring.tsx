import { AlertOutlined, ClockCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { Button, Card, List, Skeleton, Space, Tag, Timeline, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import ProductEmpty from '@/components/ProductEmpty'
import { getMonitoringAlerts, type MonitoringAlert, type RiskLevel } from '@/api/saas'

const { Paragraph, Text, Title } = Typography

const severityColor: Record<RiskLevel, string> = {
  high: 'red',
  medium: 'orange',
  low: 'green',
}

function Monitoring() {
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([])
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try {
      setAlerts(await getMonitoringAlerts())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  return (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <div className="page-heading">
        <div>
          <Tag icon={<AlertOutlined />} color="red">Monitoring</Tag>
          <Title level={2}>监控预警中心</Title>
          <Paragraph type="secondary">
            从一次性审查延伸到注册后风控：公告期异议、抢注、法规变更和竞品动态统一进入队列。
          </Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={load}>
          刷新
        </Button>
      </div>

      <Card title="预警队列" extra={<Text type="secondary">{alerts.length} 条待跟踪</Text>}>
        {loading ? (
          <Skeleton active paragraph={{ rows: 8 }} />
        ) : alerts.length ? (
          <List
            itemLayout="vertical"
            dataSource={alerts}
            renderItem={(item) => (
              <List.Item className="alert-row">
                <Space direction="vertical" size={10} style={{ width: '100%' }}>
                  <Space align="start" style={{ justifyContent: 'space-between', width: '100%' }} wrap>
                    <Space direction="vertical" size={2}>
                      <Text strong>{item.title}</Text>
                      <Text type="secondary">{item.alertId} · {item.country} · {item.source}</Text>
                    </Space>
                    <Space>
                      <motion.span
                        animate={{ opacity: item.severity === 'high' ? [0.65, 1, 0.65] : 1 }}
                        className={`severity-pulse severity-${item.severity}`}
                        transition={{ duration: 1.8, repeat: item.severity === 'high' ? Infinity : 0 }}
                      >
                        <Tag color={severityColor[item.severity]}>{item.severity.toUpperCase()}</Tag>
                      </motion.span>
                      <Tag>{item.status}</Tag>
                    </Space>
                  </Space>
                  <Timeline
                    items={[
                      { color: severityColor[item.severity], children: `影响品牌：${item.brandName}` },
                      { color: 'blue', dot: <ClockCircleOutlined />, children: `处理窗口：${item.window}` },
                      { color: 'green', children: `建议动作：${item.recommendation}` },
                    ]}
                  />
                  <Text type="secondary">负责人：{item.owner} · 创建时间：{item.createdAt}</Text>
                </Space>
              </List.Item>
            )}
          />
        ) : (
          <ProductEmpty description="暂无监控预警，公告期与抢注风险会自动进入这里。" />
        )}
      </Card>
    </Space>
  )
}

export default Monitoring
