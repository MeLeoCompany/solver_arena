import { getJson, postJson } from './client'

export interface SolverInfo {
  key: string
  label: string
  parameters: string[]
  available: boolean
  availability_detail: string | null
  availability_checked_at: string | null
}

export function listSolvers(): Promise<SolverInfo[]> {
  return getJson<SolverInfo[]>('/solvers')
}

export function refreshSolvers(): Promise<SolverInfo[]> {
  return postJson<SolverInfo[]>('/solvers/refresh', {})
}

export function solveEndpoint(key: string): string {
  return `/solve/${key}`
}
