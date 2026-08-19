import { useEffect, useState } from 'react'
import { ApiError } from '../api/client'
import { getBatch } from '../api/batches'
import type { BatchResponse } from '../api/types'

const POLL_INTERVAL_MS = 1500
const ACTIVE_STATES: BatchResponse['state'][] = ['pending', 'running']

export function useBatchPolling(batchId: string | null) {
  const [batch, setBatch] = useState<BatchResponse | null>(null)
  const [notFound, setNotFound] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    setBatch(null)
    setNotFound(false)
    setError(false)
    if (!batchId) return

    let cancelled = false
    let timer: ReturnType<typeof setTimeout>

    async function poll() {
      try {
        const response = await getBatch(batchId as string)
        if (cancelled) return
        setBatch(response)
        if (ACTIVE_STATES.includes(response.state)) {
          timer = setTimeout(poll, POLL_INTERVAL_MS)
        }
      } catch (err) {
        if (cancelled) return
        if (err instanceof ApiError && err.status === 404) setNotFound(true)
        else setError(true)
      }
    }
    poll()

    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [batchId])

  return { batch, notFound, error }
}
