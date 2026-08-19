import { useState } from 'react'
import type { SolverInfo } from '../api/solvers'

interface Props {
  solvers: SolverInfo[]
  onRefresh: () => void
  refreshing: boolean
}

export function AvailabilityPanel({ solvers, onRefresh, refreshing }: Props) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null)
  const expanded = solvers.find((s) => s.key === expandedKey && !s.available && s.availability_detail)

  return (
    <div className="availability-panel">
      <div className="availability-panel__header">
        <span>Доступность солверов на этой машине</span>
        <button type="button" className="button" disabled={refreshing} onClick={onRefresh}>
          {refreshing ? 'Проверяем…' : 'Обновить'}
        </button>
      </div>
      <ul className="availability-panel__list">
        {solvers.map((s) => (
          <li
            key={s.key}
            className={`availability-panel__item availability-panel__item--${s.available ? 'ok' : 'down'}`}
          >
            <span className="availability-panel__dot" />
            <span className="availability-panel__label">{s.label}</span>
            {!s.available && s.availability_detail && (
              <button
                type="button"
                className="availability-panel__why"
                aria-label={`Почему ${s.label} недоступен`}
                onClick={() => setExpandedKey((key) => (key === s.key ? null : s.key))}
              >
                ?
              </button>
            )}
          </li>
        ))}
      </ul>
      {expanded && (
        <div className="availability-panel__note">
          <strong>{expanded.label}:</strong> {expanded.availability_detail}
        </div>
      )}
    </div>
  )
}
