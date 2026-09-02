import { getJson, getText, postForm, postFormWithProgress, postJson } from './client'
import type { CancelResponse, JobResponse, SolutionResponse } from './types'

export function submitSolve(
  endpoint: string,
  jobId: string,
  file: File,
  flags: Record<string, string>,
  onProgress?: (percent: number) => void,
): Promise<JobResponse> {
  const form = new FormData()
  form.append('mps_file', file)
  form.append('flags', JSON.stringify({ job_id: jobId, flags }))
  return onProgress
    ? postFormWithProgress<JobResponse>(endpoint, form, onProgress)
    : postForm<JobResponse>(endpoint, form)
}

export function getJob(jobId: string): Promise<JobResponse> {
  return getJson<JobResponse>(`/jobs/${jobId}`)
}

export function getSolution(jobId: string): Promise<SolutionResponse> {
  return getJson<SolutionResponse>(`/jobs/${jobId}/solution`)
}

export function getFullLog(jobId: string): Promise<string> {
  return getText(`/jobs/${jobId}/log`)
}

export function cancelJob(jobId: string): Promise<CancelResponse> {
  return postJson<CancelResponse>(`/jobs/${jobId}/cancel`, {})
}

export function listJobs(options?: { includeBatchJobs?: boolean }): Promise<JobResponse[]> {
  const query = options?.includeBatchJobs ? '?include_batch_jobs=true' : ''
  return getJson<JobResponse[]>(`/jobs${query}`)
}

export function logStreamUrl(jobId: string): string {
  return `/jobs/${jobId}/logs`
}
