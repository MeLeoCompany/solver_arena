import { getJson, postForm, postFormWithProgress, postJson } from './client'
import type { QoreVersionResponse } from './types'

export function listQoreVersions(): Promise<QoreVersionResponse[]> {
  return getJson<QoreVersionResponse[]>('/qore-versions')
}

export function uploadQoreVersion(
  soFile: File,
  label: string,
  onProgress?: (percent: number) => void,
): Promise<QoreVersionResponse> {
  const form = new FormData()
  form.append('so_file', soFile)
  form.append('label', label)
  return onProgress
    ? postFormWithProgress<QoreVersionResponse>('/qore-versions', form, onProgress)
    : postForm<QoreVersionResponse>('/qore-versions', form)
}

export function activateQoreVersion(id: number): Promise<QoreVersionResponse> {
  return postJson<QoreVersionResponse>(`/qore-versions/${id}/activate`, {})
}
