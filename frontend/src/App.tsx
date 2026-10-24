import { useState } from 'react'
import AccountSelector from './components/AccountSelector'
import AccountDashboard from './pages/AccountDashboard'
import DepositFunds from './pages/DepositFunds'
import type { Account, User } from './types/api'
export default function App() {
  const [selection, setSelection] = useState<{ user: User | null; account: Account | null }>({ user: null, account: null })
  const [page, setPage] = useState<'dashboard' | 'deposit'>('dashboard')
  const [depositSubmitting, setDepositSubmitting] = useState(false)
  return <div className="app-shell"><header className="app-header"><a className="brand" href="#"><span className="brand-mark" aria-hidden="true">+</span>HSA<span className="brand-light">simulator</span></a><span className="header-note">A little clarity for your health savings.</span></header>
    <main><div className="page-title"><span className="eyebrow">YOUR HEALTH. YOUR SAVINGS.</span><h1>{page === 'deposit' ? 'Deposit funds' : 'Account dashboard'}</h1><p>{page === 'deposit' ? 'Add simulated funds to your health savings account.' : 'Explore your balance, manage your card, and see how HSA purchases work.'}</p></div>
      <fieldset disabled={depositSubmitting} className="m-0"><AccountSelector onSelect={(user, account) => { setSelection({ user, account }); setPage('dashboard') }} /></fieldset>
      {selection.user && selection.account ? <>
        <div hidden={page !== 'dashboard'}><AccountDashboard key={`${selection.user.id}:${selection.account.id}`} user={selection.user} account={selection.account} onDeposit={() => setPage('deposit')} /></div>
        {page === 'deposit' && <DepositFunds key={`${selection.user.id}:${selection.account.id}`} user={selection.user} account={selection.account} onBack={() => setPage('dashboard')} onSubmitting={setDepositSubmitting} />}
      </> : <section className="panel welcome"><span className="welcome-icon" aria-hidden="true">↗</span><h2>Your account starts here</h2><p>Select a user and account above, or create them to explore the simulator.</p></section>}
    </main><footer>HSA Simulator · For demonstration purposes · All amounts in USD</footer>
  </div>
}
