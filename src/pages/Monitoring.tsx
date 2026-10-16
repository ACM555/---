import { AlertOutlined, ClockCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { Alert, Button, Card, List, Skeleton, Space, Tag, Timeline, Typography } from 'antd'
import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import ProductEmpty from '@/components/ProductEmpty'
import PublicTrademarkSearch from '@/components/PublicTrademarkSearch'
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
    } catch {
      setAlerts([])
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
            检索合法开放的商标申请记录，跟踪已采集记录的变化；不自动判断商标冲突或异议期限。
          </Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={load}>
          刷新
        </Button>
      </div>

      <Alert type="info" showIcon message="当前接入新加坡官方许可开放的数据 API；原 IPOS 网页采集因缓存条款限制已暂停。首次收录不是新申请，采集时间不是官方发布时间；尚未覆盖 11 国全量商标库。" />

      <PublicTrademarkSearch />

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
                      {item.sourceUrl && <a href={item.sourceUrl} target="_blank" rel="noreferrer">查看官方原文</a>}
                      <Text type="secondary">{item.alertId} · {item.country} · {item.source}</Text>
                    </Space>
                    <Space>
                      <motion.span
                        animate={{ opacity: item.severity === 'high' ? [0.65, 1, 0.65] : 1 }}
                        className={`severity-pulse severity-${item.severity}`}
                        transition={{ duration: 1.8, repeat: item.severity === 'high' ? Infinity : 0 }}
                      >
                        <Tag color="blue">资料线索 · 未作法律评级</Tag>
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
                  <Text type="secondary">负责人：{item.owner} · 首次收录/变更观察时间：{item.createdAt} · 官方公布日期：{item.publicationDate || '未提供'}</Text>
                  {item.attribution && <Text type="secondary" style={{ overflowWrap: 'anywhere' }}>{item.attribution} {item.licenceUrl && <a href={item.licenceUrl} target="_blank" rel="noreferrer">开放数据许可</a>}</Text>}
                </Space>
              </List.Item>
            )}
          />
        ) : (
          <ProductEmpty description="尚无采集条目，请管理员核对数据源同步状态。" />
        )}
      </Card>
    </Space>
  )
}

export default Monitoring
