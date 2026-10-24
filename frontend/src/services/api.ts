import type { Account, Card, Purchase, Transaction, User } from '../types/api'

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '')
export class ApiError extends Error {
  constructor(message: string, public status: number | null) { super(message) }
}
export function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Something went wrong. Please try again.'
}
export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response
  try {
    response = await fetch(baseUrl + path, {
      ...options, headers: { 'Content-Type': 'application/json', ...options.headers },
    })
  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') throw error
    throw new ApiError('Could not reach the API. Check that the backend is running, then retry.', null)
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = body?.detail
    const message = typeof detail === 'string' ? detail : Array.isArray(detail)
      ? detail.map((item: { loc?: (string | number)[]; msg?: string }) =>
        `${item.loc?.slice(1).join('.') || 'Request'}: ${item.msg || 'Invalid value'}`).join('; ')
      : `Request failed (${response.status}). Please try again.`
    throw new ApiError(message, response.status)
  }
  if (body === null) throw new ApiError('The API returned an unreadable response. Please refresh.', response.status)
  return body as T
}
const post = <T>(path: string, body: unknown) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })
const accountPath = (uid: number, aid: number) => `/users/${uid}/accounts/${aid}`
export const api = {
  users: (signal?: AbortSignal) => request<User[]>('/users', { signal }),
  accounts: (signal?: AbortSignal) => request<Account[]>('/accounts', { signal }),
  createUser: (name: string, email: string) => post<User>('/users', { name, email }),
  createAccount: (uid: number) => post<Account>(`/users/${uid}/accounts`, {}),
  cards: (uid: number, aid: number, signal?: AbortSignal) => request<Card[]>(accountPath(uid, aid) + '/cards', { signal }),
  history: (uid: number, aid: number, signal?: AbortSignal) => request<Transaction[]>(accountPath(uid, aid) + '/transactions?limit=5', { signal }),
  issueCard: (uid: number, aid: number, name: string) => post<Card>(accountPath(uid, aid) + '/cards', { cardholder_name: name }),
  deactivateCard: (uid: number, aid: number, cid: number) => post<Card>(accountPath(uid, aid) + `/cards/${cid}/deactivate`, {}),
  deposit: (uid: number, aid: number, amount_cents: number, key: string) => request<Transaction>(accountPath(uid, aid) + '/deposits', {
    method: 'POST', body: JSON.stringify({ amount_cents }), headers: { 'Idempotency-Key': key },
  }),
  purchase: (uid: number, aid: number, body: Purchase, key: string) => request<Transaction>(accountPath(uid, aid) + '/purchases', {
    method: 'POST', body: JSON.stringify(body), headers: { 'Idempotency-Key': key },
  }),
}
