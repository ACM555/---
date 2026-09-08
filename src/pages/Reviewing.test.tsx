import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import Reviewing from '@/pages/Reviewing'
import { renderWithProviders } from '@/test/render'

vi.mock('@/api/audit', () => ({ getAuditResult: vi.fn() }))

describe('Reviewing', () => {
  it('缺少任务 ID 时提供可恢复的错误提示', async () => {
    renderWithProviders(<Reviewing />, '/reviewing')

    expect(await screen.findByText('审查失败')).toBeInTheDocument()
    expect(screen.getByText('缺少任务ID，请从提交页重新进入')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重新审查' })).toBeDisabled()
  })
})
