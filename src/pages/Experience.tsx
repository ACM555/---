import { useState, type CSSProperties } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Alert, Button, Card, Typography } from 'antd'
import { ArrowRightOutlined, FileSearchOutlined, FileTextOutlined, RobotOutlined } from '@ant-design/icons'
import { useAuth } from '@/context/AuthContext'
import { assetPath } from '@/utils/assetPath'

const steps = [
  { icon: <FileSearchOutlined />, title: '浏览六大模块', text: '查看投资、合同、贸易、用工、知识产权与争议解决的风险筛查入口。' },
  { icon: <FileTextOutlined />, title: '核验资料与报告', text: '检索可回查法律资料，提交材料进行初步筛查，并查看报告与复核提示。' },
  { icon: <RobotOutlined />, title: '问问 AI', text: '打开右下角 AI 助手，围绕东盟国家、业务场景和材料要求提问。' },
]

export default function Experience() {
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState('')
  const { loginAsGuest, isAuthenticated, loading } = useAuth()
  const navigate = useNavigate()

  const start = async () => {
    setStarting(true)
    setError('')
    try {
      if (!isAuthenticated) await loginAsGuest()
      navigate('/', { replace: true })
    } catch {
      setError('暂时无法进入体验，请点击重试。')
    } finally {
      setStarting(false)
    }
  }

  return (
    <main className="experience-shell" style={{
      '--experience-background': `url(${assetPath('/assets/photos/cross-border-business.webp')})`,
    } as CSSProperties}>
      <div className="experience-brand">
        <img src={assetPath('/assets/brand/outbound-guard-mark.svg')} alt="Outbound Guard" />
        <span>出海卫士 <small>东盟跨境商事法律 AI 助手</small></span>
      </div>
      <Card className="experience-card">
        <span className="experience-eyebrow">老师体验入口 · 无需注册</span>
        <Typography.Title>东盟跨境合规<br />扫码即刻体验</Typography.Title>
        <Typography.Paragraph type="secondary">
          无需账号密码，进入独立的游客评审空间，体验六模块风险筛查、法律资料检索、报告与 AI 问答。
        </Typography.Paragraph>
        <ol className="experience-steps">
          {steps.map((step, index) => <li key={step.title}>
            <span className="experience-step-icon">{step.icon}</span>
            <div><strong>{index + 1}. {step.title}</strong><p>{step.text}</p></div>
          </li>)}
        </ol>
        {error && <Alert type="error" showIcon message={error} />}
        <Button block type="primary" size="large" icon={<ArrowRightOutlined aria-hidden />} loading={starting || loading} disabled={starting || loading} onClick={() => void start()}>
          {error ? '重试进入体验' : '开始体验'}
        </Button>
        <Typography.Paragraph className="experience-note" type="secondary">
          每位游客拥有独立的任务空间。筛查与 AI 建议仅供初步参考，不构成法律意见。
        </Typography.Paragraph>
        <Link to="/login">已有账号？前往登录</Link>
      </Card>
    </main>
  )
}
