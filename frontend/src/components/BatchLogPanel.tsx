import { useEffect, useState } from 'react'
import { batchLogStreamUrl } from '../api/batches'
import { useStickToBottom } from '../hooks/useStickToBottom'
import { isBannerLine } from '../utils/logLines'

interface Props {
  batchId: string
}

export function BatchLogPanel({ batchId }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const { containerRef, handleScroll, scrollToBottomIfSticking, resetSticking } =
    useStickToBottom<HTMLDivElement>()

  useEffect(() => {
    setLines([])
    resetSticking()
    const source = new EventSource(batchLogStreamUrl(batchId))
    source.onmessage = (event) => setLines((prev) => [...prev, event.data])
    return () => source.close()
  }, [batchId, resetSticking])

  useEffect(() => {
    scrollToBottomIfSticking()
  }, [lines, scrollToBottomIfSticking])

  return (
    <div className="log-panel" ref={containerRef} onScroll={handleScroll}>
      {lines.length === 0 ? (
        <div className="log-panel__empty">Логов пока нет…</div>
      ) : (
        lines.map((line, i) => (
          <div
            key={i}
            className={`log-panel__line${isBannerLine(line) ? ' log-panel__line--banner' : ''}`}
          >
            {line}
          </div>
        ))
      )}
    </div>
  )
}
