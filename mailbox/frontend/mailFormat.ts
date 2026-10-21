/** Reine Anzeige-Logik der Mailbox (testbar ohne DOM). */

export interface FolderRow {
  id: number
  account_id: string
  account: string
  name: string
  role: string
  total: number
  unread: number
  gone: number
}

const ROLE_ORDER = ["inbox", "drafts", "sent", "archive", "all", "junk", "trash", ""]
const ROLE_LABEL: Record<string, string> = {
  inbox: "Posteingang", drafts: "Entwürfe", sent: "Gesendet", archive: "Archiv", all: "Alle Nachrichten",
  junk: "Spam", trash: "Papierkorb",
}

export function folderLabel(f: Pick<FolderRow, "name" | "role">): string {
  return ROLE_LABEL[f.role] ?? f.name
}

/** Ordner je Konto gruppiert; Rollen zuerst (Posteingang oben), dann alphabetisch. */
export function groupFolders(rows: FolderRow[]): { account: string; accountId: string; folders: FolderRow[] }[] {
  const by = new Map<string, FolderRow[]>()
  for (const r of rows) by.set(r.account_id, [...(by.get(r.account_id) ?? []), r])
  return [...by.entries()].map(([accountId, fs]) => ({
    accountId,
    account: fs[0].account,
    folders: [...fs].sort((a, b) => {
      const ra = ROLE_ORDER.indexOf(a.role), rb = ROLE_ORDER.indexOf(b.role)
      return ra !== rb ? ra - rb : a.name.localeCompare(b.name, "de")
    }),
  })).sort((a, b) => a.account.localeCompare(b.account, "de"))
}

/** „09:15“ heute, „Mo. 19.10.“ in den letzten 6 Tagen, sonst „05.01.2015“. */
export function shortDate(iso: string, now: Date = new Date()): string {
  if (!iso) return ""
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ""
  const sameDay = d.toDateString() === now.toDateString()
  if (sameDay) return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" })
  const days = (now.getTime() - d.getTime()) / 86_400_000
  if (days >= 0 && days < 6) return d.toLocaleDateString("de-DE", { weekday: "short", day: "2-digit", month: "2-digit" })
  return d.toLocaleDateString("de-DE", { day: "2-digit", month: "2-digit", year: "numeric" })
}

export function fullDate(iso: string): string {
  if (!iso) return "unbekanntes Datum"
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? "unbekanntes Datum" : d.toLocaleString("de-DE", { dateStyle: "full", timeStyle: "short" })
}

/** „Anna Beispiel <anna@x>“ → „Anna Beispiel“; nur Adresse → Adresse; leer → „(ohne Absender)“. */
export function senderName(from: string): string {
  const m = /^\s*"?([^"<]*?)"?\s*<([^>]+)>\s*$/.exec(from ?? "")
  if (m) return m[1].trim() || m[2].trim()
  return (from ?? "").trim() || "(ohne Absender)"
}

export function size(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1).replace(".", ",")} MB`
}

export const FILTER_HELP: [string, string][] = [
  ["von:anna", "Absender"], ["an:till", "Empfänger"], ["betreff:rechnung", "im Betreff"],
  ["hat:anhang", "mit Anhang"], ["vor:2020-01-01", "älter als"], ["nach:2024-06-01", "ab Datum"],
  ["ordner:Archiv", "in Ordner"], ["konto:gmail", "in Konto"], ['"genaue Wörter"', "als Phrase"],
]

/** Status eines Kontos → kurzer Text + Ton. */
export function accountState(status: string): { text: string; tone: "ok" | "warn" | "err" } {
  if (status === "ok") return { text: "verbunden", tone: "ok" }
  if (status === "auth_failed") return { text: "Anmeldung fehlgeschlagen", tone: "err" }
  if (status === "error") return { text: "Fehler beim Abgleich", tone: "err" }
  return { text: "noch nicht abgeglichen", tone: "warn" }
}

/** Fortschritt des Abgleichs für die Ordnerleiste; leer, wenn nichts läuft. */
export function syncText(sync?: { running: number; messages_done: number; folders_done: number; folders_total: number }): string {
  if (!sync || !sync.running) return ""
  const n = sync.messages_done.toLocaleString("de-DE")
  return sync.folders_total ? `lädt … ${n} Mails · Ordner ${Math.min(sync.folders_done + 1, sync.folders_total)}/${sync.folders_total}` : `lädt … ${n} Mails`
}
