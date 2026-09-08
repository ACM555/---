import request from './request'
import type { UnifiedResponse } from '@/types/audit'

export interface PlatformModule {
  key: string
  name: string
  status: 'online' | 'demo'
  coverage: number
  features: string[]
  output: string
}

export interface PlatformOverview {
  positioning: string
  slogan: string
  healthScore?: number
  riskTrend?: Array<{
    date: string
    high: number
    medium: number
    low: number
  }>
  modules: PlatformModule[]
  dataSources: string[]
  sla: Array<{
    name: string
    target: string
    status: string
  }>
  businessModel: Array<{
    name: string
    price: string
    buyer: string
  }>
}

export interface CountryRule {
  country: string
  riskTags: string[]
  legalBasis: string
  reviewFocus: string
  timeline?: string
  strategy?: string
}

export async function getPlatformOverview(): Promise<PlatformOverview> {
  const res = (await request.get('/platform/overview')) as UnifiedResponse<PlatformOverview>
  return res.data
}

export async function getCountryRules(): Promise<CountryRule[]> {
  const res = (await request.get('/rules/countries')) as UnifiedResponse<CountryRule[]>
  return res.data
}
