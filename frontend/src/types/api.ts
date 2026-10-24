export interface User { id: number; name: string; email: string; created_at: string }
export interface Account { id: number; user_id: number; balance_cents: number; created_at: string }
export interface Card {
  id: number; account_id: number; last_four: string; expires_on: string;
  created_at: string; status: 'ACTIVE' | 'INACTIVE'; cardholder_name: string;
}
export const categories = {
  DOCTOR_VISIT: 'Doctor’s visit', PHARMACY: 'Pharmacy', HOSPITAL: 'Hospital',
  PRESCRIPTION: 'Prescription', DENTAL: 'Dental', VISION: 'Vision',
  OTC_MEDICINE: 'Over-the-counter medicine', PREVENTATIVE_CARE: 'Preventative care',
  RESTAURANT: 'Restaurant', MOVIES: 'Movies', ELECTRONICS: 'Electronics',
} as const
export type Category = keyof typeof categories
export interface Transaction {
  id: number; account_id: number; card_id: number | null; amount_cents: number;
  balance_change_cents: number; category: Category | null; created_at: string;
  type: 'DEPOSIT' | 'PURCHASE'; status: 'APPROVED' | 'DECLINED';
  decline_reason: 'INSUFFICIENT_FUNDS' | 'INVALID_EXPENSE' | 'INACTIVE_CARD' | 'EXPIRED_CARD' | null;
  idempotency_key: string;
}
export interface Purchase { card_id: number; amount_cents: number; category: Category }
