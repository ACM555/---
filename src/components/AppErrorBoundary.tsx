import { Component, type ErrorInfo, type ReactNode } from 'react'

interface AppErrorBoundaryProps {
  children: ReactNode
}

interface AppErrorBoundaryState {
  error: Error | null
}

class AppErrorBoundary extends Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
  state: AppErrorBoundaryState = { error: null }

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('Application render failed', error, info)
  }

  render() {
    if (this.state.error) {
      return (
        <main className="boot-fallback">
          <section className="boot-fallback-card">
            <h1>页面加载失败</h1>
            <p>前端程序出现异常，请点击下方按钮重新加载。</p>
            <button type="button" onClick={() => window.location.reload()}>
              重新加载
            </button>
          </section>
        </main>
      )
    }

    return this.props.children
  }
}

export default AppErrorBoundary
