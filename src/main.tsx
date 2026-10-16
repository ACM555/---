import React from 'react'
import ReactDOM from 'react-dom/client'
import { App as AntdApp, ConfigProvider } from 'antd'
import 'antd/dist/reset.css'
import App from '@/App'
import AppErrorBoundary from '@/components/AppErrorBoundary'
import { AuthProvider } from '@/context/AuthContext'
import '@/styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#7a0019',
          colorInfo: '#155eef',
          colorSuccess: '#15803d',
          colorWarning: '#b45309',
          colorError: '#b91c1c',
          colorBgBase: '#f5f7fb',
          colorTextBase: '#102033',
          colorBorder: '#d8e0ea',
          borderRadius: 12,
          boxShadow: '0 16px 42px rgba(15, 23, 42, 0.08)',
          fontFamily:
            '-apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif',
        },
        components: {
          Card: {
            colorBgContainer: '#ffffff',
          },
          Layout: {
            bodyBg: '#f5f7fb',
            headerBg: '#ffffff',
            siderBg: '#0b1b35',
          },
          Menu: {
            darkItemBg: 'transparent',
            darkItemSelectedBg: 'rgba(255, 255, 255, 0.14)',
            darkItemSelectedColor: '#ffffff',
          },
          Table: {
            colorBgContainer: '#ffffff',
            headerBg: '#f3f6fb',
          },
        },
      }}
    >
      <AntdApp>
        <AppErrorBoundary>
          <AuthProvider>
            <App />
          </AuthProvider>
        </AppErrorBoundary>
      </AntdApp>
    </ConfigProvider>
  </React.StrictMode>,
)
