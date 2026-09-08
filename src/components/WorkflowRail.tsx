import {
  CheckCircleOutlined,
  FileSearchOutlined,
  FileTextOutlined,
  HistoryOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import { Button, Progress, Typography } from 'antd'
import { useLocation, useNavigate } from 'react-router-dom'

const workflowItems = [
  { key: 'submit', label: '资料提交', icon: <FileSearchOutlined /> },
  { key: 'reviewing', label: '风险审查', icon: <SafetyCertificateOutlined /> },
  { key: 'report', label: '证据与报告', icon: <FileTextOutlined /> },
  { key: 'history', label: '审计留痕', icon: <HistoryOutlined /> },
]

function getActiveStep(pathname: string) {
  if (pathname.startsWith('/report')) return 2
  if (pathname.startsWith('/reviewing')) return 1
  if (pathname.startsWith('/submit')) return 0
  return -1
}

function WorkflowRail() {
  const location = useLocation()
  const navigate = useNavigate()
  const activeStep = getActiveStep(location.pathname)
  const progress = activeStep < 0 ? 0 : Math.round(((activeStep + 1) / 3) * 100)

  return (
    <aside className="workflow-rail" aria-label="商标审查流程">
      <div>
        <Typography.Text className="workflow-eyebrow">商标审查流程</Typography.Text>
        <Typography.Title level={4} className="workflow-title">
          越南注册预审
        </Typography.Title>
        <Typography.Paragraph className="workflow-description">
          从资料提交到证据报告，所有结论均保留规则与来源依据。
        </Typography.Paragraph>
      </div>

      <div className="workflow-list">
        {workflowItems.map((item, index) => {
          const isComplete = activeStep > index || (activeStep === 2 && index === 2)
          const isActive = activeStep === index

          return (
            <div
              className={`workflow-item${isActive ? ' workflow-item--active' : ''}${isComplete ? ' workflow-item--complete' : ''}`}
              key={item.key}
            >
              <span className="workflow-item-icon">
                {isComplete ? <CheckCircleOutlined /> : item.icon}
              </span>
              <span>{item.label}</span>
            </div>
          )
        })}
      </div>

      <div className="workflow-status">
        <div className="workflow-status-row">
          <Typography.Text strong>当前进度</Typography.Text>
          <Typography.Text>{progress}%</Typography.Text>
        </div>
        <Progress
          aria-label={`商标审查进度 ${progress}%`}
          percent={progress}
          showInfo={false}
          strokeColor="#006a6a"
        />
        <Typography.Paragraph className="workflow-status-note">
          系统仅提供计算风险评估，正式申请前仍建议由商标专业人员复核。
        </Typography.Paragraph>
        <Button block onClick={() => navigate('/submit')}>
          发起新审查
        </Button>
      </div>
    </aside>
  )
}

export default WorkflowRail
