import {
  AuditOutlined,
  CheckCircleOutlined,
  LoadingOutlined,
  SafetyOutlined,
} from '@ant-design/icons'
import { Button, Card, Progress, Result, Space, Spin, Steps, Typography } from 'antd'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { getAuditResult } from '@/api/audit'

const { Paragraph, Text, Title } = Typography

type ReviewingRouteState = {
  taskId?: string
}

type ReviewingStatus = 'loading' | 'success' | 'error' | 'timeout'

const reviewSteps = [
  {
    title: '规则与资料线索整理',
    description: '整理本地规则与可回查资料线索，不作主管机关结论',
  },
  {
    title: '图样辅助比对',
    description: '图像特征仅用于资料整理与人工复核提示',
  },
  {
    title: '权利线索核验',
    description: '整理在先权利与公共标志线索，需核验权利状态与适用范围',
  },
  {
    title: '场景风险提示',
    description: '提示标识、场景与资料缺口，具体适用性须人工复核',
  },
  {
    title: '风险提示清单生成',
    description: '汇总风险线索、待补事实与建议动作，不作结果判断',
  },
]

function Reviewing() {
  const navigate = useNavigate()
  const location = useLocation()
  const taskId = (location.state as ReviewingRouteState | null)?.taskId
  const [currentStep, setCurrentStep] = useState(0)
  const [status, setStatus] = useState<ReviewingStatus>('loading')
  const [errorMsg, setErrorMsg] = useState('')
  const [progress, setProgress] = useState(0)
  const timerRef = useRef<number | null>(null)
  const navigateTimerRef = useRef<number | null>(null)
  const startTimeRef = useRef(Date.now())

  const clearTimers = useCallback(() => {
    if (timerRef.current) {
      window.clearTimeout(timerRef.current)
      timerRef.current = null
    }

    if (navigateTimerRef.current) {
      window.clearTimeout(navigateTimerRef.current)
      navigateTimerRef.current = null
    }
  }, [])

  const poll = useCallback(async () => {
    if (!taskId) {
      setStatus('error')
      setErrorMsg('缺少任务ID，请从提交页重新进入')
      return
    }

    if (Date.now() - startTimeRef.current > 60000) {
      clearTimers()
      setStatus('timeout')
      return
    }

    try {
      const result = await getAuditResult(taskId)
      const nextStep = Math.min(result.currentStep ?? 0, reviewSteps.length - 1)
      const nextProgress =
        result.progress || Math.round(((nextStep + 1) / reviewSteps.length) * 100)

      setCurrentStep(nextStep)
      setProgress(nextProgress)

      if (result.status === 'done') {
        clearTimers()
        setStatus('success')
        setCurrentStep(reviewSteps.length - 1)
        setProgress(100)
        navigateTimerRef.current = window.setTimeout(() => {
          navigate(`/report/${taskId}`, { state: { taskId } })
        }, 800)
        return
      }

      if (result.status === 'error') {
        clearTimers()
        setStatus('error')
        setErrorMsg(result.errorMessage || result.summary?.overallResult || '审查过程中发生未知错误')
        return
      }

      timerRef.current = window.setTimeout(poll, 2000)
    } catch {
      clearTimers()
      setStatus('error')
      setErrorMsg('网络请求失败，请确认后端服务已启动')
    }
  }, [clearTimers, navigate, taskId])

  const handleRetry = () => {
    clearTimers()
    startTimeRef.current = Date.now()
    setCurrentStep(0)
    setProgress(0)
    setErrorMsg('')
    setStatus('loading')
    poll()
  }

  useEffect(() => {
    startTimeRef.current = Date.now()
    poll()

    return clearTimers
  }, [clearTimers, poll])

  const stepItems = reviewSteps.map((step, index) => {
    const isFinished = status === 'success' || currentStep > index
    const isCurrent = status === 'loading' && currentStep === index

    return {
      title: step.title,
      description: step.description,
      icon: isFinished ? (
        <CheckCircleOutlined style={{ color: '#52c41a' }} />
      ) : isCurrent ? (
        <LoadingOutlined style={{ color: '#1677ff' }} />
      ) : (
        <AuditOutlined />
      ),
    }
  })

  if (status === 'error') {
    return (
      <Result
        status="error"
        title="审查失败"
        subTitle={errorMsg || '审查过程中发生未知错误'}
        extra={[
          <Button type="primary" key="retry" onClick={handleRetry} disabled={!taskId}>
            重新审查
          </Button>,
          <Button key="submit" onClick={() => navigate('/submit')}>
            返回修改
          </Button>,
        ]}
      />
    )
  }

  if (status === 'timeout') {
    return (
      <Result
        status="warning"
        title="审查超时"
        subTitle="服务器响应时间超过 60 秒，可能由于网络延迟或服务负载过高"
        extra={[
          <Button type="primary" key="retry" onClick={handleRetry}>
            重新审查
          </Button>,
          <Button key="submit" onClick={() => navigate('/submit')}>
            返回提交页
          </Button>,
        ]}
      />
    )
  }

  return (
    <Card style={{ margin: '48px auto', maxWidth: 640 }}>
      <Space direction="vertical" size={28} style={{ display: 'flex' }}>
        <div style={{ textAlign: 'center' }}>
          <Spin
            spinning={status === 'loading'}
            indicator={<LoadingOutlined style={{ fontSize: 32 }} spin />}
          >
            <SafetyOutlined
              style={{
                color: status === 'success' ? '#52c41a' : '#1677ff',
                fontSize: 52,
                marginBottom: 16,
              }}
            />
          </Spin>
          <Title level={2} style={{ margin: '12px 0 8px' }}>
            {status === 'success' ? '审查完成' : 'AI 合规审查中...'}
          </Title>
          <Text type="secondary">
            {status === 'success' ? '审查完成，正在跳转报告页...' : '预计耗时 3-5 秒，请勿关闭页面'}
          </Text>
        </div>

        <Progress
          percent={progress}
          status={status === 'success' ? 'success' : 'active'}
          strokeColor={status === 'success' ? '#52c41a' : '#1677ff'}
        />

        <Steps current={currentStep} direction="vertical" items={stepItems} />

        <Paragraph type="secondary" style={{ margin: 0, textAlign: 'center' }}>
          {taskId ? `任务ID：${taskId}` : '正在等待任务ID'}
        </Paragraph>
      </Space>
    </Card>
  )
}

export default Reviewing
