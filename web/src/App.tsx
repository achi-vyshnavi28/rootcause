import { useCallback, useEffect, useState } from 'react'
import { api, type AuditCheck, type Query, type Run, type RunRow } from './api'
import { AskForm } from './components/AskForm'
import { RunReport } from './components/RunReport'
import './App.css'

export default function App() {
  const [datasets, setDatasets] = useState<Record<string, string>>({})
  const [runs, setRuns] = useState<RunRow[]>([])
  const [audit, setAudit] = useState<AuditCheck | null>(null)
  const [run, setRun] = useState<Run | null>(null)
  const [queries, setQueries] = useState<Query[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const [d, r, a] = await Promise.all([api.datasets(), api.runs(), api.verify()])
      setDatasets(d)
      setRuns(r)
      setAudit(a)
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not reach the API')
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function show(id: string) {
    try {
      const [r, q] = await Promise.all([api.run(id), api.audit(id)])
      setRun(r)
      setQueries(q)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load the run')
    }
  }

  async function ask(question: string, dataset: string) {
    setBusy(true)
    setError(null)
    try {
      const r = await api.ask(question, dataset)
      setRun(r)
      setQueries(r.run_id ? await api.audit(r.run_id) : [])
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'The analysis failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <main>
      <header>
        <div>
          <h1>RootCause</h1>
          <p className="muted">AI analyst that finds why a metric changed · every SQL query validated · tamper-evident audit log</p>
        </div>
        {audit && (
          <span className={`badge ${audit.intact ? 'ok' : 'bad'}`}>
            Audit log {audit.intact ? 'intact' : 'BROKEN'} · {audit.entries} entries
          </span>
        )}
      </header>
      {error && <p role="alert" className="error">{error}</p>}
      <div className="layout">
        <div>
          <AskForm datasets={datasets} busy={busy} onAsk={(q, d) => void ask(q, d)} />
          <section className="card" aria-label="Recent runs">
            <h2>Recent runs</h2>
            <ul className="runs">
              {runs.map((r) => (
                <li key={r.run_id}>
                  <button className="row-btn" onClick={() => void show(r.run_id)}>
                    {r.question}
                    <span className="muted small"> · {r.dataset} · {r.status}</span>
                  </button>
                </li>
              ))}
            </ul>
          </section>
        </div>
        {run ? <RunReport run={run} queries={queries} /> : <section className="card muted">Ask a question or open a recent run.</section>}
      </div>
    </main>
  )
}
