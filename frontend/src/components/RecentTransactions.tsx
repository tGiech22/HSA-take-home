import { categories } from '../types/api'
import type { Transaction } from '../types/api'
import { formatMoney } from '../utils/money'
export default function RecentTransactions({ transactions }: { transactions: Transaction[] }) {
  if (!transactions.length) return <div className="empty"><h3>No transactions yet</h3><p>Deposits and purchase attempts will appear here.</p></div>
  return <div className="table-scroll"><table><thead><tr><th>Transaction</th><th>Date</th><th>Status</th><th className="amount">Amount</th></tr></thead><tbody>{transactions.map(t => <tr key={t.id}>
    <td><strong>{t.type === 'DEPOSIT' ? 'Deposit' : t.category ? categories[t.category] : 'Purchase'}</strong><small>Transaction #{t.id}{t.decline_reason ? ` · ${t.decline_reason.toLowerCase().replaceAll('_', ' ')}` : ''}</small></td>
    <td>{new Date(t.created_at).toLocaleString()}</td><td><span className={`badge ${t.status === 'APPROVED' ? 'approved' : 'declined'}`}>{t.status === 'APPROVED' ? 'Approved' : 'Declined'}</span></td>
    <td className="amount"><strong>{formatMoney(t.amount_cents)}</strong><small>{t.status === 'DECLINED' ? '$0.00 balance change' : `${t.type === 'DEPOSIT' ? '+' : '−'}${formatMoney(Math.abs(t.balance_change_cents))}`}</small></td>
  </tr>)}</tbody></table></div>
}
