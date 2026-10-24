import { useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { ApiError, api, errorMessage } from '../services/api'
import { categories } from '../types/api'
import type { Card, Category, Purchase, Transaction } from '../types/api'
import { formatMoney, parseDollars } from '../utils/money'
import { isExpired } from './VirtualCard'
export default function PurchaseForm({ uid, aid, cards, onRefresh }: { uid: number; aid: number; cards: Card[]; onRefresh: () => void }) {
  const [amount, setAmount] = useState('')
  const [cid, setCid] = useState('')
  const [category, setCategory] = useState<Category>('PHARMACY')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState<Transaction | null>(null)
  const pending = useRef<{ body: Purchase; key: string } | null>(null)
  const [retry, setRetry] = useState(false)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (busy) return
    setError(''); setResult(null)
    try {
      if (!pending.current) {
        if (!cards.some(c => c.id === Number(cid))) throw new Error('Select a card.')
        pending.current = { body: { amount_cents: parseDollars(amount), card_id: Number(cid), category }, key: crypto.randomUUID() }
      }
      setBusy(true)
      const transaction = await api.purchase(uid, aid, pending.current.body, pending.current.key)
      pending.current = null; setRetry(false); setResult(transaction); setAmount(''); onRefresh()
    } catch (e) {
      // Unknown outcomes retain their original body and key until resolved by retry.
      if (pending.current && (!(e instanceof ApiError) || e.status === null || e.status >= 500 || e.status === 200 || e.status === 201)) setRetry(true)
      else { pending.current = null; setRetry(false) }
      setError(errorMessage(e))
    } finally { setBusy(false) }
  }
  return <form onSubmit={submit}>
    <p className="muted">Try a qualified expense or test a decline. These purchases are simulated.</p>
    <fieldset disabled={busy || retry || cards.length === 0}>
      <label>Card<select required value={cid} onChange={e => setCid(e.target.value)}><option value="">Choose a card</option>{cards.map(c => <option key={c.id} value={c.id}>•••• {c.last_four} · #{c.id} · {isExpired(c) ? 'Expired' : c.status.toLowerCase()}</option>)}</select></label>
      <div className="form-grid"><label>Amount (USD)<input required inputMode="decimal" placeholder="0.00" value={amount} onChange={e => setAmount(e.target.value)} /></label>
      <label>Expense category<select value={category} onChange={e => setCategory(e.target.value as Category)}>{Object.entries(categories).map(([value, label]) => <option value={value} key={value}>{label}{['RESTAURANT', 'MOVIES', 'ELECTRONICS'].includes(value) ? ' (not qualified)' : ''}</option>)}</select></label></div>
    </fieldset>
    {!cards.length && <p className="muted">Issue a card before simulating a purchase.</p>}
    <button disabled={busy || !cards.length} type="submit">{busy ? 'Processing…' : retry ? 'Retry same purchase' : 'Simulate purchase'}</button>
    {retry && <p className="muted">The outcome is unknown. Retry the same purchase to retrieve its result without charging twice.</p>}
    {error && <p className="error" role="alert">{error}</p>}
    {result && <div className={result.status === 'APPROVED' ? 'success result' : 'result'} role="status"><strong>{result.status === 'APPROVED' ? 'Purchase approved' : 'Purchase declined'}</strong><p>{formatMoney(result.amount_cents)}{result.decline_reason ? ` · ${result.decline_reason.toLowerCase().replaceAll('_', ' ')}. Balance unchanged.` : ' · Your account has been updated.'}</p></div>}
  </form>
}
