import { cleanup, fireEvent, screen, waitFor } from '@testing-library/react'
import { Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getMe, guestLogin } from '@/api/auth'
import Experience from '@/pages/Experience'
import { renderWithProviders } from '@/test/render'

vi.mock('@/api/auth', () => ({
  getMe: vi.fn(),
  guestLogin: vi.fn(),
  login: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}))

const guest = {
  userId: 'guest-id',
  username: 'judge_guest_test',
  role: 'user' as const,
  company: '评委游客体验',
  createdAt: '2026-10-13T00:00:00Z',
}

function renderExperience() {
  return renderWithProviders(
    <Routes>
      <Route path="/experience" element={<Experience />} />
      <Route path="/" element={<h1>体验工作台</h1>} />
      <Route path="/login" element={<h1>账号登录</h1>} />
    </Routes>,
    '/experience',
  )
}

describe('Experience', () => {
  afterEach(cleanup)

  beforeEach(() => {
    vi.clearAllMocks()
    window.localStorage.clear()
    vi.mocked(getMe).mockResolvedValue(guest)
    vi.mocked(guestLogin).mockResolvedValue({ token: 'guest-token', user: guest })
  })

  it('无需注册即可创建游客会话并进入工作台', async () => {
    renderExperience()
    expect(screen.getByText('老师体验入口 · 无需注册')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '开始体验' }))
    expect(await screen.findByRole('heading', { name: '体验工作台' })).toBeInTheDocument()
    expect(guestLogin).toHaveBeenCalledTimes(1)
    expect(window.localStorage.getItem('outbound_guard_token')).toBe('guest-token')
  })

  it('失败后保留入口，允许重试', async () => {
    vi.mocked(guestLogin).mockRejectedValueOnce(new Error('offline'))
    renderExperience()
    fireEvent.click(screen.getByRole('button', { name: '开始体验' }))
    expect(await screen.findByText('暂时无法进入体验，请点击重试。')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: '重试进入体验' }))
    expect(await screen.findByRole('heading', { name: '体验工作台' })).toBeInTheDocument()
    expect(guestLogin).toHaveBeenCalledTimes(2)
  })

  it('复用已登录会话，不覆盖现有账号', async () => {
    window.localStorage.setItem('outbound_guard_token', 'existing-token')
    renderExperience()
    await waitFor(() => expect(screen.getByRole('button', { name: '开始体验' })).toBeEnabled())
    fireEvent.click(screen.getByRole('button', { name: '开始体验' }))
    expect(await screen.findByRole('heading', { name: '体验工作台' })).toBeInTheDocument()
    expect(guestLogin).not.toHaveBeenCalled()
    expect(window.localStorage.getItem('outbound_guard_token')).toBe('existing-token')
  })

  it('允许使用现有账号登录', () => {
    renderExperience()
    fireEvent.click(screen.getByRole('link', { name: '已有账号？前往登录' }))
    expect(screen.getByRole('heading', { name: '账号登录' })).toBeInTheDocument()
  })
})
