import { screen } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import Home from '@/pages/Home'
import { renderWithProviders } from '@/test/render'
import { getPlatformOverview } from '@/api/platform'
import { getBrandAssets, getDataSourceStatus, getMonitoringAlerts } from '@/api/saas'

vi.mock('@/api/platform', () => ({ getPlatformOverview: vi.fn() }))
vi.mock('@/api/saas', () => ({
  getBrandAssets: vi.fn(),
  getDataSourceStatus: vi.fn(),
  getMonitoringAlerts: vi.fn(),
}))

describe('Home', () => {
  beforeEach(() => {
    vi.mocked(getPlatformOverview).mockResolvedValue({ positioning: '测试定位', slogan: '测试口号', healthScore: 90, modules: [], dataSources: [], sla: [], businessModel: [] })
    vi.mocked(getBrandAssets).mockResolvedValue([])
    vi.mocked(getMonitoringAlerts).mockResolvedValue([])
    vi.mocked(getDataSourceStatus).mockResolvedValue([])
  })

  it('读取平台概览并展示核心入口', async () => {
    renderWithProviders(<Home />)

    expect(await screen.findByText(/测试定位/)).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /发起智能审查/ }).length).toBeGreaterThan(0)
  })
})
