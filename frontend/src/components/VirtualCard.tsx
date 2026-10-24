import { useState } from 'react'
import { api, errorMessage } from '../services/api'
import type { Card } from '../types/api'
export function isExpired(card: Card): boolean { return card.expires_on < new Date().toISOString().slice(0, 10) }
export default function VirtualCard({ uid, aid, name, cards, onRefresh }: {
  uid: number; aid: number; name: string; cards: Card[]; onRefresh: () => void
}) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const active = cards.find(c => c.status === 'ACTIVE' && !isExpired(c))
  const card = active ?? cards[0]
  async function act(deactivate: boolean) {
    setBusy(true); setError(''); setNotice('')
    try {
      if (deactivate && card) await api.deactivateCard(uid, aid, card.id)
      else await api.issueCard(uid, aid, name)
      setNotice(deactivate ? 'Card deactivated.' : 'Card issued.'); onRefresh()
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  return <>
    {card ? <div className="debit-card"><div className="section-heading"><strong>HSA / virtual debit</strong><span className="text-lg font-semibold">{isExpired(card) ? 'Expired' : card.status === 'ACTIVE' ? 'Active' : 'Inactive'}</span></div>
      <div className="chip" aria-hidden="true" /><p className="card-number">•••• &nbsp; •••• &nbsp; •••• &nbsp; {card.last_four}</p>
      <div className="section-heading"><span>{card.cardholder_name}</span><span>Expires {card.expires_on.slice(0, 7)}</span></div></div>
      : <div className="empty"><h3>No virtual card yet</h3><p>Issue a simulated card to try a purchase.</p></div>}
    <div className="card-actions">{!active && <button disabled={busy} onClick={() => act(false)}>Issue card</button>}
    {card?.status === 'ACTIVE' && <button className="secondary" disabled={busy} onClick={() => act(true)}>Deactivate card</button>}</div>
    {busy && <p role="status">Updating card…</p>}{error && <p role="alert" className="error">{error}</p>}{notice && <p role="status">{notice}</p>}
  </>
}
