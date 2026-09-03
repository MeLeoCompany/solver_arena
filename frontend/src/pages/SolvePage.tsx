import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileDropZone } from '../components/FileDropZone'
import { FlagsEditor } from '../components/FlagsEditor'
import { QoreConfigEditor } from '../components/QoreConfigEditor'
import { LogPanel } from '../components/LogPanel'
import { JobResultCard } from '../components/JobResultCard'
import { AvailabilityPanel } from '../components/AvailabilityPanel'
import { ConfirmModal } from '../components/ConfirmModal'
import { UploadProgressBar } from '../components/UploadProgressBar'
import { listSolvers, refreshSolvers, solveEndpoint, type SolverInfo } from '../api/solvers'
import { submitSolve, cancelJob } from '../api/jobs'
import type { JobResponse } from '../api/types'
import { ApiError } from '../api/client'
import { useSystemStatus } from '../status/SystemStatusContext'
import { pluralRu } from '../utils/pluralize'
import { randomUUID } from '../utils/uuid'

type Phase = 'idle' | 'running' | 'cancelling' | 'settled'

export function SolvePage() {
  const navigate = useNavigate()
  const [solvers, setSolvers] = useState<SolverInfo[] | null>(null)
  const [solverKey, setSolverKey] = useState<string | null>(null)
  const [refreshingSolvers, setRefreshingSolvers] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [flagValues, setFlagValues] = useState<Record<string, string>>({})
  const [phase, setPhase] = useState<Phase>('idle')
  const [jobId, setJobId] = useState<string | null>(null)
  const [result, setResult] = useState<JobResponse | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [showBusyConfirm, setShowBusyConfirm] = useState(false)
  const [uploadPercent, setUploadPercent] = useState<number | null>(null)
  const activeJobs = useSystemStatus()

  useEffect(() => {
    listSolvers().then((list) => {
      setSolvers(list)
      setSolverKey((current) => current ?? list.find((s) => s.available)?.key ?? list[0]?.key ?? null)
    })
  }, [])

  async function handleRefreshSolvers() {
    setRefreshingSolvers(true)
    try {
      const list = await refreshSolvers()
      setSolvers(list)
    } finally {
      setRefreshingSolvers(false)
    }
  }

  const solver = solvers?.find((s) => s.key === solverKey) ?? null
  const busy = phase === 'running' || phase === 'cancelling'

  function handleSubmit() {
    if (!file || !solver) return
    if (activeJobs && activeJobs > 0) {
      setShowBusyConfirm(true)
      return
    }
    void doSubmit()
  }

  async function doSubmit() {
    if (!file || !solver) return
    const newJobId = randomUUID()
    setJobId(newJobId)
    setResult(null)
    setSubmitError(null)
    setUploadPercent(0)
    setPhase('running')

    try {
      const response = await submitSolve(solveEndpoint(solver.key), newJobId, file, flagValues, setUploadPercent)
      setResult(response)
      setPhase('settled')
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Не удалось отправить задачу')
      setPhase('idle')
    } finally {
      setUploadPercent(null)
    }
  }

  async function handleCancel() {
    if (!jobId) return
    setPhase('cancelling')
    try {
      await cancelJob(jobId)
    } catch {
      // job may have finished right before the cancel landed — the in-flight
      // solve request will still resolve on its own either way
    }
  }

  function handleReset() {
    setPhase('idle')
    setJobId(null)
    setResult(null)
  }

  if (!solvers || !solver) {
    return <div className="solve-page">Загрузка солверов…</div>
  }

  return (
    <div className="solve-page">
      <h1>Новая задача</h1>

      <AvailabilityPanel solvers={solvers} onRefresh={handleRefreshSolvers} refreshing={refreshingSolvers} />

      {phase !== 'settled' && (
        <div className="solve-form">
          <label className="solve-form__solver">
            Солвер
            <select
              value={solverKey ?? ''}
              onChange={(e) => setSolverKey(e.target.value)}
              disabled={busy}
            >
              {solvers.map((s) => (
                <option key={s.key} value={s.key} disabled={!s.available}>
                  {s.label}
                  {!s.available ? ' (недоступен)' : ''}
                </option>
              ))}
            </select>
          </label>

          {!solver.available && (
            <div className="solve-form__error">
              Солвер «{solver.label}» сейчас недоступен{solver.availability_detail ? `: ${solver.availability_detail}` : ''}
            </div>
          )}

          <FileDropZone file={file} onFileSelected={setFile} disabled={busy} />

          {solver.key === 'qore' ? (
            <QoreConfigEditor
              value={flagValues.config ?? ''}
              onChange={(text) => setFlagValues({ config: text })}
              disabled={busy}
            />
          ) : (
            <FlagsEditor
              parameterNames={solver.parameters}
              values={flagValues}
              onChange={setFlagValues}
              disabled={busy}
            />
          )}

          {submitError && <div className="solve-form__error">{submitError}</div>}

          {!busy ? (
            <button
              type="button"
              className="button button--primary"
              disabled={!file || !solver.available}
              onClick={handleSubmit}
            >
              Решить
            </button>
          ) : (
            <button
              type="button"
              className="button button--danger"
              disabled={phase === 'cancelling'}
              onClick={handleCancel}
            >
              {phase === 'cancelling' ? 'Отменяем…' : 'Отменить'}
            </button>
          )}
        </div>
      )}

      {uploadPercent !== null && uploadPercent < 100 && <UploadProgressBar percent={uploadPercent} />}

      {jobId && phase !== 'idle' && (
        <div className="solve-page__logs">
          <h2>Логи</h2>
          <LogPanel jobId={jobId} live={phase !== 'settled'} />
        </div>
      )}

      {phase === 'settled' && result && (
        <div className="solve-page__result">
          {result.state === 'cancelled' && (
            <div className="solve-page__cancel-ok">Задача успешно отменена ✓</div>
          )}
          <JobResultCard job={result} />
          <div className="solve-page__result-actions">
            <button type="button" className="button" onClick={handleReset}>
              Новая задача
            </button>
            <button
              type="button"
              className="button"
              onClick={() => navigate(`/jobs/${result.job_id}`)}
            >
              Постоянная ссылка на результат
            </button>
          </div>
        </div>
      )}

      {showBusyConfirm && activeJobs !== null && (
        <ConfirmModal
          title="Сервер занят"
          message={`Сейчас выполняется ${activeJobs} ${pluralRu(activeJobs, 'расчёт', 'расчёта', 'расчётов')}. Это может повлиять на время и результаты вашего расчёта.`}
          onConfirm={() => {
            setShowBusyConfirm(false)
            void doSubmit()
          }}
          onCancel={() => setShowBusyConfirm(false)}
        />
      )}
    </div>
  )
}
