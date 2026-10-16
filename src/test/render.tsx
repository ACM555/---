import type { ReactElement } from 'react'
import { App as AntdApp, ConfigProvider } from 'antd'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { AuthProvider } from '@/context/AuthContext'

export function renderWithProviders(ui: ReactElement, initialEntry = '/') {
  return render(
    <ConfigProvider>
      <AntdApp>
        <MemoryRouter initialEntries={[initialEntry]}>
          <AuthProvider>{ui}</AuthProvider>
        </MemoryRouter>
      </AntdApp>
    </ConfigProvider>,
  )
}
