import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorMessage } from '../services/api'
import type { Account, User } from '../types/api'

export default function AccountSelector({ onSelect }: { onSelect: (user: User | null, account: Account | null) => void }) {
  const [users, setUsers] = useState<User[]>([])
  const [accounts, setAccounts] = useState<Account[]>([])
  const [uid, setUid] = useState('')
  const [aid, setAid] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [reload, setReload] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError('')
    Promise.all([api.users(controller.signal), api.accounts(controller.signal)])
      .then(([u, a]) => { setUsers(u); setAccounts(a) })
      .catch(e => { if (!controller.signal.aborted) setError(errorMessage(e)) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [reload])
  async function createUser(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError('')
    try {
      const user = await api.createUser(name.trim(), email.trim())
      setUsers(previous => [...previous, user]); setUid(String(user.id)); setAid('')
      onSelect(user, null); setName(''); setEmail('')
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  async function createAccount() {
    setBusy(true); setError('')
    try {
      const account = await api.createAccount(Number(uid))
      setAccounts(previous => [...previous, account]); setAid(String(account.id))
      onSelect(users.find(u => u.id === Number(uid))!, account)
    } catch (e) { setError(errorMessage(e)) } finally { setBusy(false) }
  }
  return <section className="panel selection" aria-label="User and account selection">
    <div className="section-heading"><div><span className="eyebrow">YOUR WORKSPACE</span><h2>Manage your workspace</h2></div><span className="badge">Simulated users · No sign-in</span></div>
    {loading ? <p role="status">Loading users and accounts…</p> : <>
      {error && <p className="error" role="alert">{error} <button type="button" disabled={busy} onClick={() => setReload(r => r + 1)}>Retry loading</button></p>}
      <label>User<select value={uid} disabled={busy} onChange={e => {
        setUid(e.target.value); setAid(''); onSelect(users.find(u => u.id === Number(e.target.value)) ?? null, null)
      }}><option value="">Choose a user</option>{users.map(u => <option key={u.id} value={u.id}>{u.name} · {u.email}</option>)}</select></label>
      <div className="mt-5 grid gap-5 md:grid-cols-2">
      <section className="rounded-xl border border-slate-200 p-5" aria-labelledby="choose-account-heading">
      <h3 id="choose-account-heading">Choose an existing account</h3>
      <p className="muted">Open the dashboard for one of this user’s accounts.</p>
      <label>Existing account<select value={aid} disabled={!uid || busy} onChange={e => {
        setAid(e.target.value); onSelect(users.find(u => u.id === Number(uid))!, accounts.find(a => a.id === Number(e.target.value)) ?? null)
      }}><option value="">Choose an account</option>{accounts.filter(a => a.user_id === Number(uid)).map(a => <option key={a.id} value={a.id}>HSA account #{a.id}</option>)}</select></label>
      {uid && !accounts.some(a => a.user_id === Number(uid)) && <p className="muted">This user has no existing accounts.</p>}
      </section>
      <section className="rounded-xl border border-slate-200 p-5" aria-labelledby="create-account-heading">
      <h3 id="create-account-heading">Create a new account</h3>
      <p className="muted">{uid ? `Create a new HSA account for ${users.find(u => u.id === Number(uid))?.name}. No existing account selection is needed.` : 'Choose or create a user above to create their HSA account.'}</p>
      <button type="button" disabled={!uid || busy} onClick={createAccount}>{busy ? 'Working…' : 'Create new account'}</button>
      </section>
      </div>
      <details><summary>{users.length ? 'Create another user' : 'Create your first user'}</summary><form className="selector-grid" onSubmit={createUser}>
        <label>Name<input required value={name} onChange={e => setName(e.target.value)} disabled={busy} /></label>
        <label>Email<input required type="email" value={email} onChange={e => setEmail(e.target.value)} disabled={busy} /></label>
        <button disabled={busy || !name.trim()} type="submit">Create user</button>
      </form></details>
    </>}
  </section>
}
