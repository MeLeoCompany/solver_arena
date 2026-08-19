import { Fragment, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError } from '../api/client'
import { compareJobs, downloadCompareJobsReport } from '../api/comparison'
import { listJobs } from '../api/jobs'
import type {
  CompareJobsResponse,
  JobResponse,
  ObjectiveComparisonRow,
  SolutionDiffRow,
  ViolationRow,
} from '../api/types'
import { JobPickerTable } from '../components/JobPickerTable'
import { MetricExplainer } from '../components/MetricExplainer'
import { formatNum } from '../utils/formatNumber'

export function ComparePage() {
  const [jobs, setJobs] = useState<JobResponse[] | null>(null)
  const [referenceId, setReferenceId] = useState<string | null>(null)
  const [altIds, setAltIds] = useState<Set<string>>(new Set())
  const [result, setResult] = useState<CompareJobsResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [reportLoading, setReportLoading] = useState(false)
  const [reportError, setReportError] = useState<string | null>(null)

  useEffect(() => {
    listJobs({ includeBatchJobs: true }).then((list) => setJobs(list.filter((j) => j.state === 'done')))
  }, [])

  function toggleAlt(jobId: string) {
    setAltIds((prev) => {
      const next = new Set(prev)
      if (next.has(jobId)) next.delete(jobId)
      else next.add(jobId)
      return next
    })
  }

  function handleReferenceChange(jobId: string) {
    setReferenceId(jobId)
    setAltIds((prev) => {
      if (!prev.has(jobId)) return prev
      const next = new Set(prev)
      next.delete(jobId)
      return next
    })
  }

  async function handleCompare() {
    if (!referenceId || altIds.size === 0) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      setResult(await compareJobs(referenceId, Array.from(altIds)))
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Не удалось сравнить задачи')
    } finally {
      setLoading(false)
    }
  }

  async function handleDownloadReport() {
    if (!referenceId || altIds.size === 0) return
    setReportLoading(true)
    setReportError(null)
    try {
      await downloadCompareJobsReport(referenceId, Array.from(altIds))
    } catch (err) {
      setReportError(err instanceof ApiError ? err.message : 'Не удалось выгрузить отчёт')
    } finally {
      setReportLoading(false)
    }
  }

  if (!jobs) return <div className="compare-page">Загрузка задач…</div>

  const busy = loading

  return (
    <div className="compare-page">
      <h1>Сравнение решений</h1>
      <p className="compare-page__intro">
        Выберите эталонную задачу и одну или несколько альтернативных — обычно это одна и та же
        MPS-задача, решённая разными солверами (или с разными флагами). Сравнение осмысленно только
        если задачи решают одну и ту же модель. Клик по заголовку столбца сортирует, поля под
        заголовками — фильтр по этому столбцу.
      </p>

      <div className="compare-form">
        <JobPickerTable
          jobs={jobs}
          referenceId={referenceId}
          onReferenceChange={handleReferenceChange}
          altIds={altIds}
          onToggleAlt={toggleAlt}
          disabled={busy}
        />

        {error && <div className="solve-form__error">{error}</div>}

        <button
          type="button"
          className="button button--primary"
          disabled={!referenceId || altIds.size === 0 || busy}
          onClick={handleCompare}
        >
          {loading ? 'Сравниваем…' : 'Сравнить'}
        </button>
      </div>

      {result && (
        <div className="compare-results">
          <ObjectiveSection rows={result.objective} referenceMinimize={result.reference_minimize} />
          <ViolationsSection rows={result.violations} />
          <SolutionDiffSection rows={result.solution_diff} />
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

function ObjectiveSection({
  rows,
  referenceMinimize,
}: {
  rows: ObjectiveComparisonRow[]
  referenceMinimize: boolean
}) {
  const directionWord = referenceMinimize ? 'минимизация' : 'максимизация'
  const betterWord = referenceMinimize ? 'меньше' : 'больше'

  return (
    <section className="compare-section">
      <h2>
        Целевая функция <span className="compare-section__badge">{directionWord}</span>
      </h2>
      <MetricExplainer
        description={
          `Направление оптимизации эталонной задачи — ${directionWord}, то есть ${betterWord} = лучше. ` +
          'Насколько значение целевой функции у альтернативной задачи отличается от эталонной — в ' +
          'абсолютных числах и в процентах. «Δ (эталон − альт)» — это разница, а не модуль: ' +
          'отрицательное значение означает, что у альтернативы число больше эталонного, ' +
          'положительное — меньше (независимо от направления оптимизации).'
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
              <th>Альт. задача</th>
              <th>Солвер</th>
              <th>Obj (эталон)</th>
              <th>Obj (альт)</th>
              <th>Δ (эталон − альт)</th>
              <th>Δ %</th>
              <th>Статус эталон / альт</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const senseMismatch = row.alt_minimize !== referenceMinimize
              return (
                <Fragment key={row.alt_job_id}>
                  <tr>
                    <td>
                      <Link to={`/jobs/${row.alt_job_id}`}>{row.alt_job_id.slice(0, 8)}</Link>
                    </td>
                    <td>{row.alt_solver}</td>
                    {row.error ? (
                      <td colSpan={5} className="compare-table__error">
                        {row.error}
                      </td>
                    ) : (
                      <>
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
                  {senseMismatch && (
                    <tr>
                      <td colSpan={7} className="compare-table__warning">
                        ⚠ у альтернативы другое направление оптимизации (
                        {row.alt_minimize ? 'минимизация' : 'максимизация'}) — сравнение может быть некорректным
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function ViolationsSection({ rows }: { rows: ViolationRow[] }) {
  return (
    <section className="compare-section">
      <h2>Нарушение ограничений</h2>
      <MetricExplainer
        description={
          'Проверяет, насколько сильно решение выходит за границы ограничений задачи (например, ' +
          'x + y ≤ 10) — отдельно для решения каждой задачи, это не сравнение эталона с альтернативой. ' +
          '«В допуске» = да означает, что все ограничения выполнены (с точностью до погрешности решателя).'
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
              <th>Задача</th>
              <th>Солвер</th>
              <th>Max violation</th>
              <th>Кол-во нарушений</th>
              <th>В допуске</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.job_id}>
                <td>
                  <Link to={`/jobs/${row.job_id}`}>{row.job_id.slice(0, 8)}</Link>
                </td>
                <td>{row.solver}</td>
                {row.error ? (
                  <td colSpan={3} className="compare-table__error">
                    {row.error}
                  </td>
                ) : (
                  <>
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
    </section>
  )
}

function SolutionDiffSection({ rows }: { rows: SolutionDiffRow[] }) {
  return (
    <section className="compare-section">
      <h2>Разница векторов решения</h2>
      <MetricExplainer
        description={
          'Сравнивает сами значения переменных (не только итоговую целевую функцию) — сколько ' +
          'переменных заметно отличаются между эталоном и альтернативой, и как эти отличия сказываются ' +
          'на целевой функции. Влияние показано отдельно: линейная часть и квадратичная (для QP-задач ' +
          'с квадратичным членом в целевой функции — для обычных LP/MILP она всегда 0).'
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
              <th>Альт. задача</th>
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
              <tr key={row.alt_job_id}>
                <td>
                  <Link to={`/jobs/${row.alt_job_id}`}>{row.alt_job_id.slice(0, 8)}</Link>
                </td>
                <td>{row.alt_solver}</td>
                {row.error ? (
                  <td colSpan={5} className="compare-table__error">
                    {row.error}
                  </td>
                ) : (
                  <>
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
    </section>
  )
}
