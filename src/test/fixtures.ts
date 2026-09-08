import type { AuditResult } from '@/types/audit'

export function createAuditResult(overrides: Partial<AuditResult> = {}): AuditResult {
  const base: AuditResult = {
    taskId: 'task-001',
    status: 'done',
    currentStep: 2,
    progress: 100,
    brandName: '墨兰奶白',
    niceClass: '第43类-餐饮服务',
    goodsServices: '茶饮及餐饮服务',
    riskLevel: 'high',
    riskScore: 88,
    overallResult: '检出高风险冲突，建议正式申请前人工复核。',
    manualReviewRequired: true,
    hitRules: [],
    references: [],
    summary: {
      brandName: '墨兰奶白',
      niceClass: '第43类-餐饮服务',
      riskLevel: 'high',
      riskScore: 88,
      overallResult: '检出高风险冲突，建议正式申请前人工复核。',
    },
    absolute: { hasRisk: true, rejectionProbability: 76, articles: [] },
    relative: { hasRisk: true, conflicts: [], precedents: [] },
    visual: { radarData: [], matchedBrands: [] },
    intelligence: {
      crossClassShield: {
        triggered: false,
        score: 0,
        title: '跨类保护扫描',
        explanation: '',
        protectedElements: [],
        suggestedAction: '',
      },
      refusalHistory: {
        triggered: false,
        title: '驳回前科',
        explanation: '',
        redFlags: [],
        evidence: [],
      },
      culturalReview: { triggered: false, title: '文化审查', country: '越南', rules: [] },
      registrationStrategy: { route: '单国申请', rationale: '', marketCount: 1, timeline: [], costNotes: [] },
      monitoring: [],
    },
    advice: {
      recommendations: [],
      documentPreview: '',
      documentDownloadUrl: '/api/audit/report/task-001/pdf',
    },
  }

  return {
    ...base,
    ...overrides,
    intelligence: overrides.intelligence ?? base.intelligence,
  }
}
