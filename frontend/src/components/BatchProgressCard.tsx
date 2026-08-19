import { Link } from 'react-router-dom'
import type { BatchResponse } from '../api/types'

const STATE_LABEL: Record<BatchResponse['state'], string> = {
  pending: 'В очереди',
  running: 'Выполняется…',
  done: 'Завершён',
  failed: 'Ошибка',
  cancelled: 'Отменён',
}

export function BatchProgressCard({ batch }: { batch: BatchResponse }) {
  const percent = batch.total > 0 ? Math.round((batch.completed / batch.total) * 100) : 0

  return (
    <div className={`result-card result-card--${batch.state}`}>
      <div className="result-card__header">
        <span className="result-card__badge">{STATE_LABEL[batch.state]}</span>
        <span className="result-card__status">
          {batch.completed} / {batch.total} задач
        </span>
      </div>

      <div className="batch-progress__bar">
        <div className="batch-progress__bar-fill" style={{ width: `${percent}%` }} />
      </div>

      <dl className="result-card__stats">
        <div>
          <dt>Solver</dt>
          <dd>{batch.solver}</dd>
        </div>
        {batch.created_by && (
          <div>
            <dt>Автор</dt>
            <dd>{batch.created_by}</dd>
          </div>
        )}
        <div>
          <dt>Batch ID</dt>
          <dd className="result-card__job-id">{batch.batch_id}</dd>
        </div>
      </dl>

      {batch.jobs.length > 0 && (
        <div className="batch-jobs-table__wrapper">
          <table className="batch-jobs-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Файл</th>
                <th>Статус</th>
                <th>Objective</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {batch.jobs.map((job) => (
                <tr key={job.job_id}>
                  <td>{job.batch_index}</td>
                  <td>{job.original_filename ?? '—'}</td>
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
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
