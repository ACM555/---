import request from './request'

export type EvidenceLevel = 'A' | 'B'
export interface LegalSourceProvenance { provenance_id:string; role:'primary'|'cross_check'; publisher:string; source_type:string; source_url:string; source_language:string; checked_at:string; version_note:string; conflict_note:string }
export interface LegalSource { source_id:string; country_code:string; legal_module:string; evidence_level:EvidenceLevel; title:string; source_type:string; source_url:string; source_language:string; effective_at:string|null; verified_at:string; supported_fact:string; prerequisites:string[]; non_inferences:string[]; review_triggers:string[]; provenance:LegalSourceProvenance[]; reviewable_passage_count:number }
export interface LegalPassage { passage_id:string; source_id:string; locator:string; original_text:string; chinese_text:string|null; effective_at:string|null; prerequisites:string[]; non_inferences:string[]; approval_status:'draft'|'approved'|'retired'; created_at:string; updated_at:string }
export async function getLegalSources(params: { country_code?:string; legal_module?:string; evidence_level?:EvidenceLevel } = {}): Promise<LegalSource[]> {
  const response = await request.get('/legal/sources', { params })
  return response as unknown as LegalSource[]
}
export async function getSourcesForReview(status = 'draft'): Promise<LegalSource[]> { return (await request.get('/legal/admin/sources', { params:{ approval_status:status } })) as unknown as LegalSource[] }
export async function reviewLegalSource(sourceId:string, approval_status:'approved'|'retired'): Promise<LegalSource> { return (await request.post(`/legal/admin/sources/${sourceId}/approval`, { approval_status })) as unknown as LegalSource }
export async function getLegalPassages(sourceId:string): Promise<LegalPassage[]> { return (await request.get(`/legal/admin/sources/${sourceId}/passages`)) as unknown as LegalPassage[] }
export async function createLegalPassage(sourceId:string, payload: Omit<LegalPassage, 'passage_id'|'created_at'|'updated_at'>): Promise<LegalPassage> { return (await request.post(`/legal/admin/sources/${sourceId}/passages`, payload)) as unknown as LegalPassage }
export async function reviewLegalPassage(passageId:string, approval_status:'approved'|'retired'): Promise<LegalPassage> { return (await request.post(`/legal/admin/passages/${passageId}/approval`, { approval_status })) as unknown as LegalPassage }
