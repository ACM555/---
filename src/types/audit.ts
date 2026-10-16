export interface AuditRequest {
  brandName: string
  englishName: string
  niceClass: string
  goodsServices: string
  businessDescription?: string
  targetCountries?: string[]
  operationStage?: 'pre-entry' | 'launching' | 'operating'
  plannedMarkets?: number
  hasChinaBaseMark?: boolean
  logo: string
}

export type AuditFormData = AuditRequest

export interface AuditResponse {
  code: number
  message: string
  data: {
    taskId: string
  }
}

export interface HitRule {
  ruleId?: string
  ruleName?: string
  ruleType: 'absolute' | 'relative'
  article: string
  content: string
  applicable: boolean
  similarityType: string
  similarityScore: number
  note: string
}

export interface LegalReference {
  refType: 'law' | 'case' | 'trademark'
  title: string
  source: string
  date: string
  registrationNo: string
  summary: string
  relevance: string
  sourceKind?: 'internal_rule' | 'official_law' | 'official_pointer' | 'local_record'
  sourceUrl?: string
  version?: string
  approvalStatus?: string
  locator?: string
  originalText?: string
  prerequisites?: string[]
}

export interface AuditResult {
  taskId: string
  status: 'pending' | 'processing' | 'done' | 'error'
  currentStep: number
  progress: number
  errorMessage?: string
  brandName: string
  niceClass: string
  goodsServices: string
  riskLevel: 'high' | 'medium' | 'low'
  riskScore: number
  overallResult: string
  manualReviewRequired: boolean
  assessmentStatus?: 'pending_verification' | 'source_backed'
  hitRules: HitRule[]
  references: LegalReference[]
  summary: {
    brandName: string
    niceClass: string
    riskLevel: 'high' | 'medium' | 'low'
    riskScore: number
    overallResult: string
  }
  absolute: {
    hasRisk: boolean
    rejectionProbability: number
    articles: Array<{
      article: string
      content: string
      applicable: boolean
      note: string
    }>
  }
  relative: {
    hasRisk: boolean
    conflicts: Array<{
      brandName: string
      registeredClass: string
      registrationNo: string
      similarityType: string
      similarityScore: number
    }>
    precedents: Array<{
      caseName: string
      court: string
      date: string
      ruling: string
      relevance: string
    }>
  }
  visual: {
    radarData: Array<{
      dimension: string
      target: number
      benchmark: number
    }>
    matchedBrands: Array<{
      name: string
      thumbnailUrl: string
      matchScore: number
    }>
    analysisMode?: string
    summary?: string
  }
  intelligence: {
    crossClassShield: {
      triggered: boolean
      score: number
      title: string
      explanation: string
      protectedElements: string[]
      suggestedAction: string
    }
    refusalHistory: {
      triggered: boolean
      title: string
      explanation: string
      redFlags: string[]
      evidence: string[]
    }
    culturalReview: {
      triggered: boolean
      title: string
      country: string
      rules: Array<{
        label: string
        severity: 'high' | 'medium' | 'low'
        note: string
      }>
    }
    registrationStrategy: {
      route: string
      rationale: string
      marketCount: number
      timeline: Array<{
        stage: string
        duration: string
        output: string
      }>
      costNotes: string[]
    }
    monitoring: Array<{
      name: string
      cadence: string
      source: string
      actionWindow: string
    }>
  }
  advice: {
    recommendations: Array<{
      priority: 'P0' | 'P1' | 'P2'
      title: string
      description: string
    }>
    documentPreview: string
    documentDownloadUrl?: string
  }
}

export interface UnifiedResponse<T> {
  code: number
  message: string
  data: T
}
