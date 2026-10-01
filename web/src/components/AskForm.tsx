import { useState } from 'react'

const EXAMPLES = [
  'Why did the number of orders drop in April 2018 compared to March 2018?',
  'Why did revenue fall in May 2018 compared to April 2018?',
]

interface Props {
  datasets: Record<string, string>
  busy: boolean
  onAsk: (question: string, dataset: string) => void
}

export function AskForm({ datasets, busy, onAsk }: Props) {
  const keys = Object.keys(datasets)
  const [dataset, setDataset] = useState(keys.includes('olist_lab') ? 'olist_lab' : keys[0] ?? 'olist')
  const [question, setQuestion] = useState('')
  const ready = question.trim().length >= 3 && !busy

  return (
    <form className="card ask" onSubmit={(e) => { e.preventDefault(); if (ready) onAsk(question.trim(), dataset) }}>
      <label>
        Question
        <textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2}
          placeholder="Why did a metric change between two periods?" />
      </label>
      <div className="row">
        <label>
          Dataset
          <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
            {keys.map((k) => <option key={k} value={k}>{datasets[k]}</option>)}
          </select>
        </label>
        <button type="submit" disabled={!ready}>{busy ? 'Analysing…' : 'Find the root cause'}</button>
      </div>
      <div className="examples">
        {EXAMPLES.map((q) => (
          <button type="button" key={q} className="chip" onClick={() => setQuestion(q)}>{q}</button>
        ))}
      </div>
    </form>
  )
}
