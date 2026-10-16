import { BlockOutlined, WarningOutlined } from '@ant-design/icons'
import { Card, Empty, Progress, Space, Tag, Typography } from 'antd'
import type { ReactNode } from 'react'
import type { HitRule } from '@/types/audit'

const { Paragraph, Text, Title } = Typography

interface HitRuleListProps {
  hitRules: HitRule[]
}

interface RuleGroupProps {
  icon: ReactNode
  rules: HitRule[]
  title: string
}

interface RuleCardProps {
  rule: HitRule
  showSimilarity?: boolean
}

function sortRules(rules: HitRule[]) {
  return [...rules].sort((a, b) => Number(b.applicable) - Number(a.applicable))
}

function RuleCard({ rule, showSimilarity = false }: RuleCardProps) {
  return (
    <Card
      size="small"
      style={{
        borderLeft: rule.applicable ? '4px solid #ff4d4f' : '4px solid #52c41a',
      }}
    >
      <Space direction="vertical" size={8} style={{ display: 'flex' }}>
        <Space wrap>
          <Text strong>{rule.article}</Text>
          <Tag color="orange">内部筛查规则 · 待核验{rule.ruleId ? ` · ${rule.ruleId}` : ''}</Tag>
          <Tag color={rule.applicable ? 'red' : 'green'}>
            {rule.applicable ? '触发' : '未触发'}
          </Tag>
        </Space>

        <Paragraph style={{ margin: 0 }}>{rule.content}</Paragraph>

        {showSimilarity && rule.similarityScore > 0 && (
          <div>
            <Text style={{ fontSize: 12 }} type="secondary">
              {rule.similarityType || '相似度评分'}
            </Text>
            <Progress
              percent={rule.similarityScore}
              size="small"
              status={rule.applicable ? 'exception' : 'normal'}
            />
          </div>
        )}

        <Paragraph style={{ fontSize: 13, margin: 0 }} type="secondary">
          风险线索说明：{rule.note || '暂无说明'}
        </Paragraph>
      </Space>
    </Card>
  )
}

function RuleGroup({ icon, rules, title }: RuleGroupProps) {
  const triggeredCount = rules.filter((rule) => rule.applicable).length
  const isRelative = rules.some((rule) => rule.ruleType === 'relative')

  return (
    <Space direction="vertical" size={12} style={{ display: 'flex' }}>
      <Title level={5} style={{ margin: 0 }}>
        <Space>
          {icon}
          <span>
            {title}（{triggeredCount}/{rules.length} 项触发）
          </span>
        </Space>
      </Title>

      {rules.length > 0 ? (
        rules.map((rule) => (
          <RuleCard key={`${rule.ruleType}-${rule.article}-${rule.note}`} rule={rule} showSimilarity={isRelative} />
        ))
      ) : (
        <Empty description={`暂无${title}`} />
      )}
    </Space>
  )
}

function HitRuleList({ hitRules }: HitRuleListProps) {
  if (hitRules.length === 0) {
    return <Empty description="暂无规则匹配结果" />
  }

  const absoluteRules = sortRules(hitRules.filter((rule) => rule.ruleType === 'absolute'))
  const relativeRules = sortRules(hitRules.filter((rule) => rule.ruleType === 'relative'))

  return (
    <Space direction="vertical" size={24} style={{ display: 'flex' }}>
      <RuleGroup icon={<BlockOutlined />} rules={absoluteRules} title="规则风险线索" />
      <RuleGroup icon={<WarningOutlined />} rules={relativeRules} title="权利与相似线索" />
    </Space>
  )
}

export default HitRuleList
