import {
  AlertOutlined,
  ArrowRightOutlined,
  AuditOutlined,
  BankOutlined,
  CheckCircleOutlined,
  CloudServerOutlined,
  DatabaseOutlined,
  FileProtectOutlined,
  FileTextOutlined,
  GlobalOutlined,
  MonitorOutlined,
  SafetyCertificateOutlined,
  SendOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons'
import {
  Alert,
  Button,
  Card,
  Col,
  Divider,
  List,
  Row,
  Skeleton,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd'
import { useEffect, useMemo, useState, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { assetPath } from '@/utils/assetPath'
import { HoverLift, MotionItem, StaggerGroup } from '@/components/MotionKit'
import ProductEmpty from '@/components/ProductEmpty'
import { getPlatformOverview, type PlatformOverview } from '@/api/platform'
import { getBrandAssets, getDataSourceStatus, getMonitoringAlerts } from '@/api/saas'
import type { BrandAsset, DataSourceStatus, MonitoringAlert } from '@/api/saas'

const { Paragraph, Text, Title } = Typography

const fallbackOverview: PlatformOverview = {
  positioning: '面向中国企业进入东盟市场的跨境商事法律 AI 助手',
  slogan: '六模块风险筛查、可回查资料与人工复核闭环',
  healthScore: 86,
  riskTrend: [],
  modules: [],
  dataSources: [],
  sla: [],
  businessModel: [],
}

const riskColor = {
  high: 'red',
  medium: 'orange',
  low: 'green',
} as const

const moduleIcons = [
  <AuditOutlined />,
  <FileProtectOutlined />,
  <GlobalOutlined />,
  <ThunderboltOutlined />,
  <AlertOutlined />,
  <FileTextOutlined />,
]

const primaryQuickActions = [
  {
    desc: '按国家、模块、场景和事实生成受控核验清单',
    icon: <SendOutlined />,
    path: '/engineering-screening',
    title: '发起合规筛查',
  },
  {
    desc: '查看品牌组合、风险等级和下一步动作',
    icon: <SafetyCertificateOutlined />,
    path: '/assets',
    title: '品牌资产库',
  },
  {
    desc: '查看演示预警队列与风险处理建议',
    icon: <MonitorOutlined />,
    path: '/monitoring',
    title: '监控预警',
  },
]

const portalNews = [
  {
    date: '07-19',
    tag: '规则动态',
    title: '越南公告期异议窗口进入高发周期，茶饮与餐饮服务建议提前准备证据链',
  },
  {
    date: '07-18',
    tag: '能力升级',
    title: 'M5 商标资料核验演示：整理权属、相似标识与人工复核事项',
  },
  {
    date: '07-18',
    tag: '数据源',
    title: 'WIPO、TMview、NOIP 与本地规则库完成统一健康度监控',
  },
  {
    date: '07-17',
    tag: '实务策略',
    title: '三国以上市场推荐“基础标 + 单国/马德里混合路径”降低申请成本',
  },
]

const strategyCards = [
  {
    cover: assetPath('/assets/photos/china-business-meeting.webp'),
    kicker: '报告归档',
    path: '/reports',
    title: '报告中心',
    text: '沉淀可复用、可归档、可交付的中英越文审查报告与代理人协作清单。',
  },
  {
    cover: assetPath('/assets/photos/china-city-data.webp'),
    kicker: '规则资料',
    path: '/rules',
    title: '国家规则库',
    text: '按越南、泰国、印尼、马来西亚等市场组织禁用条款、周期和提交策略。',
  },
  {
    cover: assetPath('/assets/photos/china-court-office.webp'),
    kicker: '品牌监控',
    path: '/assets',
    title: '品牌运营视图',
    text: '把品牌资产、监控事件和注册阶段打通，给评委看到完整业务闭环。',
  },
]

function formatAlertMeta(item: MonitoringAlert) {
  return `${item.country} · ${item.window} · ${item.owner}`
}

function handleCardKey(event: KeyboardEvent<HTMLElement>, action: () => void) {
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    action()
  }
}

function Home() {
  const navigate = useNavigate()
  const { isAdmin } = useAuth()
  const [overview, setOverview] = useState<PlatformOverview>(fallbackOverview)
  const [assets, setAssets] = useState<BrandAsset[]>([])
  const [alerts, setAlerts] = useState<MonitoringAlert[]>([])
  const [sources, setSources] = useState<DataSourceStatus[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let mounted = true

    Promise.all([
      getPlatformOverview(),
      getBrandAssets(),
      getMonitoringAlerts(),
      getDataSourceStatus(),
    ])
      .then(([nextOverview, nextAssets, nextAlerts, nextSources]) => {
        if (mounted) {
          setOverview(nextOverview)
          setAssets(nextAssets)
          setAlerts(nextAlerts)
          setSources(nextSources)
          setError(false)
        }
      })
      .catch(() => {
        if (mounted) {
          setError(true)
        }
      })
      .finally(() => {
        if (mounted) {
          setLoading(false)
        }
      })

    return () => {
      mounted = false
    }
  }, [])

  const highRiskAssets = assets.filter((item) => item.riskLevel === 'high').length
  const highAlerts = alerts.filter((item) => item.severity === 'high').length
  const featuredAlert = alerts[0]
  const moduleRows = useMemo(() => overview.modules.slice(0, 6), [overview.modules])
  const quickActions = useMemo(
    () => [
      ...primaryQuickActions,
      isAdmin
        ? {
            desc: '查看任务、用户、资料审核和系统运行状态',
            icon: <BankOutlined />,
            path: '/admin',
            title: '运营后台',
          }
        : {
            desc: '集中查看已完成的风险报告与归档材料',
            icon: <FileTextOutlined />,
            path: '/reports',
            title: '报告归档',
          },
    ],
    [isAdmin],
  )

  return (
    <Space direction="vertical" size={30} style={{ display: 'flex' }}>
      <section className="seu-hero portal-hero-cn">
        <div className="hero-scanline" aria-hidden="true" />
        <div className="hero-particles" aria-hidden="true">
          <span />
          <span />
          <span />
          <span />
        </div>

        <div className="seu-hero-content">
          <Tag className="seu-hero-tag">中国企业出海 · 东盟跨境商事法律 AI 助手</Tag>
          <Title level={1}>东盟跨境商事法律 AI 助手</Title>
          <Paragraph>
            {overview.positioning}，覆盖{overview.slogan}。用 AI 检索、法律规则和证据链报告，
            帮企业把跨境商事法律风险的资料依据、事实缺口与复核边界提前看清楚、讲明白。
          </Paragraph>
          <Space className="seu-hero-actions" size={12} wrap>
            <Button icon={<ArrowRightOutlined />} onClick={() => navigate('/engineering-screening')} size="large" type="primary">
              发起合规筛查
            </Button>
            <Button className="hero-secondary-btn" onClick={() => navigate('/reports')} size="large">
              查看报告中心
            </Button>
          </Space>
        </div>

        <div className="seu-hero-board">
          <Text className="board-kicker">DEMO OVERVIEW</Text>
          <strong>{overview.healthScore ?? 86}</strong>
          <span>演示运行指标</span>
          <Divider />
          <Space direction="vertical" size={8}>
            <Text>NOIP / WIPO / TMview 与本地资料核验入口</Text>
            <Text>高风险预警 {highAlerts} 条 · 资产库 {assets.length} 组</Text>
          </Space>
        </div>
      </section>

      {error ? (
        <Alert
          showIcon
          type="warning"
          message="部分平台数据暂时不可用"
          description="请确认后端服务已启动。当前页面保留门户展示，不影响继续发起审查。"
        />
      ) : null}

      <section className="seu-quick-section">
        <StaggerGroup>
          <Row gutter={[16, 16]}>
            {quickActions.map((item) => (
              <Col key={item.path} xs={24} sm={12} xl={6}>
                <MotionItem>
                  <HoverLift>
                    <Card
                      className="seu-quick-card"
                      onClick={() => navigate(item.path)}
                      onKeyDown={(event) => handleCardKey(event, () => navigate(item.path))}
                      role="button"
                      tabIndex={0}
                    >
                      <div className="quick-icon">{item.icon}</div>
                      <Title level={4}>{item.title}</Title>
                      <Paragraph>{item.desc}</Paragraph>
                    </Card>
                  </HoverLift>
                </MotionItem>
              </Col>
            ))}
          </Row>
        </StaggerGroup>
      </section>

      <section className="seu-news-section">
        <div className="section-titlebar seu-titlebar">
          <div>
            <Text className="section-kicker">演示动态 · 非实时监控</Text>
            <Title level={2}>风险队列样例</Title>
          </div>
          <Button type="link" onClick={() => navigate('/monitoring')}>
            更多预警
          </Button>
        </div>

        <Row gutter={[20, 20]}>
          <Col xs={24} xl={11}>
            <Card className="seu-feature-news">
              <Tag color={featuredAlert ? riskColor[featuredAlert.severity] : 'red'}>重点预警</Tag>
              <Title level={3}>{featuredAlert?.title ?? '越南公告期近似商标风险持续升温'}</Title>
              <Paragraph>
                {featuredAlert
                  ? `${formatAlertMeta(featuredAlert)}。建议立即完成证据链归档、图形改稿和代理人协作准备。`
                  : '系统会把公告期抢注、异议窗口和国际权利族信号整理为可执行动作，适合比赛现场演示。'}
              </Paragraph>
              <Button ghost onClick={() => navigate('/monitoring')}>
                查看处置建议
              </Button>
            </Card>
          </Col>
          <Col xs={24} xl={13}>
            <Card className="seu-news-list-card">
              <List
                dataSource={portalNews}
                renderItem={(item) => (
                  <List.Item className="seu-news-item">
                    <div className="news-date">{item.date}</div>
                    <div>
                      <Tag color="blue">{item.tag}</Tag>
                      <Text strong>{item.title}</Text>
                    </div>
                  </List.Item>
                )}
              />
            </Card>
          </Col>
        </Row>
      </section>

      <section className="portal-section seu-capability-section">
        <div className="section-titlebar seu-titlebar">
          <div>
            <Text className="section-kicker">核心能力</Text>
            <Title level={2}>M1-M6 能力栏目</Title>
          </div>
          <Tag color="green">六大模块已接入演示链路</Tag>
        </div>
        {loading ? (
          <Card>
            <Skeleton active paragraph={{ rows: 8 }} />
          </Card>
        ) : moduleRows.length ? (
          <Row gutter={[18, 18]}>
            {moduleRows.map((item, index) => (
              <Col key={item.key} xs={24} md={12} xl={8}>
                <HoverLift>
                  <Card
                    className="seu-channel-card"
                    onClick={() => navigate(`/engineering-screening?module=${item.key}`)}
                    onKeyDown={(event) => handleCardKey(event, () => navigate(`/engineering-screening?module=${item.key}`))}
                    role="button"
                    tabIndex={0}
                  >
                    <div className="channel-index">{String(index + 1).padStart(2, '0')}</div>
                    <div className="channel-icon">{moduleIcons[index] ?? <CheckCircleOutlined />}</div>
                    <Text className="channel-key">{item.key}</Text>
                    <Title level={4}>{item.name}</Title>
                    <Paragraph>{item.output}</Paragraph>
                    <Space size={[6, 6]} wrap>
                      {item.features.slice(0, 4).map((feature) => (
                        <Tag key={feature}>{feature}</Tag>
                      ))}
                    </Space>
                  </Card>
                </HoverLift>
              </Col>
            ))}
          </Row>
        ) : (
          <ProductEmpty description="暂无模块数据" />
        )}
      </section>

      <Row gutter={[20, 20]}>
        {strategyCards.map((item) => (
          <Col key={item.title} xs={24} lg={8}>
            <Card
              className="seu-image-channel"
              cover={<img alt={item.title} loading="lazy" src={item.cover} />}
              onClick={() => navigate(item.path)}
              onKeyDown={(event) => handleCardKey(event, () => navigate(item.path))}
              role="button"
              tabIndex={0}
            >
              <Text className="section-kicker">{item.kicker}</Text>
              <Title level={4}>{item.title}</Title>
              <Paragraph>{item.text}</Paragraph>
            </Card>
          </Col>
        ))}
      </Row>

      <section className="seu-data-band">
        <div>
          <Text className="section-kicker">平台运行概览</Text>
          <Title level={2}>企业级法律科技 SaaS</Title>
          <Paragraph>把注册前预检、跨类保护、公告期监控和报告归档整合为一套可测试、可交付、可持续运营的产品。</Paragraph>
        </div>
        <Row gutter={[18, 18]}>
          <Col xs={12} lg={6}>
            <Statistic title="品牌资产" value={assets.length} suffix="组" prefix={<SafetyCertificateOutlined />} />
          </Col>
          <Col xs={12} lg={6}>
            <Statistic title="高风险资产" value={highRiskAssets} suffix="组" prefix={<FileProtectOutlined />} />
          </Col>
          <Col xs={12} lg={6}>
            <Statistic title="活跃预警" value={alerts.length} suffix="条" prefix={<AlertOutlined />} />
          </Col>
          <Col xs={12} lg={6}>
            <Statistic title="数据源" value={sources.length || overview.dataSources.length} suffix="路" prefix={<DatabaseOutlined />} />
          </Col>
        </Row>
        <div className="seu-data-sources">
          {(sources.length ? sources : overview.dataSources).slice(0, 4).map((item) => (
            <Tag key={typeof item === 'string' ? item : item.name} icon={<CloudServerOutlined />}>
              {typeof item === 'string' ? item : `${item.name} · ${item.freshness}`}
            </Tag>
          ))}
        </div>
      </section>
    </Space>
  )
}

export default Home
