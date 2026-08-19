import { getJson, postJson } from './client'
import type { UserResponse } from './types'

export function login(username: string, password: string): Promise<UserResponse> {
  return postJson<UserResponse>('/auth/login', { username, password })
}

export function logout(): Promise<{ logged_out: boolean }> {
  return postJson('/auth/logout', {})
}

export function me(): Promise<UserResponse> {
  return getJson<UserResponse>('/auth/me')
}
