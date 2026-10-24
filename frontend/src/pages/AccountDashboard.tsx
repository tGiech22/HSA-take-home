import { useEffect, useState } from 'react'
import type { Dispatch, ReactNode, SetStateAction } from 'react'
import type { Account, Card, Transaction, User } from '../types/api'
import { api, errorMessage } from '../services/api'
import { formatMoney } from '../utils/money'
import VirtualCard from '../components/VirtualCard'
import PurchaseForm from '../components/PurchaseForm'
import RecentTransactions from '../components/RecentTransactions'

type Resource<T> = { data: T | null; loading: boolean; error: string }
const initial = <T,>(): Resource<T> => ({ data: null, loading: true, error: '' })
function Content<T>({ state, retry, children }: { state: Resource<T>; retry: () => void; children: (data: T) => ReactNode }) {
  if (state.loading) return <p className="loading" role="status">Loading…</p>
  if (state.error) return <div role="alert"><p className="error">{state.error}</p><button className="secondary" onClick={retry}>Retry</button></div>
  return state.data !== null ? children(state.data) : null
}
export default function AccountDashboard({ user, account, onDeposit }: { user: User; account: Account; onDeposit: () => void }) {
  const [balance, setBalance] = useState<Resource<Account>>(initial)
  const [cards, setCards] = useState<Resource<Card[]>>(initial)
  const [history, setHistory] = useState<Resource<Transaction[]>>(initial)
  const [revision, setRevision] = useState(0)
  const refresh = () => setRevision(r => r + 1)
  useEffect(() => {
    const controller = new AbortController()
    function load<T>(fetcher: () => Promise<T>, setter: Dispatch<SetStateAction<Resource<T>>>) {
      setter(previous => ({ ...previous, loading: true, error: '' }))
      fetcher().then(data => { if (!controller.signal.aborted) setter({ data, loading: false, error: '' }) })
        .catch(e => { if (!controller.signal.aborted) setter(previous => ({ ...previous, loading: false, error: errorMessage(e) })) })
    }
    load(async () => {
      const accounts = await api.accounts(controller.signal)
      const found = accounts.find(a => a.id === account.id && a.user_id === user.id)
      if (!found) throw new Error('This account is no longer available.')
      return found
    }, setBalance)
    load(() => api.cards(user.id, account.id, controller.signal), setCards)
    load(() => api.history(user.id, account.id, controller.signal), setHistory)
    return () => controller.abort()
  }, [user.id, account.id, revision])
  return <>
    <div className="section-heading dashboard-heading"><div><span className="eyebrow">ACCOUNT #{account.id}</span><h2>{user.name}’s overview</h2></div><button className="secondary" onClick={refresh}>Refresh data</button></div>
    <div className="dashboard-grid"><section className="panel balance-panel"><span className="eyebrow">AVAILABLE BALANCE</span><Content state={balance} retry={refresh}>{a => <p className="balance">{formatMoney(a.balance_cents)}</p>}</Content><p className="muted">USD · Health savings account</p><button type="button" onClick={onDeposit}>Deposit funds</button><div className="balance-note">Add simulated funds to your selected account.</div></section>
    <section className="panel"><div className="section-heading"><h2>Your virtual card</h2><span className="badge">Simulation</span></div><Content state={cards} retry={refresh}>{list => <VirtualCard uid={user.id} aid={account.id} name={user.name} cards={list} onRefresh={refresh} />}</Content></section>
    <section className="panel purchase-panel"><div className="section-heading"><h2>Simulate a purchase</h2><span className="eyebrow">TEST & EXPLORE</span></div>
      {cards.data !== null ? <PurchaseForm uid={user.id} aid={account.id} cards={cards.data} onRefresh={refresh} /> : <p className="muted">{cards.error ? 'Load cards successfully to simulate purchases.' : 'Loading cards…'}</p>}
    </section>
    <section className="panel history-panel"><div className="section-heading"><div><h2>Recent transactions</h2><p className="muted">Your five latest deposits and purchase attempts.</p></div></div><Content state={history} retry={refresh}>{list => <RecentTransactions transactions={list} />}</Content></section></div>
  </>
}
