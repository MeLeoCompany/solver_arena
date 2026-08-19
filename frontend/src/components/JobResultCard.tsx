import type { JobResponse } from '../api/types'

const STATE_LABEL: Record<JobResponse['state'], string> = {
  pending: 'В очереди',
  running: 'Решается…',
  done: 'Завершено',
  failed: 'Ошибка',
  cancelled: 'Отменено',
}

const STATUS_LABEL: Record<NonNullable<JobResponse['solve_status']>, string> = {
  optimal: 'Оптимально',
  feasible: 'Допустимое решение',
  infeasible: 'Задача нерешаема',
  timeout: 'Не успел за лимит времени',
  unbounded: 'Задача неограничена',
}

export function JobResultCard({ job }: { job: JobResponse }) {
  return (
    <div className={`result-card result-card--${job.state}`}>
      <div className="result-card__header">
        <span className="result-card__badge">{STATE_LABEL[job.state]}</span>
        {job.solve_status && (
          <span className="result-card__status">{STATUS_LABEL[job.solve_status]}</span>
        )}
      </div>

      <dl className="result-card__stats">
        {job.objective !== null && (
          <div>
            <dt>Целевая функция</dt>
            <dd>{job.objective}</dd>
          </div>
        )}
        {job.solve_time !== null && (
          <div>
            <dt>Время решения</dt>
            <dd>{job.solve_time.toFixed(2)} с</dd>
          </div>
        )}
        <div>
          <dt>Solver</dt>
          <dd>{job.solver}</dd>
        </div>
        {job.created_by && (
          <div>
            <dt>Автор</dt>
            <dd>{job.created_by}</dd>
          </div>
        )}
        <div>
          <dt>Job ID</dt>
          <dd className="result-card__job-id">{job.job_id}</dd>
        </div>
      </dl>

      {job.error && <div className="result-card__error">{job.error}</div>}

      <div className="result-card__actions">
        {job.log_url && (
          <a className="button" href={job.log_url} download={`${job.job_id}.log`}>
            Скачать полный лог
          </a>
        )}
        {job.solution_url && (
          <a className="button" href={job.solution_url} download={`${job.job_id}.json`}>
            Скачать решение
          </a>
        )}
      </div>
    </div>
  )
}
