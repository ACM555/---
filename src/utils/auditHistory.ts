import type { AuditRequest } from '@/types/audit'

const HISTORY_KEY = 'outbound_guard_audit_history'
const CURRENT_TASK_KEY = 'outbound_guard_current_task_id'
const MAX_HISTORY = 20

export interface AuditHistoryItem {
  taskId: string
  brandName: string
  englishName: string
  niceClass: string
  goodsServices: string
  targetMarkets: string[]
  hasChinaBase: boolean
  createdAt: string
}

function safeParseHistory(value: string | null): AuditHistoryItem[] {
  if (!value) return []
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function getAuditHistory(): AuditHistoryItem[] {
  return safeParseHistory(window.localStorage.getItem(HISTORY_KEY))
}

export function getCurrentTaskId(): string | null {
  return window.localStorage.getItem(CURRENT_TASK_KEY)
}

export function saveAuditTask(taskId: string, request: AuditRequest) {
  const nextItem: AuditHistoryItem = {
    taskId,
    brandName: request.brandName,
    englishName: request.englishName,
    niceClass: request.niceClass,
    goodsServices: request.goodsServices,
    targetMarkets: request.targetCountries ?? [],
    hasChinaBase: request.hasChinaBaseMark ?? false,
    createdAt: new Date().toISOString(),
  }
  const history = getAuditHistory().filter((item) => item.taskId !== taskId)
  const nextHistory = [nextItem, ...history].slice(0, MAX_HISTORY)
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory))
  window.localStorage.setItem(CURRENT_TASK_KEY, taskId)
}

export function setCurrentTaskId(taskId: string) {
  window.localStorage.setItem(CURRENT_TASK_KEY, taskId)
}

export function removeAuditTask(taskId: string) {
  const nextHistory = getAuditHistory().filter((item) => item.taskId !== taskId)
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(nextHistory))

  if (getCurrentTaskId() === taskId) {
    const nextCurrent = nextHistory[0]?.taskId
    if (nextCurrent) {
      window.localStorage.setItem(CURRENT_TASK_KEY, nextCurrent)
    } else {
      window.localStorage.removeItem(CURRENT_TASK_KEY)
    }
  }
}

export function clearCurrentTask() {
  window.localStorage.removeItem(CURRENT_TASK_KEY)
}
