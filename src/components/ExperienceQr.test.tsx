import { cleanup, fireEvent, screen } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import ExperienceQr from '@/components/ExperienceQr'
import { renderWithProviders } from '@/test/render'
import { assetPath } from '@/utils/assetPath'

describe('ExperienceQr', () => {
  afterEach(cleanup)

  beforeEach(() => window.localStorage.clear())

  it('展示本地二维码，并提供图片下载入口', () => {
    renderWithProviders(<ExperienceQr />)
    const qrImage = assetPath('/teacher-experience-qr.png')
    expect(screen.getByRole('img', { name: '东盟跨境商事法律 AI 助手体验二维码' })).toHaveAttribute('src', qrImage)
    expect(screen.getByRole('link', { name: '下载二维码' })).toHaveAttribute('href', qrImage)
    expect(screen.getByRole('link', { name: '下载二维码' })).toHaveAttribute('download', '东盟法律AI助手-体验二维码.png')
  })

  it('可在当前设备直接打开体验页', () => {
    renderWithProviders(
      <Routes>
        <Route path="/" element={<ExperienceQr />} />
        <Route path="/experience" element={<h1>东盟体验页</h1>} />
      </Routes>,
    )
    fireEvent.click(screen.getByRole('button', { name: '打开体验入口' }))
    expect(screen.getByRole('heading', { name: '东盟体验页' })).toBeInTheDocument()
  })
})
