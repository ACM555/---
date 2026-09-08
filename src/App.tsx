import { BrowserRouter, Route, Routes } from 'react-router-dom'
import AppLayout from '@/components/AppLayout'
import ProtectedRoute from '@/components/ProtectedRoute'
import Admin from '@/pages/Admin'
import Auth from '@/pages/Auth'
import BrandAssets from '@/pages/BrandAssets'
import Home from '@/pages/Home'
import Monitoring from '@/pages/Monitoring'
import Report from '@/pages/Report'
import Reports from '@/pages/Reports'
import Reviewing from '@/pages/Reviewing'
import RulesLibrary from '@/pages/RulesLibrary'
import Submit from '@/pages/Submit'
import EngineeringScreening from '@/pages/EngineeringScreening'

function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Routes>
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
    </BrowserRouter>
  )
}

export default App
