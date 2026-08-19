export function formatNum(value: number | null, digits = 6): string {
  if (value === null) return '—'
  if (value === 0) return '0'
  // Only tiny numbers get exponential notation — large ones (objective
  // values routinely run into the billions) are written out in full with
  // grouping, otherwise e.g. 2.663e+9 vs 2.666e+9 look deceptively close
  // when the actual difference is very real.
  if (Math.abs(value) < 1e-4) return value.toExponential(3)
  return value.toLocaleString('ru-RU', { maximumFractionDigits: digits })
}
