import { fmtMetric, type Query, type Run } from '../api'

export function RunReport({ run, queries }: { run: Run; queries: Query[] }) {
  const r = run.report
  const ev = r.evidence
  const cands = ev?.top_candidates ?? []
  const fmt = (n: number) => fmtMetric(n, ev?.metric)
  return (
    <section className="card" aria-label="Report">
      <div className="head">
        <h2>{run.question}</h2>
        <span className={`badge ${r.confidence ?? 'unknown'}`}>{r.confidence ?? 'unknown'} confidence</span>
        {run.cached && <span className="badge cached">from cache (DynamoDB)</span>}
      </div>
      <p className="summary">{r.summary}</p>
      {r.root_cause_explanation && <p>{r.root_cause_explanation}</p>}
      {ev?.overall_change && (
        <p className="muted small">
          {ev.metric}: {fmt(ev.overall_change.value_a)} → {fmt(ev.overall_change.value_b)}
          {' '}({ev.overall_change.pct_change.toFixed(1)}%) · {ev.period_a[0]} vs {ev.period_b[0]}
        </p>
      )}
      {cands.length > 0 && (
        <table>
          <thead>
            <tr><th>Segment</th><th className="num">Before</th><th className="num">After</th><th className="num">Change</th><th>Share of change</th><th>Query</th></tr>
          </thead>
          <tbody>
            {cands.map((c) => (
              <tr key={`${c.dimension}-${c.segment}`}>
                <td>{c.dimension.replace(/_/g, ' ')} = <strong>{c.segment}</strong></td>
                <td className="num">{fmt(c.value_a)}</td>
                <td className="num">{fmt(c.value_b)}</td>
                <td className={`num ${c.change < 0 ? 'down' : 'up'}`}>{fmt(c.change)}</td>
                <td>
                  <div className="bar" aria-label={`${Math.round(c.share_of_change * 100)}%`}>
                    <span style={{ width: `${Math.min(100, Math.abs(c.share_of_change) * 100)}%` }} className={c.share_of_change < 0 ? 'neg' : ''} />
                  </div>
                  <span className="small">{Math.round(c.share_of_change * 100)}%</span>
                </td>
                <td>{c.query_id}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {r.next_checks && r.next_checks.length > 0 && (
        <>
          <h3>Next checks</h3>
          <ul>{r.next_checks.map((n) => <li key={n}>{n}</li>)}</ul>
        </>
      )}
      {queries.length > 0 && (
        <details>
          <summary>Audit trail: {queries.length} SQL queries, each validated before it ran</summary>
          {queries.map((q) => (
            <div key={q.query_id} className="query">
              <strong>{q.query_id}</strong> · {q.purpose} <span className="muted small">({q.row_count} rows, {q.duration_ms} ms)</span>
              <pre>{q.sql_executed}</pre>
            </div>
          ))}
        </details>
      )}
      {run.usage && (
        <p className="muted small">{run.usage.calls} LLM calls · ${run.usage.cost_usd.toFixed(4)} · {run.duration_s ?? run.usage.latency_s}s</p>
      )}
    </section>
  )
}
