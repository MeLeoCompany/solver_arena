import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listJobs } from '../api/jobs'
import { listBatches } from '../api/batches'
import type { BatchResponse, JobResponse } from '../api/types'

type Row =
  | { type: 'job'; createdAt: string; job: JobResponse }
  | { type: 'batch'; createdAt: string; batch: BatchResponse }

export function HistoryPage() {
  const [rows, setRows] = useState<Row[] | null>(null)
  const [error, setError] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  useEffect(() => {
    Promise.all([listJobs(), listBatches()])
      .then(([jobs, batches]) => {
        const jobRows: Row[] = jobs.map((job) => ({
          type: 'job',
          createdAt: job.created_at ?? '',
          job,
        }))
        const batchRows: Row[] = batches.map((batch) => ({
          type: 'batch',
          createdAt: batch.created_at,
          batch,
        }))
        setRows([...jobRows, ...batchRows].sort((a, b) => b.createdAt.localeCompare(a.createdAt)))
      })
      .catch(() => setError(true))
  }, [])

  function toggle(batchId: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(batchId)) next.delete(batchId)
      else next.add(batchId)
      return next
    })
  }

  if (error) return <div className="history-page__error">Не удалось загрузить историю</div>
  if (!rows) return <div className="history-page__loading">Загрузка…</div>

  return (
    <div className="history-page">
      <h1>История задач</h1>
      {rows.length === 0 ? (
        <div className="history-page__empty">Пока нет решённых задач</div>
      ) : (
        <div className="history-table__wrapper">
          <table className="history-table">
            <thead>
              <tr>
                <th></th>
                <th>Создана</th>
                <th>Solver</th>
                <th>Файл</th>
                <th>Автор</th>
                <th>Статус</th>
                <th>Objective</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) =>
                row.type === 'job' ? (
                  <tr key={row.job.job_id}>
                    <td></td>
                    <td>{row.job.created_at ? new Date(row.job.created_at).toLocaleString() : '—'}</td>
                    <td>{row.job.solver}</td>
                    <td>—</td>
                    <td>{row.job.created_by ?? '—'}</td>
                    <td>
                      <span className={`history-table__state history-table__state--${row.job.state}`}>
                        {row.job.state}
                        {row.job.solve_status ? ` / ${row.job.solve_status}` : ''}
                      </span>
                    </td>
                    <td>{row.job.objective ?? '—'}</td>
                    <td>
                      <Link to={`/jobs/${row.job.job_id}`}>Открыть</Link>
                    </td>
                  </tr>
                ) : (
                  <BatchRows
                    key={row.batch.batch_id}
                    batch={row.batch}
                    expanded={expanded.has(row.batch.batch_id)}
                    onToggle={() => toggle(row.batch.batch_id)}
                  />
                ),
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function BatchRows({
  batch,
  expanded,
  onToggle,
}: {
  batch: BatchResponse
  expanded: boolean
  onToggle: () => void
}) {
  return (
    <>
      <tr className="history-table__batch-row" onClick={onToggle}>
        <td className="history-table__expand">{expanded ? '▼' : '▶'}</td>
        <td>{new Date(batch.created_at).toLocaleString()}</td>
        <td>{batch.solver}</td>
        <td>Группа · {batch.total} файлов</td>
        <td>{batch.created_by ?? '—'}</td>
        <td>
          <span className={`history-table__state history-table__state--${batch.state}`}>
            {batch.state} ({batch.completed}/{batch.total})
          </span>
        </td>
        <td>—</td>
        <td>
          <Link to={`/batches/${batch.batch_id}`} onClick={(e) => e.stopPropagation()}>
            Открыть
          </Link>
        </td>
      </tr>
      {expanded &&
        batch.jobs.map((job) => (
          <tr key={job.job_id} className="history-table__child-row">
            <td></td>
            <td></td>
            <td>{job.solver}</td>
            <td>
              {job.batch_index}. {job.original_filename ?? '—'}
            </td>
            <td>{job.created_by ?? '—'}</td>
            <td>
              <span className={`history-table__state history-table__state--${job.state}`}>
                {job.state}
                {job.solve_status ? ` / ${job.solve_status}` : ''}
              </span>
            </td>
            <td>{job.objective ?? '—'}</td>
            <td>
              <Link to={`/jobs/${job.job_id}`}>Открыть</Link>
            </td>
          </tr>
        ))}
    </>
  )
}
