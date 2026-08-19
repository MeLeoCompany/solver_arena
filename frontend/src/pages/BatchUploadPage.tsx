import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FileDropZone } from '../components/FileDropZone'
import { FlagsEditor } from '../components/FlagsEditor'
import { QoreConfigEditor } from '../components/QoreConfigEditor'
import { BatchLogPanel } from '../components/BatchLogPanel'
import { BatchProgressCard } from '../components/BatchProgressCard'
import { AvailabilityPanel } from '../components/AvailabilityPanel'
import { ConfirmModal } from '../components/ConfirmModal'
import { listSolvers, refreshSolvers, type SolverInfo } from '../api/solvers'
import { cancelBatch, submitBatch } from '../api/batches'
import { useBatchPolling } from '../hooks/useBatch'
import { ApiError } from '../api/client'
import { useSystemStatus } from '../status/SystemStatusContext'
import { pluralRu } from '../utils/pluralize'

type Phase = 'idle' | 'submitting' | 'running' | 'settled'

export function BatchUploadPage() {
  const navigate = useNavigate()
  const [solvers, setSolvers] = useState<SolverInfo[] | null>(null)
  const [solverKey, setSolverKey] = useState<string | null>(null)
  const [refreshingSolvers, setRefreshingSolvers] = useState(false)
  const [zipFile, setZipFile] = useState<File | null>(null)
  const [flagValues, setFlagValues] = useState<Record<string, string>>({})
  const [phase, setPhase] = useState<Phase>('idle')
  const [batchId, setBatchId] = useState<string | null>(null)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const [showBusyConfirm, setShowBusyConfirm] = useState(false)
  const activeJobs = useSystemStatus()

  useEffect(() => {
    listSolvers().then((list) => {
      setSolvers(list)
      setSolverKey((current) => current ?? list.find((s) => s.available)?.key ?? list[0]?.key ?? null)
    })
  }, [])

  const { batch } = useBatchPolling(batchId)

  useEffect(() => {
    if (batch && batch.state !== 'running' && batch.state !== 'pending') {
      setPhase('settled')
    }
  }, [batch])

  async function handleRefreshSolvers() {
    setRefreshingSolvers(true)
    try {
      setSolvers(await refreshSolvers())
    } finally {
      setRefreshingSolvers(false)
    }
  }

  const solver = solvers?.find((s) => s.key === solverKey) ?? null
  const busy = phase === 'submitting' || phase === 'running'

  function handleSubmit() {
    if (!zipFile || !solver) return
    if (activeJobs && activeJobs > 0) {
      setShowBusyConfirm(true)
      return
    }
    void doSubmit()
  }

  async function doSubmit() {
    if (!zipFile || !solver) return
    setSubmitError(null)
    setPhase('submitting')
    try {
      const response = await submitBatch(solver.key, zipFile, flagValues)
      setBatchId(response.batch_id)
      setPhase('running')
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : 'Не удалось отправить группу задач')
      setPhase('idle')
    }
  }

  async function handleCancel() {
    if (!batchId) return
    setCancelling(true)
    try {
      await cancelBatch(batchId)
    } catch {
      // batch may have finished right before the cancel landed
    } finally {
      setCancelling(false)
    }
  }

  function handleReset() {
    setPhase('idle')
    setBatchId(null)
    setZipFile(null)
    setSubmitError(null)
  }

  if (!solvers || !solver) {
    return <div className="solve-page">Загрузка солверов…</div>
  }

  return (
    <div className="solve-page">
      <h1>Группа задач</h1>

      <AvailabilityPanel solvers={solvers} onRefresh={handleRefreshSolvers} refreshing={refreshingSolvers} />

      {phase === 'idle' && (
        <div className="solve-form">
          <label className="solve-form__solver">
            Солвер
            <select value={solverKey ?? ''} onChange={(e) => setSolverKey(e.target.value)} disabled={busy}>
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

          <FileDropZone
            file={zipFile}
            onFileSelected={setZipFile}
            disabled={busy}
            accept=".zip"
            placeholder="Перетащите zip-архив с .mps файлами сюда или нажмите, чтобы выбрать"
          />
          <div className="solve-form__hint">
            Одни и те же флаги применяются ко всем задачам архива. Задачи решаются строго по очереди,
            одна за другой, — солвер получает все ресурсы целиком на каждой из них, чтобы сравнение
            между солверами оставалось честным.
          </div>

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

          <button
            type="button"
            className="button button--primary"
            disabled={!zipFile || !solver.available}
            onClick={handleSubmit}
          >
            Запустить группу
          </button>
        </div>
      )}

      {phase === 'submitting' && <div className="solve-page__loading">Загружаем архив…</div>}

      {batchId && phase !== 'idle' && (
        <div className="solve-page__result">
          {batch && <BatchProgressCard batch={batch} />}

          {phase === 'running' && (
            <button
              type="button"
              className="button button--danger"
              disabled={cancelling}
              onClick={handleCancel}
            >
              {cancelling ? 'Отменяем…' : 'Отменить'}
            </button>
          )}

          <div className="solve-page__logs">
            <h2>Логи</h2>
            <BatchLogPanel batchId={batchId} />
          </div>

          {phase === 'settled' && (
            <div className="solve-page__result-actions">
              <button type="button" className="button" onClick={handleReset}>
                Новая группа
              </button>
              <button type="button" className="button" onClick={() => navigate(`/batches/${batchId}`)}>
                Постоянная ссылка на группу
              </button>
            </div>
          )}
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
