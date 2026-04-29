import type { EvaluationPayload, ReportResponse } from '../types'

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8020'

export async function createReport(payload: EvaluationPayload): Promise<ReportResponse> {
  const response = await fetch(`${API_BASE}/api/reports`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || '报告生成失败')
  }

  return response.json()
}

export function pdfUrl(path: string) {
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}
