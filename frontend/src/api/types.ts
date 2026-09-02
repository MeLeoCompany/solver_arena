export type JobState = 'pending' | 'running' | 'done' | 'failed' | 'cancelled'

export type SolveStatus = 'optimal' | 'feasible' | 'infeasible' | 'timeout' | 'unbounded'

export interface JobResponse {
  job_id: string
  solver: string
  state: JobState
  solve_status: SolveStatus | null
  objective: number | null
  solve_time: number | null
  solution_url: string | null
  log_url: string | null
  error: string | null
  created_at: string | null
  original_filename: string | null
  created_by: string | null
  batch_id: string | null
  batch_index: number | null
}

export interface BatchResponse {
  batch_id: string
  solver: string
  state: JobState
  total: number
  completed: number
  created_by: string | null
  created_at: string
  jobs: JobResponse[]
}

export interface BatchCancelResponse {
  batch_id: string
  cancelling: boolean
}

export interface SolutionResponse {
  job_id: string
  variables: number[] | Record<string, number>
}

export interface CancelResponse {
  job_id: string
  cancelling: boolean
}

export interface UserResponse {
  username: string
  is_admin: boolean
}

export interface ApiTokenResponse {
  id: number
  name: string
  created_at: string
  expires_at: string
}

export interface ApiTokenCreatedResponse extends ApiTokenResponse {
  token: string
}

export interface UserAdminResponse {
  id: number
  username: string
  is_admin: boolean
  created_at: string
}

export interface UserCreatedResponse {
  id: number
  username: string
  password: string
  created_at: string
}

export interface QoreVersionResponse {
  id: number
  label: string
  active: boolean
  smoke_test_ok: boolean
  smoke_test_output: string | null
  uploaded_by: string | null
  uploaded_at: string
}

export interface ObjectiveComparisonRow {
  alt_job_id: string
  alt_solver: string
  reference_objective: number | null
  alt_objective: number | null
  delta_abs: number | null
  delta_rel_pct: number | null
  reference_status: string | null
  alt_status: string | null
  alt_minimize: boolean
  error: string | null
  // Only set for batch-vs-batch comparisons — null in the plain job-vs-job path.
  batch_index: number | null
  reference_job_id: string | null
  reference_filename: string | null
  alt_filename: string | null
}

export interface ViolationRow {
  job_id: string
  solver: string
  max_violation: number | null
  num_violations: number | null
  within_tolerance: boolean | null
  error: string | null
  batch_index: number | null
  filename: string | null
}

export interface SolutionDiffRow {
  alt_job_id: string
  alt_solver: string
  num_diffs: number | null
  max_diff: number | null
  objective_impact_linear: number | null
  objective_impact_quadratic: number | null
  objective_impact_total: number | null
  error: string | null
  batch_index: number | null
  reference_job_id: string | null
  reference_filename: string | null
  alt_filename: string | null
}

export interface CompareJobsResponse {
  reference_job_id: string
  reference_minimize: boolean
  objective: ObjectiveComparisonRow[]
  violations: ViolationRow[]
  solution_diff: SolutionDiffRow[]
}

export interface CompareBatchesResponse {
  reference_batch_id: string
  alt_batch_id: string
  objective: ObjectiveComparisonRow[]
  violations: ViolationRow[]
  solution_diff: SolutionDiffRow[]
}
