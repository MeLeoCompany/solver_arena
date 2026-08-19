import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listBatches } from '../api/batches'
import { ApiError } from '../api/client'
import { compareBatches, downloadCompareBatchesReport } from '../api/comparison'
import type {
  BatchResponse,
  CompareBatchesResponse,
  ObjectiveComparisonRow,
  SolutionDiffRow,
  ViolationRow,
} from '../api/types'
import { BatchPickerTable } from '../components/BatchPickerTable'
import { MetricExplainer } from '../components/MetricExplainer'
import { formatNum } from '../utils/formatNumber'

export function CompareBatchesPage() {
  const [batches, setBatches] = useState<BatchResponse[] | null>(null)
  const [referenceId, setReferenceId] = useState<string | null>(null)
  const [altId, setAltId] = useState<string | null>(null)
  const [result, setResult] = useState<CompareBatchesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  useEffect(() => {
    listBatches().then((list) => setBatches(list.filter((b) => b.state === 'done')))
  }, [])

  function handleReferenceChange(batchId: string) {
    setReferenceId(batchId)
    if (altId === batchId) setAltId(null)
  }

  async function handleCompare() {
    if (!referenceId || !altId) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await compareBatches(referenceId, altId))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось сравнить группы')
    } finally {
      setLoading(false)
    }
  }

  async function handleDownloadReport() {
    if (!referenceId || !altId) return
    setReportLoading(true)
    setReportError(null)
    try {
      await downloadCompareBatchesReport(referenceId, altId)
    } catch (err) {
      setReportError(err instanceof ApiError ? err.message : 'Не удалось выгрузить отчёт')
    } finally {
      setReportLoading(false)
    }
  }

  if (!batches) return <div className="compare-page">Загрузка групп…</div>

  const busy = loading
  const total = result?.objective.length ?? 0
  const withError = result?.objective.filter((row) => row.error).length ?? 0

  return (
    <div className="compare-page">
      <h1>Сравнение групп</h1>
      <p className="compare-page__intro">
        Выберите эталонную группу и одну альтернативную — файлы сопоставляются по порядковому
        номеру внутри группы (тому же для обеих групп, если они были загружены из одинаково
        отсортированных zip-архивов). Клик по заголовку столбца сортирует, поля под заголовками —
        фильтр по этому столбцу.
      </p>

      <div className="compare-form">
        <BatchPickerTable
          batches={batches}
          referenceId={referenceId}
          onReferenceChange={handleReferenceChange}
          altId={altId}
          onAltChange={setAltId}
          disabled={busy}
        />

        {error && <div className="solve-form__error">{error}</div>}

        <button
          type="button"
          className="button button--primary"
          disabled={!referenceId || !altId || busy}
          onClick={handleCompare}
        >
          {loading ? 'Сравниваем…' : 'Сравнить'}
        </button>
      </div>

      {result && (
        <div className="compare-results">
          <p className="compare-batches__summary">
            Сопоставлено файлов: {total}
            {withError > 0 && `, из них с ошибкой сопоставления: ${withError}`}
          </p>
          <BatchObjectiveSection rows={result.objective} />
          <BatchViolationsSection rows={result.violations} />
          <BatchSolutionDiffSection rows={result.solution_diff} />
          <div className="compare-results__actions compare-results__actions--bottom">
            <button
              type="button"
              className="button button--primary"
              disabled={reportLoading}
              onClick={handleDownloadReport}
            >
              {reportLoading ? 'Готовим отчёт…' : 'Выгрузить в отчёт'}
            </button>
            {reportError && <span className="solve-form__error">{reportError}</span>}
          </div>
        </div>
      )}
    </div>
  )
}

function fileLabel(reference: string | null, alt: string | null): string {
  if (reference && alt && reference !== alt) return `${reference} / ${alt}`
  return reference ?? alt ?? '—'
}

function refLink(jobId: string | null) {
  if (!jobId) return '—'
  return <Link to={`/jobs/${jobId}`}>{jobId.slice(0, 8)}</Link>
}

function BatchObjectiveSection({ rows }: { rows: ObjectiveComparisonRow[] }) {
  return (
    <details className="compare-section" open>
      <summary>
        <h2>Целевая функция</h2>
      </summary>
      <MetricExplainer
        description={
          'То же сравнение, что и для одиночных задач, только по каждому файлу группы отдельно. ' +
          '«Δ (эталон − альт)» — это разница, а не модуль: отрицательное значение означает, что у ' +
          'альтернативы число больше эталонного, положительное — меньше.'
        }
        formula={
          'Δ_abs = obj(эталон) − obj(альт)\n' +
          'Δ_% = Δ_abs / max(|obj(эталон)|, |obj(альт)|, ε) × 100,   ε = 1e-9'
        }
      />
      <div className="compare-table__wrapper">
        <table className="compare-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Файл</th>
              <th>Эталон</th>
              <th>Альт</th>
              <th>Солвер</th>
              <th>Obj (эталон)</th>
              <th>Obj (альт)</th>
              <th>Δ (эталон − альт)</th>
              <th>Δ %</th>
              <th>Статус эталон / альт</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <Fragment key={`${row.batch_index}-${row.alt_job_id || row.reference_job_id}`}>
                <tr>
                  <td>{row.batch_index}</td>
                  <td>{fileLabel(row.reference_filename, row.alt_filename)}</td>
                  <td>{refLink(row.reference_job_id)}</td>
                  <td>{row.alt_job_id ? <Link to={`/jobs/${row.alt_job_id}`}>{row.alt_job_id.slice(0, 8)}</Link> : '—'}</td>
                  {row.error ? (
                    <td colSpan={6} className="compare-table__error">
                      {row.error}
                    </td>
                  ) : (
                    <>
                      <td>{row.alt_solver}</td>
                      <td>{formatNum(row.reference_objective)}</td>
                      <td>{formatNum(row.alt_objective)}</td>
                      <td>{formatNum(row.delta_abs)}</td>
                      <td>{formatNum(row.delta_rel_pct)}%</td>
                      <td>
                        {row.reference_status ?? '—'} / {row.alt_status ?? '—'}
                      </td>
                    </>
                  )}
                </tr>
              </Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

function BatchViolationsSection({ rows }: { rows: ViolationRow[] }) {
  return (
    <details className="compare-section" open>
      <summary>
        <h2>Нарушение ограничений</h2>
      </summary>
      <MetricExplainer
        description={
          'Проверяет, насколько сильно решение выходит за границы ограничений задачи — отдельно ' +
          'для решения каждого файла в каждой группе, это не сравнение эталона с альтернативой.'
        }
        formula={
          'Для ограничения i с границами [lo_i, hi_i]:\n' +
          'нарушение_i = насколько (Ax)_i вышло за пределы [lo_i, hi_i], иначе 0\n' +
          'max_violation = наибольшее нарушение среди всех ограничений\n' +
          'в допуске = max_violation ≤ ε,   ε = 1e-6'
        }
      />
      <div className="compare-table__wrapper">
        <table className="compare-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Файл</th>
              <th>Задача</th>
              <th>Солвер</th>
              <th>Max violation</th>
              <th>Кол-во нарушений</th>
              <th>В допуске</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.batch_index}-${row.job_id}`}>
                <td>{row.batch_index}</td>
                <td>{row.filename ?? '—'}</td>
                <td>
                  <Link to={`/jobs/${row.job_id}`}>{row.job_id.slice(0, 8)}</Link>
                </td>
                {row.error ? (
                  <td colSpan={4} className="compare-table__error">
                    {row.error}
                  </td>
                ) : (
                  <>
                    <td>{row.solver}</td>
                    <td>{formatNum(row.max_violation)}</td>
                    <td>{row.num_violations}</td>
                    <td className={row.within_tolerance ? 'compare-table__ok' : 'compare-table__bad'}>
                      {row.within_tolerance ? 'да' : 'нет'}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}

function BatchSolutionDiffSection({ rows }: { rows: SolutionDiffRow[] }) {
  return (
    <details className="compare-section" open>
      <summary>
        <h2>Разница векторов решения</h2>
      </summary>
      <MetricExplainer
        description={
          'Сравнивает сами значения переменных — сколько переменных заметно отличаются между ' +
          'эталоном и альтернативой в каждом файле группы, и как эти отличия сказываются на ' +
          'целевой функции (линейная часть и квадратичная — для QP-задач).'
        }
        formula={
          'Δx = x(эталон) − x(альт)\n' +
          'Кол-во отличий — число переменных с |Δx_i| > ε, влияющих на целевую функцию,   ε = 1e-6\n' +
          'Impact линейный = Σ f_i·Δx_i  по этим переменным\n' +
          'Impact квадратичный = 0.5·x(эталон)ᵀQx(эталон) − 0.5·x(альт)ᵀQx(альт)\n' +
          'Impact итого = линейный + квадратичный'
        }
      />
      <div className="compare-table__wrapper">
        <table className="compare-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Файл</th>
              <th>Эталон</th>
              <th>Альт</th>
              <th>Солвер</th>
              <th>Кол-во отличий</th>
              <th>Макс. |Δx|</th>
              <th>Impact линейный</th>
              <th>Impact квадратичный</th>
              <th>Impact итого</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={`${row.batch_index}-${row.alt_job_id || row.reference_job_id}`}>
                <td>{row.batch_index}</td>
                <td>{fileLabel(row.reference_filename, row.alt_filename)}</td>
                <td>{refLink(row.reference_job_id)}</td>
                <td>{row.alt_job_id ? <Link to={`/jobs/${row.alt_job_id}`}>{row.alt_job_id.slice(0, 8)}</Link> : '—'}</td>
                {row.error ? (
                  <td colSpan={6} className="compare-table__error">
                    {row.error}
                  </td>
                ) : (
                  <>
                    <td>{row.alt_solver}</td>
                    <td>{row.num_diffs}</td>
                    <td>{formatNum(row.max_diff)}</td>
                    <td>{formatNum(row.objective_impact_linear)}</td>
                    <td>{formatNum(row.objective_impact_quadratic)}</td>
                    <td>{formatNum(row.objective_impact_total)}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  )
}
