import type { HistoryRecord } from '../types'

const KEY = 'acl-helper-history'

export function loadHistory(): HistoryRecord[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || '[]')
  } catch {
    return []
  }
}

export function saveHistory(record: HistoryRecord) {
  const next = [record, ...loadHistory()].slice(0, 12)
  localStorage.setItem(KEY, JSON.stringify(next))
  return next
}

export function clearHistory() {
  localStorage.removeItem(KEY)
}
