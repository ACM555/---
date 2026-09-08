import {
  AlertOutlined,
  ApiOutlined,
  AppstoreOutlined,
  BankOutlined,
  DatabaseOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  HomeOutlined,
  LogoutOutlined,
  SendOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Avatar, Button, Layout, Menu, Space, Tag, Typography } from 'antd'
import type { MenuProps } from 'antd'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { PageTransition } from '@/components/MotionKit'
import AiAssistant from '@/components/AiAssistant'

const { Content, Header, Sider } = Layout

function selectedKey(pathname: string) {
  if (pathname.startsWith('/assets')) return '/assets'
  if (pathname.startsWith('/submit')) return '/submit'
  if (pathname.startsWith('/reviewing')) return '/reviewing'
  if (pathname.startsWith('/reports') || pathname.startsWith('/report')) return '/reports'
  if (pathname.startsWith('/monitoring')) return '/monitoring'
  if (pathname.startsWith('/rules')) return '/rules'
  if (pathname.startsWith('/admin')) return '/admin'
  return '/'
}

function AppLayout() {
  const location = useLocation()
  const navigate = useNavigate()
  const { isAuthenticated, isAdmin, logout, user } = useAuth()

  const navigationItems: MenuProps['items'] = [
    { key: '/', icon: <HomeOutlined />, label: '风险工作台' },
    { key: '/assets', icon: <AppstoreOutlined />, label: '品牌资产' },
    { key: '/submit', icon: <SendOutlined />, label: '智能审查' },
    { key: '/reviewing', icon: <FileSearchOutlined />, label: '审查进度' },
    { key: '/reports', icon: <FileTextOutlined />, label: '报告中心' },
    { key: '/monitoring', icon: <AlertOutlined />, label: '监控预警' },
    { key: '/rules', icon: <DatabaseOutlined />, label: '规则库' },
    { key: '/engineering-screening', icon: <FileSearchOutlined />, label: '合规风险筛查' },
    ...(isAdmin ? [{ key: '/admin', icon: <BankOutlined />, label: '后台管理' }] : []),
  ]

  const handleLogout = async () => {
    await logout()
    navigate('/login')
  }

  return (
    <Layout className="app-shell">
      <div className="aurora-layer" aria-hidden="true" />
      <div className="grid-layer" aria-hidden="true" />
      <Sider className="app-sider" width={260} breakpoint="lg" collapsedWidth={0}>
        <div className="brand-block">
          <img alt="Outbound Guard" className="brand-mark-img" src="/assets/brand/outbound-guard-mark.svg" />
          <div>
            <Typography.Text strong>Outbound Guard</Typography.Text>
            <Typography.Text type="secondary">Trademark Risk OS</Typography.Text>
          </div>
        </div>
        <Menu
          className="side-menu"
          mode="inline"
          items={navigationItems}
          selectedKeys={[selectedKey(location.pathname)]}
          onClick={({ key }) => navigate(key)}
        />
        <div className="side-status">
          <Tag color="cyan">Live Product Mode</Tag>
          <Typography.Paragraph>
            覆盖注册前审查、组合资产管理、公告期监控、规则库和报告归档的完整产品闭环。
          </Typography.Paragraph>
        </div>
      </Sider>
      <Layout>
        <Header className="app-header">
          <Space size={12}>
            <Tag icon={<ApiOutlined />} color="geekblue">
              面向中国品牌出海东盟，融合商标预检、智能审查、报告与AI引导，帮助识别风险，提升跨境商标合规决策效率。
            </Tag>
          </Space>
          <Space size={12} wrap>
            <Button type="primary" onClick={() => navigate('/submit')}>
              新建审查
            </Button>
            {isAuthenticated ? (
              <>
                <Typography.Text type="secondary">{user?.company || user?.username}</Typography.Text>
                <Button aria-label="退出登录" icon={<LogoutOutlined />} onClick={handleLogout}>
                  退出
                </Button>
              </>
            ) : (
              <Button onClick={() => navigate('/login')}>登录 / 注册</Button>
            )}
            <Avatar icon={<UserOutlined />} />
          </Space>
        </Header>
        <Content className="app-content">
          <PageTransition>
            <Outlet />
          </PageTransition>
        </Content>
        <AiAssistant />
      </Layout>
    </Layout>
  )
}

export default AppLayout
