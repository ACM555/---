import { Alert, Card, List, Space, Typography } from 'antd'
import type { ScenarioChecklist } from '@/api/legal'

export default function ScenarioChecklistCard({ checklist }: { checklist: ScenarioChecklist }) {
  return <Card title={checklist.title}>
    <Space direction="vertical" size={12} style={{ display: 'flex' }}>
      <Alert type="warning" showIcon message="官方指南资料核对演示 · 法条内容仍待审核" description={checklist.limitations.join('；')} />
      <Typography.Text>{checklist.sourceVersion}；资料核对日期：{checklist.checkedAt}</Typography.Text>
      <Typography.Text type="secondary">{checklist.lawVersion}</Typography.Text>
      <Typography.Paragraph>适用前提：{checklist.prerequisites.join('；')}</Typography.Paragraph>
      <List dataSource={checklist.checks} renderItem={item => <List.Item><Space direction="vertical" size={4}>
        <Typography.Text strong>{item.item}</Typography.Text>
        <Typography.Text>{item.output}</Typography.Text>
        <Typography.Text type="secondary">官方页面定位：{item.locator}</Typography.Text>
      </Space></List.Item>} />
      <Space wrap><a href={checklist.sourceUrl} target="_blank" rel="noreferrer">回查官方指南原文</a><a href={checklist.lawUrl} target="_blank" rel="noreferrer">回查商标法原文及现行版本</a><a href={checklist.searchUrl} target="_blank" rel="noreferrer">前往官方检索入口</a></Space>
    </Space>
  </Card>
}
