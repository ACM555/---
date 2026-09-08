import { Empty, Typography } from 'antd'

function ProductEmpty({ description = '暂无数据，完成一次智能审查后将自动沉淀。' }: { description?: string }) {
  return (
    <Empty
      description={<Typography.Text type="secondary">{description}</Typography.Text>}
      image="/assets/illustrations/empty-intel.svg"
      styles={{ image: { height: 150 } }}
    />
  )
}

export default ProductEmpty
