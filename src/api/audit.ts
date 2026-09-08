import request from './request'
import type {
  AuditRequest,
  AuditResponse,
  AuditResult,
  HitRule,
  LegalReference,
  UnifiedResponse,
} from '@/types/audit'

export async function audit(data: AuditRequest): Promise<AuditResponse> {
  const serviceDescription = data.goodsServices || data.businessDescription || ''
  const payload = {
    ...data,
    goodsServices: serviceDescription,
    businessDescription: serviceDescription,
    targetMarkets: data.targetCountries?.length ? data.targetCountries : ['越南'],
    hasChinaBase: Boolean(data.hasChinaBaseMark),
  }
  const res = await request.post('/audit', payload)
  return res as unknown as AuditResponse
}

export async function getAuditResult(taskId: string): Promise<AuditResult> {
  const res = (await request.get(`/audit/result/${taskId}`)) as UnifiedResponse<RawAuditResult>
  return normalizeAuditResult(res.data)
}

type RawHitRule = Partial<HitRule>

type RawReference = Partial<LegalReference>

type RawSuggestion = {
  priority?: 'P0' | 'P1' | 'P2'
  title?: string
  description?: string
}

type RawAuditResult = Partial<AuditResult> & {
  brandName?: string
  niceClass?: string
  goodsServices?: string
  riskLevel?: 'high' | 'medium' | 'low'
  riskScore?: number
  overallResult?: string
  manualReviewRequired?: boolean
  errorMessage?: string
  hitRules?: RawHitRule[]
  references?: RawReference[]
  suggestions?: RawSuggestion[]
  radarData?: AuditResult['visual']['radarData']
  matchedBrands?: AuditResult['visual']['matchedBrands']
  documentPreview?: string
}

function normalizeAuditResult(raw: RawAuditResult | null | undefined): AuditResult {
  const safeRaw = raw ?? {}
  const hitRules = safeRaw.hitRules ?? []
  const references = safeRaw.references ?? []
  const suggestions = safeRaw.suggestions ?? []
  const absoluteRules = hitRules.filter((rule) => rule.ruleType === 'absolute')
  const relativeRules = hitRules.filter((rule) => rule.ruleType === 'relative')
  const trademarkReferences = references.filter((reference) => reference.refType === 'trademark')
  const caseReferences = references.filter((reference) => reference.refType === 'case')
  const brandName = safeRaw.brandName ?? safeRaw.summary?.brandName ?? ''
  const niceClass = safeRaw.niceClass ?? safeRaw.summary?.niceClass ?? ''
  const goodsServices = safeRaw.goodsServices ?? ''
  const riskLevel = safeRaw.riskLevel ?? safeRaw.summary?.riskLevel ?? 'low'
  const riskScore = safeRaw.riskScore ?? safeRaw.summary?.riskScore ?? 0
  const overallResult = safeRaw.overallResult ?? safeRaw.summary?.overallResult ?? ''
  const defaultIntelligence: AuditResult['intelligence'] = {
    crossClassShield: {
      triggered: false,
      score: 0,
      title: '跨类驰名保护扫描',
      explanation: '当前任务尚未生成跨类驰名保护情报。',
      protectedElements: [],
      suggestedAction: '建议重新提交审查以生成新版情报报告。',
    },
    refusalHistory: {
      triggered: false,
      title: '驳回前科红牌',
      explanation: '当前任务尚未生成驳回前科情报。',
      redFlags: [],
      evidence: [],
    },
    culturalReview: {
      triggered: false,
      title: '文化禁忌审查',
      country: '越南',
      rules: [],
    },
    registrationStrategy: {
      route: '越南单国申请优先',
      rationale: '当前任务尚未生成完整注册策略。',
      marketCount: 1,
      timeline: [],
      costNotes: [],
    },
    monitoring: [],
  }
  const normalizedHitRules = hitRules.map((rule): HitRule => ({
    ruleType: rule.ruleType ?? 'absolute',
    article: rule.article ?? '未命名法条',
    content: rule.content ?? '',
    applicable: Boolean(rule.applicable),
    similarityType: rule.similarityType ?? '',
    similarityScore: rule.similarityScore ?? 0,
    note: rule.note ?? '',
  }))
  const normalizedReferences = references.map((reference): LegalReference => ({
    refType: reference.refType ?? 'law',
    title: reference.title ?? '未命名依据',
    source: reference.source ?? '',
    date: reference.date ?? '',
    registrationNo: reference.registrationNo ?? '',
    summary: reference.summary ?? '',
    relevance: reference.relevance ?? '',
  }))

  return {
    taskId: safeRaw.taskId ?? '',
    status: safeRaw.status ?? 'pending',
    currentStep: safeRaw.currentStep ?? 0,
    progress: safeRaw.progress ?? 0,
    errorMessage: safeRaw.errorMessage,
    brandName,
    niceClass,
    goodsServices,
    riskLevel,
    riskScore,
    overallResult,
    manualReviewRequired: Boolean(safeRaw.manualReviewRequired),
    hitRules: normalizedHitRules,
    references: normalizedReferences,
    summary: safeRaw.summary ?? {
      brandName,
      niceClass,
      riskLevel,
      riskScore,
      overallResult,
    },
    absolute: safeRaw.absolute ?? {
      hasRisk: absoluteRules.some((rule) => rule.applicable),
      rejectionProbability:
        absoluteRules.find((rule) => rule.applicable)?.similarityScore ??
        Math.max(0, Math.round((safeRaw.riskScore ?? 0) * 0.35)),
      articles: absoluteRules.map((rule) => ({
        article: rule.article ?? '未命名法条',
        content: rule.content ?? '',
        applicable: Boolean(rule.applicable),
        note: rule.note ?? '',
      })),
    },
    relative: safeRaw.relative ?? {
      hasRisk: relativeRules.some((rule) => rule.applicable),
      conflicts: trademarkReferences.map((reference, index) => ({
        brandName: reference.title ?? '未知冲突品牌',
        registeredClass: reference.summary ?? '',
        registrationNo: reference.registrationNo ?? `conflict-${index + 1}`,
        similarityType: relativeRules[index]?.similarityType ?? relativeRules[0]?.similarityType ?? '',
        similarityScore: relativeRules[index]?.similarityScore ?? relativeRules[0]?.similarityScore ?? 0,
      })),
      precedents: caseReferences.map((reference) => ({
        caseName: reference.title ?? '未命名判例',
        court: reference.source ?? '',
        date: reference.date ?? '',
        ruling: reference.summary ?? '',
        relevance: reference.relevance ?? '',
      })),
    },
    visual: safeRaw.visual ?? {
      radarData: safeRaw.radarData ?? [],
      matchedBrands: safeRaw.matchedBrands ?? [],
    },
    intelligence: safeRaw.intelligence ?? defaultIntelligence,
    advice: safeRaw.advice ?? {
      recommendations: suggestions.map((suggestion) => ({
        priority: suggestion.priority ?? 'P2',
        title: suggestion.title ?? '未命名建议',
        description: suggestion.description ?? '',
      })),
      documentPreview: safeRaw.documentPreview ?? '',
    },
  }
}
