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
  MenuOutlined,
  SendOutlined,
  UserOutlined,
} from '@ant-design/icons'
import { Avatar, Button, Drawer, Layout, Menu, Space, Tag, Typography } from 'antd'
import type { MenuProps } from 'antd'
import { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'
import { PageTransition } from '@/components/MotionKit'
import AiAssistant from '@/components/AiAssistant'
import { assetPath } from '@/utils/assetPath'

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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
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

  const handleNavigate = (path: string) => {
    setMobileMenuOpen(false)
    navigate(path)
  }

  const navigationMenu = (
    <Menu
      className="side-menu"
      mode="inline"
      items={navigationItems}
      selectedKeys={[selectedKey(location.pathname)]}
      onClick={({ key }) => handleNavigate(key)}
    />
  )

  return (
    <Layout className="app-shell">
      <div className="aurora-layer" aria-hidden="true" />
      <div className="grid-layer" aria-hidden="true" />
      <Sider className="app-sider" width={260} breakpoint="lg" collapsedWidth={0}>
        <div className="brand-block">
          <img
            alt="Outbound Guard"
            className="brand-mark-img"
            src={assetPath('/assets/brand/outbound-guard-mark.svg')}
          />
          <div>
            <Typography.Text strong>Outbound Guard</Typography.Text>
            <Typography.Text type="secondary">ASEAN Legal AI</Typography.Text>
          </div>
        </div>
        {navigationMenu}
        <div className="side-status">
          <Tag color="cyan">Live Product Mode</Tag>
          <Typography.Paragraph>
            覆盖注册前审查、组合资产管理、公告期监控、规则库和报告归档的完整产品闭环。
          </Typography.Paragraph>
        </div>
      </Sider>
      <Layout>
        <Header className="app-header">
          <div className="mobile-header-brand">
            <Button
              aria-label="打开导航菜单"
              icon={<MenuOutlined />}
              onClick={() => setMobileMenuOpen(true)}
              type="text"
            />
            <img alt="Outbound Guard" src={assetPath('/assets/brand/outbound-guard-mark.svg')} />
            <div>
              <Typography.Text strong>Outbound Guard</Typography.Text>
              <Typography.Text type="secondary">东盟法律风控工作台</Typography.Text>
            </div>
          </div>
          <Space className="header-product-note" size={12}>
            <Tag icon={<ApiOutlined />} color="geekblue">
              注册前预检 · 跨类保护 · 公告监控 · 报告归档
            </Tag>
          </Space>
          <Space className="header-actions" size={10}>
            <Button className="header-primary-action" type="primary" onClick={() => navigate('/submit')}>
              新建审查
            </Button>
            {isAuthenticated ? (
              <>
                <Tag className="header-user-tag" color={user?.username.startsWith('judge_guest_') ? 'green' : 'blue'}>
                  {user?.company || user?.username}
                </Tag>
                <Button aria-label="退出登录" icon={<LogoutOutlined />} onClick={handleLogout} type="text">
                  <span className="header-logout-text">退出</span>
                </Button>
              </>
            ) : (
              <Button onClick={() => navigate('/login')}>登录 / 注册</Button>
            )}
            <Avatar className="header-avatar" icon={<UserOutlined />} />
          </Space>
        </Header>
        <Content className="app-content" id="main-content">
          <PageTransition>
            <Outlet />
          </PageTransition>
        </Content>
        <AiAssistant />
      </Layout>
      <Drawer
        className="mobile-nav-drawer"
        onClose={() => setMobileMenuOpen(false)}
        open={mobileMenuOpen}
        placement="left"
        title={
          <div className="mobile-drawer-brand">
            <img alt="Outbound Guard" src={assetPath('/assets/brand/outbound-guard-mark.svg')} />
            <div>
              <Typography.Text strong>Outbound Guard</Typography.Text>
              <Typography.Text type="secondary">企业级法律科技 SaaS</Typography.Text>
            </div>
          </div>
        }
        width={320}
      >
        {navigationMenu}
        <div className="mobile-drawer-footer">
          <Tag color="green">{user?.company || '已登录'}</Tag>
          <Button block icon={<LogoutOutlined />} onClick={handleLogout}>
            退出当前账号
          </Button>
        </div>
      </Drawer>
    </Layout>
  )
}

export default AppLayout
