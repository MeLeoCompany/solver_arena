import { ApiError, postJson } from './client'
import type { CompareBatchesResponse, CompareJobsResponse } from './types'

export function compareJobs(referenceJobId: string, altJobIds: string[]): Promise<CompareJobsResponse> {
  return postJson<CompareJobsResponse>('/compare/jobs', {
    reference_job_id: referenceJobId,
    alt_job_ids: altJobIds,
  })
}

export function compareBatches(referenceBatchId: string, altBatchId: string): Promise<CompareBatchesResponse> {
  return postJson<CompareBatchesResponse>('/compare/batches', {
    reference_batch_id: referenceBatchId,
    alt_batch_id: altBatchId,
  })
}

async function downloadPdf(path: string, body: unknown, filename: string): Promise<void> {
  const response = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    let detail = response.statusText
    try {
      detail = (await response.json()).detail ?? detail
    } catch {
      // no JSON body — keep statusText
    }
    throw new ApiError(response.status, detail)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function downloadCompareJobsReport(referenceJobId: string, altJobIds: string[]): Promise<void> {
  return downloadPdf(
    '/compare/jobs/report',
    { reference_job_id: referenceJobId, alt_job_ids: altJobIds },
    `compare-${referenceJobId.slice(0, 8)}.pdf`,
  )
}

export function downloadCompareBatchesReport(referenceBatchId: string, altBatchId: string): Promise<void> {
  return downloadPdf(
    '/compare/batches/report',
    { reference_batch_id: referenceBatchId, alt_batch_id: altBatchId },
    `compare-batches-${referenceBatchId.slice(0, 8)}.pdf`,
  )
}
