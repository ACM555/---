import { Blob as NodeBlob } from 'node:buffer'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { downloadAuditPdf } from '@/api/audit'
import request from '@/api/request'

vi.mock('@/api/request', () => ({ default: { get: vi.fn(), post: vi.fn() } }))

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe('PDF 下载校验', () => {
  it('拒绝 HTTP 204 或空文件而不是下载零字节 PDF', async () => {
    vi.stubGlobal('Blob', NodeBlob)
    vi.mocked(request.get).mockResolvedValue(new NodeBlob([]))
    await expect(downloadAuditPdf('empty')).rejects.toThrow('服务器返回了空文件')
  })

  it('拒绝伪装为 PDF 的 JSON 或 HTML', async () => {
    vi.stubGlobal('Blob', NodeBlob)
    vi.mocked(request.get).mockResolvedValue(new NodeBlob(['{"error":"failed"}']))
    await expect(downloadAuditPdf('invalid')).rejects.toThrow('不是有效的 PDF')
  })

  it('有效 PDF 开始下载后再释放对象 URL', async () => {
    vi.stubGlobal('Blob', NodeBlob)
    vi.useFakeTimers()
    const createUrl = vi.fn().mockReturnValue('blob:test-pdf')
    const revokeUrl = vi.fn()
    vi.stubGlobal('URL', Object.assign(URL, { createObjectURL: createUrl, revokeObjectURL: revokeUrl }))
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)
    vi.mocked(request.get).mockResolvedValue(new NodeBlob(['%PDF-1.4\nvalid-test']))
    await downloadAuditPdf('valid')
    expect(click).toHaveBeenCalledOnce()
    expect(revokeUrl).not.toHaveBeenCalled()
    vi.advanceTimersByTime(1000)
    expect(revokeUrl).toHaveBeenCalledWith('blob:test-pdf')
  })
})
