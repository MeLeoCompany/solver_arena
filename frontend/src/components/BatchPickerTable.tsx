import { useMemo, useState } from 'react'
import type { BatchResponse } from '../api/types'

type SortKey = 'solver' | 'total' | 'created_at'
type SortDirection = 'asc' | 'desc'

interface ColumnFilters {
  solver: string
  batchId: string
}

interface Props {
  batches: BatchResponse[]
  referenceId: string | null
  onReferenceChange: (batchId: string) => void
  altId: string | null
  onAltChange: (batchId: string) => void
  disabled?: boolean
}

export function BatchPickerTable({ batches, referenceId, onReferenceChange, altId, onAltChange, disabled }: Props) {
  const [filters, setFilters] = useState<ColumnFilters>({ solver: '', batchId: '' })
  const [sort, setSort] = useState<{ key: SortKey; direction: SortDirection }>({
    key: 'created_at',
    direction: 'desc',
  })

  function toggleSort(key: SortKey) {
    setSort((prev) =>
      prev.key === key ? { key, direction: prev.direction === 'asc' ? 'desc' : 'asc' } : { key, direction: 'asc' },
    )
  }

  function setFilter(field: keyof ColumnFilters, value: string) {
    setFilters((prev) => ({ ...prev, [field]: value }))
  }

  const rows = useMemo(() => {
    const filtered = batches.filter((batch) => {
      if (filters.solver && !batch.solver.toLowerCase().includes(filters.solver.toLowerCase())) return false
      if (filters.batchId && !batch.batch_id.toLowerCase().includes(filters.batchId.toLowerCase())) return false
      return true
    })

    return [...filtered].sort((a, b) => {
      let cmp = 0
      if (sort.key === 'solver') cmp = a.solver.localeCompare(b.solver)
      else if (sort.key === 'total') cmp = a.total - b.total
      else if (sort.key === 'created_at') cmp = a.created_at.localeCompare(b.created_at)
      return sort.direction === 'asc' ? cmp : -cmp
    })
  }, [batches, filters, sort])

  function sortIndicator(key: SortKey): string {
    if (sort.key !== key) return ''
    return sort.direction === 'asc' ? ' ▲' : ' ▼'
  }

  return (
    <div className="job-picker">
      <div className="job-picker__wrapper">
        <table className="job-picker__table">
          <thead>
            <tr>
              <th>Эталон</th>
              <th>Альт</th>
              <th className="job-picker__sortable" onClick={() => toggleSort('solver')}>
                Солвер{sortIndicator('solver')}
              </th>
              <th className="job-picker__sortable" onClick={() => toggleSort('total')}>
                Файлов{sortIndicator('total')}
              </th>
              <th>Готово</th>
              <th className="job-picker__sortable" onClick={() => toggleSort('created_at')}>
                Создан{sortIndicator('created_at')}
              </th>
              <th>Batch ID</th>
            </tr>
            <tr className="job-picker__filter-row">
              <th></th>
              <th></th>
              <th>
                <input
                  value={filters.solver}
                  placeholder="фильтр…"
                  onChange={(e) => setFilter('solver', e.target.value)}
                />
              </th>
              <th></th>
              <th></th>
              <th></th>
              <th>
                <input
                  value={filters.batchId}
                  placeholder="фильтр…"
                  onChange={(e) => setFilter('batchId', e.target.value)}
                />
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={7} className="job-picker__empty">
                  Нет завершённых групп
                </td>
              </tr>
            ) : (
              rows.map((batch) => {
                const isReference = batch.batch_id === referenceId
                const isAlt = batch.batch_id === altId
                return (
                  <tr key={batch.batch_id} className={isReference ? 'job-picker__row--reference' : undefined}>
                    <td>
                      <input
                        type="radio"
                        name="reference-batch"
                        checked={isReference}
                        disabled={disabled}
                        onChange={() => onReferenceChange(batch.batch_id)}
                      />
                    </td>
                    <td>
                      <input
                        type="radio"
                        name="alt-batch"
                        checked={isAlt}
                        disabled={disabled || isReference}
                        onChange={() => onAltChange(batch.batch_id)}
                      />
                    </td>
                    <td>{batch.solver}</td>
                    <td>{batch.total}</td>
                    <td>
                      {batch.completed} / {batch.total}
                    </td>
                    <td>{new Date(batch.created_at).toLocaleString()}</td>
                    <td className="job-picker__job-id">{batch.batch_id.slice(0, 8)}</td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
