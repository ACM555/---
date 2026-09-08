import request from './request'
import type { UnifiedResponse } from '@/types/audit'

export type RiskLevel = 'high' | 'medium' | 'low'

export interface BrandAsset {
  brandId: string
  name: string
  englishName: string
  owner: string
  niceClasses: string[]
  targetCountries: string[]
  portfolioStatus: string
  riskLevel: RiskLevel
  riskScore: number
  lastAuditAt: string
  nextAction: string
}

export interface MonitoringAlert {
  alertId: string
  title: string
  severity: RiskLevel
  country: string
  brandName: string
  source: string
  window: string
  status: string
  owner: string
  createdAt: string
  recommendation: string
}

export interface DataSourceStatus {
  name: string
  type: string
  status: 'online' | 'degraded' | 'scheduled'
  coverage: number
  freshness: string
  lastSync: string
  note: string
}

export interface ReportRecord {
  reportId: string
  taskId: string
  brandName: string
  niceClass: string
  targetCountries: string[]
  riskLevel: RiskLevel
  riskScore: number
  manualReviewRequired: boolean
  createdAt: string
  updatedAt: string
  owner: string
  status: string
  summary: string
}

export async function getBrandAssets(): Promise<BrandAsset[]> {
  const res = (await request.get('/brands')) as UnifiedResponse<BrandAsset[]>
  return res.data
}

export async function getMonitoringAlerts(): Promise<MonitoringAlert[]> {
  const res = (await request.get('/monitoring/alerts')) as UnifiedResponse<MonitoringAlert[]>
  return res.data
}

export async function getDataSourceStatus(): Promise<DataSourceStatus[]> {
  const res = (await request.get('/data-sources/status')) as UnifiedResponse<DataSourceStatus[]>
  return res.data
}

export async function getReports(): Promise<ReportRecord[]> {
  const res = (await request.get('/reports')) as UnifiedResponse<ReportRecord[]>
  return res.data
}
