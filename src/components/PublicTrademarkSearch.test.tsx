import { act, cleanup, fireEvent, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PublicTrademarkSearch from '@/components/PublicTrademarkSearch'
import { getTrademarkWatches, searchPublicTrademarks } from '@/api/saas'
import { renderWithProviders } from '@/test/render'

vi.mock('@/api/saas', () => ({
  getTrademarkWatches: vi.fn().mockResolvedValue([]),
  searchPublicTrademarks: vi.fn(),
  explainPublicTrademark: vi.fn(),
  setTrademarkWatch: vi.fn(),
}))

const emptyResult = {
  query: 'Cloudring', records: [], total: 0, offset: 0, limit: 10, hasMore: false,
  fetchedAt: '2026-10-15T01:00:00Z', cached: false,
  boundary: '无结果不表示不存在冲突。', sourceUrl: 'https://data.gov.sg/',
  licenceUrl: 'https://data.gov.sg/open-data-licence', attribution: 'Singapore Open Data Licence',
}

describe('PublicTrademarkSearch', () => {
  afterEach(cleanup)
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(getTrademarkWatches).mockResolvedValue([])
  })

  it('零结果仍提醒需核对在先权利', async () => {
    vi.mocked(searchPublicTrademarks).mockResolvedValue(emptyResult)
    renderWithProviders(<PublicTrademarkSearch />)
    fireEvent.change(screen.getByRole('searchbox', { name: '新加坡商标关键词' }), { target: { value: 'Cloudring' } })
    fireEvent.click(screen.getByRole('button', { name: '检索官方数据' }))
    expect(await screen.findByText('本次未找到文字匹配记录；不表示没有在先权利或商标冲突。')).toBeInTheDocument()
    expect(screen.getByText('无结果不表示不存在冲突。')).toBeInTheDocument()
  })

  it('检索失败不回退到演示记录', async () => {
    vi.mocked(searchPublicTrademarks).mockRejectedValue(new Error('unavailable'))
    renderWithProviders(<PublicTrademarkSearch />)
    fireEvent.change(screen.getByRole('searchbox', { name: '新加坡商标关键词' }), { target: { value: 'Asterloom' } })
    fireEvent.click(screen.getByRole('button', { name: '检索官方数据' }))
    expect(await screen.findByText('官方数据检索暂不可用或已限流，请稍后重试。没有用演示数据代替。')).toBeInTheDocument()
  })

  it('改动输入后旧请求不会恢复结果', async () => {
    let resolve: (value: typeof emptyResult) => void = () => {}
    vi.mocked(searchPublicTrademarks).mockReturnValue(new Promise(accept => { resolve = accept }))
    renderWithProviders(<PublicTrademarkSearch />)
    const input = screen.getByRole('searchbox', { name: '新加坡商标关键词' })
    fireEvent.change(input, { target: { value: 'Cloudring' } })
    fireEvent.click(screen.getByRole('button', { name: '检索官方数据' }))
    fireEvent.change(input, { target: { value: 'Asterloom' } })
    await act(async () => { resolve(emptyResult) })
    expect(screen.queryByText('本次未找到文字匹配记录；不表示没有在先权利或商标冲突。')).not.toBeInTheDocument()
    expect(input).toHaveValue('Asterloom')
  })
})
