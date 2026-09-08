import { Spin } from 'antd'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '@/context/AuthContext'

interface ProtectedRouteProps {
  adminOnly?: boolean
}

function ProtectedRoute({ adminOnly = false }: ProtectedRouteProps) {
  const location = useLocation()
  const { isAuthenticated, isAdmin, loading } = useAuth()

  if (loading) {
    return (
      <div className="route-loading">
        <Spin>
          <div className="route-loading-card">正在校验登录状态...</div>
        </Spin>
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate replace to={`/login?from=${encodeURIComponent(location.pathname)}`} />
  }

  if (adminOnly && !isAdmin) {
    return <Navigate replace to="/" />
  }

  return <Outlet />
}

export default ProtectedRoute
