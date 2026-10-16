import { screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import Reviewing from '@/pages/Reviewing'
import { renderWithProviders } from '@/test/render'

vi.mock('@/api/audit', () => ({ getAuditResult: vi.fn() }))
vi.mock('@/api/saas', () => ({ getAuditTasks: vi.fn().mockResolvedValue([]) }))

describe('Reviewing', () => {
  it('没有任务 ID 时展示任务列表而不是错误', async () => {
    renderWithProviders(<Reviewing />, '/reviewing')

    expect(await screen.findByText('暂无审查任务，请先新建审查。')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: '审查任务' })).toBeInTheDocument()
    expect(screen.queryByText('缺少任务ID，请从提交页重新进入')).not.toBeInTheDocument()
  })
})
