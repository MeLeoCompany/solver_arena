import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { getJob } from '../api/jobs'
import { JobResultCard } from '../components/JobResultCard'
import { LogPanel } from '../components/LogPanel'
import type { JobResponse } from '../api/types'
import { ApiError } from '../api/client'

export function JobPage() {
  const { jobId } = useParams<{ jobId: string }>()
  const [job, setJob] = useState<JobResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!jobId) return
    getJob(jobId)
      .then(setJob)
      .catch((err) =>
        setError(err instanceof ApiError && err.status === 404 ? 'Задача не найдена' : 'Ошибка загрузки'),
      )
  }, [jobId])

  if (error) return <div className="job-page__error">{error}</div>
  if (!job || !jobId) return <div className="job-page__loading">Загрузка…</div>

  return (
    <div className="job-page">
      <h1>Задача {job.job_id}</h1>
      <JobResultCard job={job} />
      <h2>Лог</h2>
      <LogPanel jobId={jobId} live={false} />
    </div>
  )
}
