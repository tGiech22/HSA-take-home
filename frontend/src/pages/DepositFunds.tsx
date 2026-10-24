import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api, errorMessage } from '../services/api'
import type { Account, Transaction, User } from '../types/api'
import { formatMoney, parseDollars } from '../utils/money'

export default function DepositFunds({ user, account, onBack, onSubmitting }: {
  user: User; account: Account; onBack: () => void; onSubmitting: (busy: boolean) => void
}) {
  const [amount, setAmount] = useState('')
  const [busy, setBusy] = useState(false)
  const submitting = useRef(false)
  const [validation, setValidation] = useState('')
  const [error, setError] = useState('')
  const [unknown, setUnknown] = useState(false)
  const [result, setResult] = useState<Transaction | null>(null)

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (submitting.current || result || unknown) return
    setValidation(''); setError('')
    let cents: number
    try { cents = parseDollars(amount) } catch (e) { setValidation(errorMessage(e)); return }
    submitting.current = true; setBusy(true); onSubmitting(true)
    try {
      const transaction = await api.deposit(user.id, account.id, cents, crypto.randomUUID())
      setResult(transaction)
    } catch (e) {
      if (e instanceof ApiError && e.status !== null && e.status >= 400 && e.status < 500) {
        setError(e.message)
      } else {
        setUnknown(true)
        setError('We could not confirm the deposit outcome. It may already have been saved. Check your account before making another deposit.')
      }
    } finally {
      submitting.current = false; setBusy(false); onSubmitting(false)
    }
  }

  return <section className="panel mt-6" aria-labelledby="deposit-heading">
    <div className="section-heading"><div><span className="eyebrow">ACCOUNT #{account.id}</span><h2 id="deposit-heading">Deposit funds</h2></div>
      <button type="button" className="secondary" disabled={busy} onClick={onBack}>Back to dashboard</button></div>
    <p>Add simulated USD funds to {user.name}’s HSA account #{account.id}.</p>
    <form onSubmit={submit} noValidate aria-busy={busy} className="max-w-xl">
      <label htmlFor="deposit-amount">Amount (USD)</label>
      <input id="deposit-amount" className="mt-2" inputMode="decimal" autoComplete="off" placeholder="0.00"
        value={amount} disabled={busy || !!result || unknown} aria-invalid={!!validation}
        aria-describedby={validation ? 'deposit-help deposit-validation' : 'deposit-help'}
        onChange={e => { setAmount(e.target.value); setValidation(''); setError('') }} />
      <p id="deposit-help" className="muted">Enter an amount greater than $0, with up to two decimal places. Maximum: $1 trillion.</p>
      {validation && <p id="deposit-validation" className="error" role="alert">{validation}</p>}
      <button type="submit" disabled={busy || !!result || unknown}>{busy ? 'Depositing…' : result ? 'Deposit complete' : 'Deposit funds'}</button>
      {busy && <p role="status">Saving your deposit…</p>}
      {error && <p className="error" role="alert">{error}</p>}
      {result && <div className="success result" role="status"><strong>Deposit successful</strong>
        <p>{formatMoney(result.amount_cents)} deposited to account #{account.id}. Transaction #{result.id}.</p>
        <p>Your deposit is saved and your account balance has been updated. Use “Refresh data” on the dashboard to load the latest balance and transactions.</p>
      </div>}
    </form>
  </section>
}
