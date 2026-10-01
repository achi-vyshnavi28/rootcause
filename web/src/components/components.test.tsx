import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import example from '../../../frontend/example_run.json'
import type { Run } from '../api'
import { AskForm } from './AskForm'
import { RunReport } from './RunReport'

describe('RunReport on a real saved run', () => {
  it('shows the summary, the ranked segments and the audit trail', async () => {
    const run = example as unknown as Run
    render(<RunReport run={{ ...run, cached: true }} queries={run.queries ?? []} />)
    expect(screen.getByText(/Total orders dropped by 731/)).toBeInTheDocument()
    expect(screen.getByText('MG')).toBeInTheDocument()
    expect(screen.getByText('63%')).toBeInTheDocument()
    expect(screen.getByText('from cache (DynamoDB)')).toBeInTheDocument()
    await userEvent.click(screen.getByText(/Audit trail/))
    expect(screen.getAllByText(/SELECT/).length).toBeGreaterThan(0)
  })
})

describe('AskForm', () => {
  it('needs a question, offers examples and sends the chosen dataset', async () => {
    const onAsk = vi.fn()
    render(<AskForm datasets={{ olist: 'Olist (original)', olist_lab: 'Olist lab' }} busy={false} onAsk={onAsk} />)
    const submit = screen.getByRole('button', { name: 'Find the root cause' })
    expect(submit).toBeDisabled()
    await userEvent.click(screen.getByRole('button', { name: /orders drop in April 2018/ }))
    await userEvent.click(submit)
    expect(onAsk).toHaveBeenCalledWith('Why did the number of orders drop in April 2018 compared to March 2018?', 'olist_lab')
  })
})
