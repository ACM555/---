import { CopyOutlined, DownloadOutlined } from '@ant-design/icons'
import { Button, Card, Empty, Space, Typography, message } from 'antd'

const { Paragraph, Text } = Typography

interface DocumentPreviewCardProps {
  brandName: string
  content: string
  title?: string
  emptyDescription?: string
  filenameSuffix?: string
}

function downloadMarkdown(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

function DocumentPreviewCard({
  brandName,
  content,
  title = 'M6 · 越南商标注册合规预检报告',
  emptyDescription = '暂无报告预览',
  filenameSuffix = '越南商标注册合规预检报告',
}: DocumentPreviewCardProps) {
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(content)
      message.success('报告内容已复制')
    } catch {
      message.error('复制失败，请手动选择文本复制')
    }
  }

  const handleDownload = () => {
    const safeName = brandName.trim() || 'outbound-guard-report'
    downloadMarkdown(`${safeName}-${filenameSuffix}.md`, content)
  }

  return (
    <Card
      title={title}
      extra={
        <Space>
          <Button disabled={!content} icon={<CopyOutlined />} onClick={handleCopy}>
            复制 Markdown
          </Button>
          <Button disabled={!content} icon={<DownloadOutlined />} onClick={handleDownload} type="primary">
            下载 .md
          </Button>
        </Space>
      }
    >
      {content ? (
        <div
          style={{
            background: '#fafafa',
            border: '1px solid #f0f0f0',
            borderRadius: 12,
            maxHeight: 520,
            overflow: 'auto',
            padding: 20,
          }}
        >
          {content.split('\n\n').map((paragraph) => {
            const isHeading = paragraph.startsWith('#')
            return (
              <Paragraph
                key={paragraph}
                style={{
                  fontSize: isHeading ? 16 : 14,
                  fontWeight: isHeading ? 700 : 400,
                  lineHeight: 1.8,
                  marginBottom: 14,
                  whiteSpace: 'pre-line',
                }}
              >
                {paragraph}
              </Paragraph>
            )
          })}
          <Text type="secondary">
            当前下载为 Markdown 预检报告；正式 PDF 排版模板将在后续阶段处理。
          </Text>
        </div>
      ) : (
        <Empty description={emptyDescription} />
      )}
    </Card>
  )
}

export default DocumentPreviewCard
