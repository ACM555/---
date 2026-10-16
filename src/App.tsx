import { lazy, Suspense } from 'react'
import { HashRouter, Route, Routes } from 'react-router-dom'
import ProtectedRoute from '@/components/ProtectedRoute'

const AppLayout = lazy(() => import('@/components/AppLayout'))
const Admin = lazy(() => import('@/pages/Admin'))
const Auth = lazy(() => import('@/pages/Auth'))
const BrandAssets = lazy(() => import('@/pages/BrandAssets'))
const Experience = lazy(() => import('@/pages/Experience'))
const Home = lazy(() => import('@/pages/Home'))
const Monitoring = lazy(() => import('@/pages/Monitoring'))
const Report = lazy(() => import('@/pages/Report'))
const Reports = lazy(() => import('@/pages/Reports'))
const Reviewing = lazy(() => import('@/pages/Reviewing'))
const RulesLibrary = lazy(() => import('@/pages/RulesLibrary'))
const Submit = lazy(() => import('@/pages/Submit'))
const EngineeringScreening = lazy(() => import('@/pages/EngineeringScreening'))

function RouteFallback() {
  return (
    <main className="boot-fallback">
      <section className="boot-fallback-card">
        <h1>东盟跨境商事法律 AI 助手</h1>
        <p>正在载入页面...</p>
      </section>
    </main>
  )
}

function App() {
  return (
    <HashRouter>
      <Suspense fallback={<RouteFallback />}>
        <Routes>
          <Route path="/experience" element={<Experience />} />
          <Route path="/login" element={<Auth mode="login" />} />
          <Route path="/register" element={<Auth mode="register" />} />
          <Route element={<ProtectedRoute adminOnly />}>
            <Route path="/admin" element={<Admin />} />
          </Route>
          <Route path="/" element={<AppLayout />}>
            <Route element={<ProtectedRoute />}>
              <Route index element={<Home />} />
              <Route path="assets" element={<BrandAssets />} />
              <Route path="submit" element={<Submit />} />
              <Route path="reviewing" element={<Reviewing />} />
              <Route path="reports" element={<Reports />} />
              <Route path="monitoring" element={<Monitoring />} />
              <Route path="rules" element={<RulesLibrary />} />
              <Route path="legal-library" element={<RulesLibrary />} />
              <Route path="engineering-screening" element={<EngineeringScreening />} />
              <Route path="report" element={<Report />} />
              <Route path="report/:taskId" element={<Report />} />
            </Route>
          </Route>
        </Routes>
      </Suspense>
    </HashRouter>
  )
}

export default App
