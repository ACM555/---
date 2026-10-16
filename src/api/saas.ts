import request from './request'
import type { UnifiedResponse } from '@/types/audit'

export type RiskLevel = 'high' | 'medium' | 'low'

export interface BrandAsset {
  assessmentStatus?: 'pending_verification' | 'source_backed'
  brandId: string
  taskId?: string
  isDemo?: boolean
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
  sourceUrl?: string
  lastCheckedAt?: string
  isDemo?: boolean
  publicationDate?: string
  licenceUrl?: string
  attribution?: string
}

export interface DataSourceStatus {
  name: string
  type: string
  status: 'online' | 'degraded' | 'scheduled'
  coverage: number
  freshness: string
  lastSync: string
  note: string
  recordCount?: number
  sourceUrl?: string
  remoteRecordCount?: number
  datasetUpdatedAt?: string
  licenceUrl?: string
  attribution?: string
}

export interface PublicTrademarkRecord {
  applicationNumber: string
  markName: string
  classes: string[]
  goodsServices: string[]
  goodsServicesTruncated: boolean
  status: string
  applicationDate?: string
  statusDate?: string
  expiryDate?: string
  publicationDate?: string
  officialModifiedAt?: string
  fetchedAt: string
  sourceUrl: string
  datasetUrl: string
  licenceUrl: string
  attribution: string
  isDemo: boolean
}

export interface PublicTrademarkSearch {
  query: string
  records: PublicTrademarkRecord[]
  total: number
  offset: number
  limit: number
  hasMore: boolean
  fetchedAt: string
  datasetUpdatedAt?: string
  cached: boolean
  boundary: string
  sourceUrl: string
  licenceUrl: string
  attribution: string
}

export interface PublicTrademarkExplanation {
  applicationNumber: string
  translations: Array<{ field: string; original: string; chinese: string }>
  aiStatus: 'translated' | 'not_configured' | 'unavailable'
  message: string
  provider: string
  model: string
  boundary: string
}

export async function searchPublicTrademarks(query: string, offset = 0): Promise<PublicTrademarkSearch> {
  const response = (await request.get('/trademarks/search', { params: { q: query, offset }, timeout: 75_000 })) as UnifiedResponse<PublicTrademarkSearch>
  return response.data
}

export async function explainPublicTrademark(applicationNumber: string): Promise<PublicTrademarkExplanation> {
  const response = (await request.post(`/trademarks/${encodeURIComponent(applicationNumber)}/explain`, {}, { timeout: 120_000 })) as UnifiedResponse<PublicTrademarkExplanation>
  return response.data
}

export async function getTrademarkWatches(): Promise<PublicTrademarkRecord[]> {
  const response = (await request.get('/trademarks/watches')) as UnifiedResponse<PublicTrademarkRecord[]>
  return response.data
}

export async function setTrademarkWatch(applicationNumber: string, watching: boolean): Promise<void> {
  const address = `/trademarks/${encodeURIComponent(applicationNumber)}/watch`
  if (watching) await request.post(address)
  else await request.delete(address)
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
  completedAt?: string
  archivedAt?: string
  lastViewedAt?: string
  owner: string
  status: string
  summary: string
  assessmentStatus?: 'pending_verification' | 'source_backed'
}

export interface AuditTaskRecord {
  taskId: string
  brandName: string
  niceClass: string
  status: 'pending' | 'processing' | 'done' | 'error'
  progress: number
  createdAt: string
  errorMessage: string
}

export async function getAuditTasks(): Promise<AuditTaskRecord[]> {
  const response = (await request.get('/audit/tasks')) as UnifiedResponse<AuditTaskRecord[]>
  return response.data
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
