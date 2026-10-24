export function parseDollars(value: string): number {
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(value.trim())
  if (!match) throw new Error('Enter a positive dollar amount with at most two decimal places.')
  const cents = BigInt(match[1]) * 100n + BigInt((match[2] ?? '').padEnd(2, '0'))
  if (cents <= 0n || cents > 100_000_000_000_000n) throw new Error('Amount must be greater than $0 and no more than $1 trillion.')
  return Number(cents)
}
export function formatMoney(cents: number): string {
  if (!Number.isSafeInteger(cents)) return 'Balance exceeds supported display precision'
  const amount = BigInt(cents)
  const absolute = amount < 0n ? -amount : amount
  return `${amount < 0n ? '-' : ''}$${(absolute / 100n).toLocaleString('en-US')}.${(absolute % 100n).toString().padStart(2, '0')}`
}
