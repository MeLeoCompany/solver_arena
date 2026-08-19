import { useEffect, useState } from 'react'
import { getFullLog, logStreamUrl } from '../api/jobs'
import { useStickToBottom } from '../hooks/useStickToBottom'
import { isBannerLine } from '../utils/logLines'

interface Props {
  jobId: string
  live: boolean
}

export function LogPanel({ jobId, live }: Props) {
  const [lines, setLines] = useState<string[]>([])
  const { containerRef, handleScroll, scrollToBottomIfSticking, resetSticking } =
    useStickToBottom<HTMLDivElement>()

  useEffect(() => {
    setLines([])
    resetSticking()
    if (live) {
      const source = new EventSource(logStreamUrl(jobId))
      source.onmessage = (event) => setLines((prev) => [...prev, event.data])
      return () => source.close()
    }
    getFullLog(jobId)
      .then((text) => setLines(text.length > 0 ? text.split('\n') : []))
      .catch(() => setLines(['(не удалось загрузить лог)']))
  }, [jobId, live, resetSticking])

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
