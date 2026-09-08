import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import Submit from '@/pages/Submit'
import { renderWithProviders } from '@/test/render'

vi.mock('@/api', () => ({ audit: vi.fn() }))
vi.mock('@/api/platform', () => ({ getCountryRules: vi.fn().mockResolvedValue([]) }))

describe('Submit', () => {
  it('提交空表单时在对应字段附近显示校验错误', async () => {
    const user = userEvent.setup()
    renderWithProviders(<Submit />, '/submit')

    await user.click(screen.getByRole('button', { name: '提交审查' }))

    expect(await screen.findByText('请输入品牌名称')).toBeInTheDocument()
    expect(screen.getByText('请选择尼斯分类')).toBeInTheDocument()
    expect(screen.getByText('请输入商品/服务描述')).toBeInTheDocument()
    expect(screen.getByText('请上传品牌 Logo')).toBeInTheDocument()
  })
})
