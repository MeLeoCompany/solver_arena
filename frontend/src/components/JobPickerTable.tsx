import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import type { JobResponse } from '../api/types'

type SortKey = 'filename' | 'solver' | 'created_at' | 'objective'
type SortDirection = 'asc' | 'desc'

interface ColumnFilters {
  filename: string
  solver: string
  jobId: string
}

interface Props {
  jobs: JobResponse[]
  referenceId: string | null
  onReferenceChange: (jobId: string) => void
  altIds: Set<string>
  onToggleAlt: (jobId: string) => void
  disabled?: boolean
}

function jobFileName(job: JobResponse): string {
  return job.original_filename ?? '(без имени файла)'
}

export function JobPickerTable({
  jobs,
  referenceId,
  onReferenceChange,
  altIds,
  onToggleAlt,
  disabled,
}: Props) {
  const [showBatchJobs, setShowBatchJobs] = useState(false)
  const [filters, setFilters] = useState<ColumnFilters>({ filename: '', solver: '', jobId: '' })
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'created_at',
    direction: 'desc',
  })

  function toggleSort(key: SortKey) {
    setSort((prev) =>
      prev.key === key ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' } : { key, direction: 'asc' },
    )
  }

  function setFilter(field: keyof ColumnFilters, value: string) {
    setFilters((prev) => ({ ...prev, [field]: value }))
  }

  const rows = useMemo(() => {
    const filtered = jobs.filter((job) => {
      if (!showBatchJobs && job.batch_id) return false
      if (filters.filename && !jobFileName(job).toLowerCase().includes(filters.filename.toLowerCase())) {
        return false
      }
      if (filters.solver && !job.solver.toLowerCase().includes(filters.solver.toLowerCase())) return false
      if (filters.jobId && !job.job_id.toLowerCase().includes(filters.jobId.toLowerCase())) return false
      return true
    })

    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sort.key === 'filename') cmp = jobFileName(a).localeCompare(jobFileName(b))
      else if (sort.key === 'solver') cmp = a.solver.localeCompare(b.solver)
      else if (sort.key === 'created_at') cmp = (a.created_at ?? '').localeCompare(b.created_at ?? '')
      else if (sort.key === 'objective') cmp = (a.objective ?? -Infinity) - (b.objective ?? -Infinity)
      return sort.direction === 'asc' ? cmp : -cmp
    })
  }, [jobs, filters, sort, showBatchJobs])

  function sortIndicator(key: SortKey): string {
    if (sort.key !== key) return ''
    return sort.direction === 'asc' ? ' ▲' : ' ▼'
  }

  const columnCount = showBatchJobs ? 8 : 7

  return (
    <div className="job-picker">
      <label className="job-picker__toggle">
        <input
          type="checkbox"
          checked={showBatchJobs}
          disabled={disabled}
          onChange={(e) => setShowBatchJobs(e.target.checked)}
        />
        Показывать задачи из групп
      </label>
      <div className="job-picker__wrapper">
        <table className="job-picker__table">
          <thead>
            <tr>
              <th>Эталон</th>
              <th>Альт</th>
              <th className="job-picker__sortable" onClick={() => toggleSort('filename')}>
                Файл{sortIndicator('filename')}
              </th>
              <th className="job-picker__sortable" onClick={() => toggleSort('solver')}>
                Солвер{sortIndicator('solver')}
              </th>
              <th className="job-picker__sortable" onClick={() => toggleSort('created_at')}>
                Создана{sortIndicator('created_at')}
              </th>
              <th className="job-picker__sortable" onClick={() => toggleSort('objective')}>
                Objective{sortIndicator('objective')}
              </th>
              {showBatchJobs && <th>Батч</th>}
              <th>Job ID</th>
            </tr>
            <tr className="job-picker__filter-row">
              <th></th>
              <th></th>
              <th>
                <input
                  value={filters.filename}
                  placeholder="фильтр…"
                  onChange={(e) => setFilter('filename', e.target.value)}
                />
              </th>
              <th>
                <input
                  value={filters.solver}
                  placeholder="фильтр…"
                  onChange={(e) => setFilter('solver', e.target.value)}
                />
              </th>
              <th></th>
              <th></th>
              {showBatchJobs && <th></th>}
              <th>
                <input
                  value={filters.jobId}
                  placeholder="фильтр…"
                  onChange={(e) => setFilter('jobId', e.target.value)}
                />
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columnCount} className="job-picker__empty">
                  Нет подходящих задач
                </td>
              </tr>
            ) : (
              rows.map((job) => {
                const isReference = job.job_id === referenceId
                return (
                  <tr key={job.job_id} className={isReference ? 'job-picker__row--reference' : undefined}>
                    <td>
                      <input
                        type="radio"
                        name="reference-job"
                        checked={isReference}
                        disabled={disabled}
                        onChange={() => onReferenceChange(job.job_id)}
                      />
                    </td>
                    <td>
                      <input
                        type="checkbox"
                        checked={altIds.has(job.job_id)}
                        disabled={disabled || isReference}
                        onChange={() => onToggleAlt(job.job_id)}
                      />
                    </td>
                    <td>{jobFileName(job)}</td>
                    <td>{job.solver}</td>
                    <td>{job.created_at ? new Date(job.created_at).toLocaleString() : '—'}</td>
                    <td>{job.objective ?? '—'}</td>
                    {showBatchJobs && (
                      <td>
                        {job.batch_id ? (
                          <Link to={`/batches/${job.batch_id}`} onClick={(e) => e.stopPropagation()}>
                            #{job.batch_index}
                          </Link>
                        ) : (
                          '—'
                        )}
                      </td>
                    )}
                    <td className="job-picker__job-id">{job.job_id.slice(0, 8)}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
