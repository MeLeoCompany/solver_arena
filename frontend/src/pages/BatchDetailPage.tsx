import { useParams } from 'react-router-dom'
import { BatchLogPanel } from '../components/BatchLogPanel'
import { BatchProgressCard } from '../components/BatchProgressCard'
import { useBatchPolling } from '../hooks/useBatch'

export function BatchDetailPage() {
  const { batchId } = useParams<{ batchId: string }>()
  const { batch, notFound, error } = useBatchPolling(batchId ?? null)

  if (notFound) return <div className="job-page__error">Группа задач не найдена</div>
  if (error) return <div className="job-page__error">Ошибка загрузки</div>
  if (!batch || !batchId) return <div className="job-page__loading">Загрузка…</div>

  return (
    <div className="job-page">
      <h1>Группа задач</h1>
      <BatchProgressCard batch={batch} />

      {batch.state === 'running' && (
        <>
          <h2>Логи</h2>
          <BatchLogPanel batchId={batchId} />
        </>
      )}
    </div>
  )
}
