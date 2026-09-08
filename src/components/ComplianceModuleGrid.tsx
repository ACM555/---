import {
  BellOutlined,
  DeploymentUnitOutlined,
  EyeOutlined,
  FileDoneOutlined,
  GlobalOutlined,
  SafetyCertificateOutlined,
} from '@ant-design/icons'
import { Card, Col, Progress, Row, Space, Typography } from 'antd'
import type { ReactNode } from 'react'
import type { AuditResult } from '@/types/audit'

const { Paragraph, Text, Title } = Typography

interface ModuleConfig {
  key: string
  title: string
  subtitle: string
  color: string
  icon: ReactNode
  description: string
}

interface ComplianceModuleGridProps {
  result?: AuditResult | null
}

const modules: ModuleConfig[] = [
  {
    key: 'M1',
    title: 'M1 · 外商投资准入与公司设立',
    subtitle: '主体、行业与准入核验',
    color: '#1677ff',
    icon: <SafetyCertificateOutlined />,
    description: '核验主体类型、行业限制、股权控制、项目地点与许可登记前提。',
  },
  {
    key: 'M2',
    title: 'M2 · 跨境商事合同审查',
    subtitle: '合同与违约风险防控',
    color: '#ff4d4f',
    icon: <EyeOutlined />,
    description: '核验适用法、交付付款、通知、争议解决及违约事实证据。',
  },
  {
    key: 'M3',
    title: 'M3 · 货物运输与贸易合规',
    subtitle: '运输、清关与单证核验',
    color: '#faad14',
    icon: <GlobalOutlined />,
    description: '核验货物、路线、贸易术语、清关主体、原产地与许可单证。',
  },
  {
    key: 'M4',
    title: 'M4 · 劳动用工与签证合规',
    subtitle: '派驻、准证与劳动关系',
    color: '#722ed1',
    icon: <DeploymentUnitOutlined />,
    description: '核验雇主、岗位、地点、国籍、工作许可、合同与社会保障。',
  },
  {
    key: 'M5',
    title: 'M5 · 知识产权与技术保护',
    subtitle: '商标、专利、技术与权属',
    color: '#13c2c2',
    icon: <BellOutlined />,
    description: '核验权利类型、权属、申请状态、公开边界与许可合作安排。',
  },
  {
    key: 'M6',
    title: 'M6 · 争议解决与货款追偿',
    subtitle: '争议条款、证据与执行核验',
    color: '#52c41a',
    icon: <FileDoneOutlined />,
    description: '核验适用法、仲裁地/法院、送达、资产、证据、时效与保全。',
  },
]

function getModuleMetric(moduleKey: string, result?: AuditResult | null) {
  if (!result) {
    return null
  }

  if (moduleKey === 'M1') {
    return { label: '综合风险', value: result.riskScore }
  }
  if (moduleKey === 'M2') {
    const relativeCount = result.hitRules.filter((rule) => rule.ruleType === 'relative' && rule.applicable).length
    return { label: '冲突线索', value: Math.min(relativeCount * 34, 100), text: `${relativeCount} 项` }
  }
  if (moduleKey === 'M3') {
    const absoluteCount = result.hitRules.filter((rule) => rule.ruleType === 'absolute' && rule.applicable).length
    return { label: '硬规则命中', value: Math.min(absoluteCount * 25, 100), text: `${absoluteCount} 项` }
  }
  if (moduleKey === 'M6') {
    return { label: '报告生成', value: result.advice.documentPreview ? 100 : 0 }
  }
  return null
}

function ComplianceModuleGrid({ result }: ComplianceModuleGridProps) {
  return (
    <Row gutter={[16, 16]}>
      {modules.map((module) => {
        const metric = getModuleMetric(module.key, result)

        return (
          <Col key={module.key} xs={24} md={12} xl={8}>
            <Card style={{ height: '100%' }}>
              <Space direction="vertical" size={12} style={{ display: 'flex' }}>
                <Space align="start" style={{ justifyContent: 'space-between', width: '100%' }}>
                  <Space align="start" size={12}>
                    <div
                      style={{
                        alignItems: 'center',
                        background: `${module.color}14`,
                        borderRadius: 12,
                        color: module.color,
                        display: 'flex',
                        fontSize: 24,
                        height: 48,
                        justifyContent: 'center',
                        width: 48,
                      }}
                    >
                      {module.icon}
                    </div>
                    <div>
                      <Title level={5} style={{ margin: 0 }}>
                        {module.title}
                      </Title>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        {module.subtitle}
                      </Text>
                    </div>
                  </Space>
                </Space>

                <Paragraph type="secondary" style={{ margin: 0, minHeight: 44 }}>
                  {module.description}
                </Paragraph>

                {metric ? (
                  <div>
                    <Space style={{ justifyContent: 'space-between', width: '100%' }}>
                      <Text type="secondary">{metric.label}</Text>
                      <Text strong>{metric.text ?? `${metric.value}/100`}</Text>
                    </Space>
                    <Progress percent={metric.value} showInfo={false} strokeColor={module.color} />
                  </div>
                ) : (
                  <Text type="secondary" style={{ fontSize: 12 }}>
                    {result ? '本模块展示对应的产品能力入口。' : '将在审查报告中展示对应能力。'}
                  </Text>
                )}
              </Space>
            </Card>
          </Col>
        )
      })}
    </Row>
  )
}

export default ComplianceModuleGrid
