import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { activateQoreVersion, listQoreVersions, uploadQoreVersion } from '../api/qoreVersions'
import type { QoreVersionResponse } from '../api/types'
import { FileDropZone } from '../components/FileDropZone'
import { UploadProgressBar } from '../components/UploadProgressBar'

export function QoreVersionsPage() {
  const [versions, setVersions] = useState<QoreVersionResponse[] | null>(null)
  const [soFile, setSoFile] = useState<File | null>(null)
  const [label, setLabel] = useState('')
  const [uploading, setUploading] = useState(false)
  const [activatingId, setActivatingId] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<QoreVersionResponse | null>(null)
  const [uploadPercent, setUploadPercent] = useState<number | null>(null)

  function reload() {
    listQoreVersions()
      .then(setVersions)
      .catch((err) => setError(err instanceof ApiError ? err.message : 'Не удалось загрузить список версий'))
  }

  useEffect(reload, [])

  async function handleUpload() {
    if (!soFile || !label.trim()) return
    setUploading(true)
    setError(null)
    setLastResult(null)
    setUploadPercent(0)
    try {
      const result = await uploadQoreVersion(soFile, label.trim(), setUploadPercent)
      setLastResult(result)
      setSoFile(null)
      setLabel('')
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось загрузить файл')
    } finally {
      setUploading(false)
      setUploadPercent(null)
    }
  }

  async function handleActivate(id: number) {
    setActivatingId(id)
    setError(null)
    try {
      await activateQoreVersion(id)
      reload()
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось активировать версию')
    } finally {
      setActivatingId(null)
    }
  }

  return (
    <div className="tokens-page">
      <h1>Версии QORE</h1>
      <p className="tokens-page__hint">
        У QORE нет собственной версии в API — метка ниже вводится вручную и служит просто
        подписью для истории. Перед тем как новый файл станет активным, он проходит smoke-тест
        (тот же, что и обычная проверка доступности солвера); если тест не пройден — текущий
        рабочий файл не трогается, а неудачная загрузка остаётся в истории для отладки.
      </p>

      <div className="tokens-page__create">
        <FileDropZone
          file={soFile}
          onFileSelected={setSoFile}
          disabled={uploading}
          accept=".so"
          placeholder="Перетащите .so сюда или нажмите, чтобы выбрать"
        />
        <input
          placeholder="Метка/комментарий (например: qore 2.4 от вендора, 22.08)"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          disabled={uploading}
        />
        <button
          type="button"
          className="button button--primary"
          disabled={uploading || !soFile || !label.trim()}
          onClick={handleUpload}
        >
          {uploading ? 'Загружаем и проверяем…' : 'Загрузить'}
        </button>
      </div>

      {uploadPercent !== null && uploadPercent < 100 && <UploadProgressBar percent={uploadPercent} />}

      {error && <div className="tokens-page__error">{error}</div>}

      {lastResult && (
        <div
          className={
            lastResult.smoke_test_ok ? 'qore-versions__result qore-versions__result--ok' : 'qore-versions__result qore-versions__result--fail'
          }
        >
          {lastResult.smoke_test_ok
            ? `«${lastResult.label}» прошла smoke-тест и стала активной.`
            : `«${lastResult.label}» не прошла smoke-тест — рабочий файл не менялся. Причина: ${lastResult.smoke_test_output ?? 'неизвестно'}`}
        </div>
      )}

      {versions && (
        <table className="tokens-table">
          <thead>
            <tr>
              <th>Метка</th>
              <th>Статус</th>
              <th>Загрузил</th>
              <th>Когда</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {versions.map((v) => (
              <tr key={v.id}>
                <td>{v.label}</td>
                <td>
                  {v.active && <span className="qore-versions__badge qore-versions__badge--active">активна</span>}
                  {!v.active && v.smoke_test_ok && <span>прошла тест</span>}
                  {!v.smoke_test_ok && (
                    <span className="qore-versions__badge qore-versions__badge--fail" title={v.smoke_test_output ?? ''}>
                      тест не пройден
                    </span>
                  )}
                </td>
                <td>{v.uploaded_by ?? '—'}</td>
                <td>{new Date(v.uploaded_at).toLocaleString()}</td>
                <td>
                  {!v.active && (
                    <button
                      type="button"
                      className="button"
                      disabled={activatingId === v.id}
                      onClick={() => handleActivate(v.id)}
                    >
                      {activatingId === v.id ? 'Проверяем…' : 'Сделать активной'}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
