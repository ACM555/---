import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import Report from '@/pages/Report'
import { renderWithProviders } from '@/test/render'

vi.mock('@/api/audit', () => ({ getAuditResult: vi.fn() }))

describe('Report', () => {
  it('缺少任务 ID 时引导用户重新提交', async () => {
    renderWithProviders(<Report />, '/report')

    expect(await screen.findByText('审查失败')).toBeInTheDocument()
    expect(screen.getByText('缺少任务ID，请从提交页重新进入')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '返回提交页重试' })).toBeInTheDocument()
  })
})
