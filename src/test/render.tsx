import type { ReactElement } from 'react'
import { App as AntdApp, ConfigProvider } from 'antd'
import { render } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'

export function renderWithProviders(ui: ReactElement, initialEntry = '/') {
  return render(
    <ConfigProvider>
      <AntdApp>
        <MemoryRouter
          future={{ v7_relativeSplatPath: true, v7_startTransition: true }}
          initialEntries={[initialEntry]}
        >
          {ui}
        </MemoryRouter>
      </AntdApp>
    </ConfigProvider>,
  )
}
