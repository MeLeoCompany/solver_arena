import { getJson, postJson } from './client'
import type { ApiTokenCreatedResponse, ApiTokenResponse } from './types'

export function createToken(name: string): Promise<ApiTokenCreatedResponse> {
  return postJson<ApiTokenCreatedResponse>('/auth/tokens', { name })
}

export function listTokens(): Promise<ApiTokenResponse[]> {
  return getJson<ApiTokenResponse[]>('/auth/tokens')
}

export async function revokeToken(id: number): Promise<void> {
  const response = await fetch(`/auth/tokens/${id}`, { method: 'DELETE', credentials: 'include' })
  if (!response.ok) throw new Error('failed to revoke token')
}
