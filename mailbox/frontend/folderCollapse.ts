export const EXPANDED_ACCOUNTS_KEY = "mailbox.expandedAccounts.v1"

type ReadStore = Pick<Storage, "getItem">
type WriteStore = Pick<Storage, "setItem">

/** Fehlender/defekter Speicher bedeutet bewusst: alle Konten eingeklappt. */
export function loadExpandedAccounts(store?: ReadStore): Set<string> {
  try {
    const source = store ?? globalThis.localStorage
    const value = JSON.parse(source?.getItem(EXPANDED_ACCOUNTS_KEY) ?? "[]") as unknown
    if (!Array.isArray(value)) return new Set()
    return new Set(value.filter((id): id is string => typeof id === "string"))
  } catch {
    return new Set()
  }
}

export function saveExpandedAccounts(ids: Set<string>, store?: WriteStore): void {
  try {
    const target = store ?? globalThis.localStorage
    target?.setItem(EXPANDED_ACCOUNTS_KEY, JSON.stringify([...ids].sort()))
  } catch {
    // Die Bedienung funktioniert weiter; nur das Merken ist dann nicht verfügbar.
  }
}

export function toggleExpandedAccount(ids: Set<string>, accountId: string): Set<string> {
  const next = new Set(ids)
  if (next.has(accountId)) next.delete(accountId)
  else next.add(accountId)
  return next
}
