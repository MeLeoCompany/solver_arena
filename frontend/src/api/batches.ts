import { getJson, postForm, postFormWithProgress, postJson } from './client'
import type { BatchCancelResponse, BatchResponse } from './types'

export function submitBatch(
  solverKey: string,
  zipFile: File,
  flags: Record<string, string>,
  onProgress?: (percent: number) => void,
): Promise<BatchResponse> {
  const form = new FormData()
  form.append('zip_file', zipFile)
  form.append('solver', solverKey)
  form.append('flags', JSON.stringify({ flags }))
  return onProgress
    ? postFormWithProgress<BatchResponse>('/batches', form, onProgress)
    : postForm<BatchResponse>('/batches', form)
}

export function getBatch(batchId: string): Promise<BatchResponse> {
  return getJson<BatchResponse>(`/batches/${batchId}`)
}

export function listBatches(): Promise<BatchResponse[]> {
  return getJson<BatchResponse[]>('/batches')
}

export function cancelBatch(batchId: string): Promise<BatchCancelResponse> {
  return postJson<BatchCancelResponse>(`/batches/${batchId}/cancel`, {})
}

export function batchLogStreamUrl(batchId: string): string {
  return `/batches/${batchId}/logs`
}
