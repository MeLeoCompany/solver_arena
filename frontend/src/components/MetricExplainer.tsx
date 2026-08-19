export function MetricExplainer({ description, formula }: { description: string; formula: string }) {
  return (
    <div className="metric-explainer">
      <div className="metric-explainer__description">{description}</div>
      <div className="metric-explainer__label">Формула</div>
      <pre className="metric-explainer__formula">{formula}</pre>
    </div>
  )
}
