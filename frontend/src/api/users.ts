import { getJson, postJson } from './client'
import type { UserAdminResponse, UserCreatedResponse } from './types'

export function createUser(username: string): Promise<UserCreatedResponse> {
  return postJson<UserCreatedResponse>('/users', { username })
}

export function listUsers(): Promise<UserAdminResponse[]> {
  return getJson<UserAdminResponse[]>('/users')
}

export async function deleteUser(id: number): Promise<void> {
  const response = await fetch(`/users/${id}`, { method: 'DELETE', credentials: 'include' })
  if (!response.ok) throw new Error('failed to delete user')
}
