import {
  BankOutlined,
  FileTextOutlined,
  SolutionOutlined,
} from '@ant-design/icons'
import { Alert, Badge, Card, Collapse, Empty, Space, Tag, Typography } from 'antd'
import type { CollapseProps } from 'antd'
import type { ReactNode } from 'react'
import type { LegalReference } from '@/types/audit'

const { Paragraph, Text } = Typography

interface LegalReferenceCollapseProps {
  references: LegalReference[]
}

type RefType = LegalReference['refType']

interface RefTypeConfig {
  color: string
  icon: ReactNode
  label: string
}

const refTypeConfig: Record<RefType, RefTypeConfig> = {
  law: { icon: <FileTextOutlined />, label: '来源与规则说明', color: '#1677ff' },
  case: { icon: <SolutionOutlined />, label: '判例引用', color: '#722ed1' },
  trademark: { icon: <BankOutlined />, label: '商标记录', color: '#fa8c16' },
}

const refTypeOrder: RefType[] = ['law', 'case', 'trademark']

// 已通过项目法源审核的官方入口：official_law，或 approvalStatus 为 approved 的 official_pointer。
function isReviewedSource(reference: LegalReference): boolean {
  if (reference.sourceKind === 'official_law') return true
  return reference.sourceKind === 'official_pointer' && reference.approvalStatus === 'approved'
}

function ReferenceCard({ reference }: { reference: LegalReference }) {
  return (
    <Card size="small" style={{ marginBottom: 8 }}>
      <Space direction="vertical" size={6} style={{ display: 'flex' }}>
        <Text strong>{reference.title || '未命名依据'}</Text>
        <Tag color={isReviewedSource(reference) ? 'green' : 'orange'}>{reference.sourceKind === 'internal_rule' || reference.source.includes('rules_v1.json') ? '内部规则 · 不是正式法源' : isReviewedSource(reference) ? '已审核官方法源入口' : '资料线索 · 待核验'}</Tag>
        <Space size={16} wrap>
          <Text style={{ fontSize: 13 }} type="secondary">
            {reference.date ? `资料核验日期：${reference.date}` : '法源版本与日期尚未核验'}
          </Text>
          {reference.registrationNo && (
            <Text style={{ fontSize: 13 }} type="secondary">
              注册号：{reference.registrationNo}
            </Text>
          )}
          <Text style={{ fontSize: 13 }} type="secondary">
            来源：{reference.source || '未知来源'}
          </Text>
        </Space>
        {reference.version && <Text type="secondary">版本：{reference.version}</Text>}
        {reference.sourceUrl && /^https?:\/\//.test(reference.sourceUrl) && <a href={reference.sourceUrl} target="_blank" rel="noreferrer">查看官方原文</a>}
        {reference.locator && <Text>章节：{reference.locator}</Text>}
        {reference.originalText && <Paragraph>原文摘录：{reference.originalText}</Paragraph>}
        {reference.prerequisites?.length ? <Paragraph>适用条件：{reference.prerequisites.join('；')}</Paragraph> : null}
        <Paragraph ellipsis={{ rows: 3, expandable: true }} style={{ margin: 0 }}>
          {reference.summary || '暂无摘要'}
        </Paragraph>
        {reference.relevance && (
          <Alert message={reference.relevance} showIcon style={{ marginTop: 4 }} type="info" />
        )}
      </Space>
    </Card>
  )
}

function LegalReferenceCollapse({ references }: LegalReferenceCollapseProps) {
  if (references.length === 0) {
    return <Empty description="暂无法律依据" />
  }

  const groups = refTypeOrder
    .map((refType) => {
      const config = refTypeConfig[refType]
      const items = references.filter((reference) => reference.refType === refType)

      return {
        ...config,
        items,
        key: refType,
      }
    })
    .filter((group) => group.items.length > 0)

  if (groups.length === 0) {
    return <Empty description="暂无法律依据" />
  }

  const defaultActiveKey = groups.map((group) => group.key)
  const collapseItems: CollapseProps['items'] = groups.map((group) => ({
    key: group.key,
    label: (
      <Space>
        <span style={{ color: group.color }}>{group.icon}</span>
        <Text strong>{group.label}</Text>
        <Badge count={group.items.length} style={{ backgroundColor: group.color }} />
      </Space>
    ),
    children: (
      <Space direction="vertical" size={8} style={{ display: 'flex' }}>
        {group.items.map((reference) => (
          <ReferenceCard
            key={`${reference.refType}-${reference.title}-${reference.registrationNo}-${reference.date}`}
            reference={reference}
          />
        ))}
      </Space>
    ),
  }))

  return <Collapse defaultActiveKey={defaultActiveKey} items={collapseItems} />
}

export default LegalReferenceCollapse
