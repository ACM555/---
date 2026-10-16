import { Alert, Button, Card, Descriptions, Input, List, Space, Tag, Typography } from 'antd'
import { useEffect, useRef, useState } from 'react'
import { explainPublicTrademark, getTrademarkWatches, searchPublicTrademarks, setTrademarkWatch, type PublicTrademarkExplanation, type PublicTrademarkRecord, type PublicTrademarkSearch as SearchResult } from '@/api/saas'

const { Paragraph, Text } = Typography

function PublicTrademarkSearch() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResult>()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [explanations, setExplanations] = useState<Record<string, PublicTrademarkExplanation>>({})
  const [explaining, setExplaining] = useState<string>()
  const [watches, setWatches] = useState<PublicTrademarkRecord[]>([])
  const [watching, setWatching] = useState<string>()
  const generation = useRef(0)

  useEffect(() => {
    let mounted = true
    getTrademarkWatches().then(records => { if (mounted) setWatches(records) }).catch(() => { if (mounted) setError('关注列表加载失败，请刷新重试。') })
    return () => { mounted = false }
  }, [])

  const toggleWatch = async (applicationNumber: string, active: boolean) => {
    setWatching(applicationNumber)
    try {
      await setTrademarkWatch(applicationNumber, active)
      setWatches(await getTrademarkWatches())
    } catch {
      setError('关注操作失败。每用户最多 10 条、系统最多 30 个不同申请号，请取消旧关注或稍后重试。')
    } finally {
      setWatching(undefined)
    }
  }

  const search = async (offset = 0) => {
    if (query.trim().length < 2) {
      setError('请输入至少 2 个字符的商标关键词。')
      return
    }
    const current = ++generation.current
    setLoading(true)
    setError('')
    setResult(undefined)
    setExplanations({})
    try {
      const response = await searchPublicTrademarks(query.trim(), offset)
      if (current === generation.current) setResult(response)
    } catch {
      if (current === generation.current) setError('官方数据检索暂不可用或已限流，请稍后重试。没有用演示数据代替。')
    } finally {
      if (current === generation.current) setLoading(false)
    }
  }

  const explain = async (applicationNumber: string) => {
    const current = generation.current
    setExplaining(applicationNumber)
    try {
      const response = await explainPublicTrademark(applicationNumber)
      if (current === generation.current) setExplanations(previous => ({ ...previous, [applicationNumber]: response }))
    } catch {
      if (current === generation.current) setError('AI 翻译暂不可用，仍可查看官方原始字段。')
    } finally {
      if (current === generation.current) setExplaining(undefined)
    }
  }

  return (
    <Card title="新加坡真实商标开放数据检索">
      <Space direction="vertical" size={16} style={{ width: '100%' }}>
        <Alert showIcon type="info" message="数据来自 IPOS 在 data.gov.sg 发布的开放申请记录；文字关键词匹配不是法律近似检索。AI 只辅助翻译，不判断可注册性或侵权。" />
        <Input.Search
          aria-label="新加坡商标关键词"
          placeholder="输入商标关键词，例如 Cloudring、Asterloom"
          value={query}
          maxLength={100}
          enterButton="检索官方数据"
          loading={loading}
          onSearch={() => search()}
          onChange={event => {
            generation.current += 1
            setQuery(event.target.value)
            setResult(undefined)
            setExplanations({})
            setExplaining(undefined)
            setLoading(false)
            setError('')
          }}
        />
        {error && <Alert showIcon type="error" message={error} />}
        <Text type="secondary">我的关注 {watches.length}/10：按申请号每 6 小时复查已关注记录；仅跟踪数据字段变更，不保证覆盖全部新申请。关注按用户隔离。</Text>
        {watches.length > 0 && <List size="small" dataSource={watches} renderItem={record => <List.Item extra={<Button size="small" loading={watching === record.applicationNumber} disabled={Boolean(watching)} onClick={() => toggleWatch(record.applicationNumber, false)}>取消关注</Button>}>
          <Space direction="vertical" size={2}><Text>{record.markName} · {record.applicationNumber}</Text><Text type="secondary">{record.status}；最近查询：{record.fetchedAt}</Text></Space>
        </List.Item>} />}
        {result && <>
          <Text>官方文字字段匹配共 {result.total.toLocaleString()} 条，本页 {result.records.length} 条。{result.cached ? '使用 6 小时内缓存。' : '本次实际查询官方接口。'}</Text>
          <Text type="secondary">数据集更新时间：{result.datasetUpdatedAt || '本次未核对'}；查询时间：{result.fetchedAt}</Text>
          <List
            dataSource={result.records}
            locale={{ emptyText: '本次未找到文字匹配记录；不表示没有在先权利或商标冲突。' }}
            renderItem={record => <List.Item key={record.applicationNumber}>
              <Space direction="vertical" size={10} style={{ width: '100%', overflowWrap: 'anywhere' }}>
                <Space wrap><Text strong>{record.markName}</Text><Tag>{record.status}</Tag><Tag color="blue">官方开放数据 · 非演示</Tag></Space>
                <Descriptions size="small" column={1} items={[
                  { key: 'number', label: '申请号', children: record.applicationNumber },
                  { key: 'classes', label: '类别', children: record.classes.join('、') || '未提供' },
                  { key: 'goods', label: '商品/服务原文', children: record.goodsServices.join('；') || '未提供' },
                  { key: 'dates', label: '原始日期', children: `申请：${record.applicationDate || '未提供'}；公布：${record.publicationDate || '未提供'}；状态日期：${record.statusDate || '未提供'}；记录修改：${record.officialModifiedAt || '未提供'}` },
                ]} />
                {record.goodsServicesTruncated && <Text type="secondary">商品服务仅展示前 12 项，请回查完整官方原文。</Text>}
                <Space wrap>
                  <a href={record.sourceUrl} target="_blank" rel="noreferrer">核对官方原始记录</a>
                  <Button size="small" loading={explaining === record.applicationNumber} disabled={Boolean(explaining)} onClick={() => explain(record.applicationNumber)}>AI 辅助翻译</Button>
                  <Button size="small" loading={watching === record.applicationNumber} disabled={Boolean(watching)} onClick={() => toggleWatch(record.applicationNumber, !watches.some(item => item.applicationNumber === record.applicationNumber))}>{watches.some(item => item.applicationNumber === record.applicationNumber) ? '取消关注' : '关注状态变化'}</Button>
                </Space>
                {explanations[record.applicationNumber] && <Alert type={explanations[record.applicationNumber].aiStatus === 'translated' ? 'info' : 'warning'} showIcon message={explanations[record.applicationNumber].message} description={<Space direction="vertical">
                  {explanations[record.applicationNumber].translations.map(item => <Text key={item.field}>{item.original} → {item.chinese}</Text>)}
                  <Text type="secondary">{explanations[record.applicationNumber].provider} / {explanations[record.applicationNumber].model}；翻译未经法律审核。</Text>
                </Space>} />}
              </Space>
            </List.Item>}
          />
          <Space wrap>
            <Button disabled={result.offset === 0} onClick={() => search(Math.max(0, result.offset - result.limit))}>上一页</Button>
            <Button disabled={!result.hasMore} onClick={() => search(result.offset + result.limit)}>下一页</Button>
            <a href={result.sourceUrl} target="_blank" rel="noreferrer">官方数据集</a>
            <a href={result.licenceUrl} target="_blank" rel="noreferrer">开放数据许可</a>
          </Space>
          <Paragraph type="secondary" style={{ overflowWrap: 'anywhere' }}>{result.attribution}</Paragraph>
          <Alert type="warning" showIcon message={result.boundary} />
        </>}
        <Text type="secondary">也可在 AI 助手输入“新加坡商标数据查询：关键词”取得带官方来源的事实与辅助翻译。</Text>
      </Space>
    </Card>
  )
}

export default PublicTrademarkSearch
