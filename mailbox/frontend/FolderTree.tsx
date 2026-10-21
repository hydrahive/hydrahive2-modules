import { Archive, Inbox, Plus, RefreshCw } from "lucide-react"
import type { Account } from "./api"
import { accountState, folderLabel, groupFolders, type FolderRow } from "./mailFormat"

export type Selection = { kind: "all" } | { kind: "folder"; id: number } | { kind: "archive" }

interface Props {
  accounts: Account[]
  folders: FolderRow[]
  selection: Selection
  onSelect: (s: Selection) => void
  onAddAccount: () => void
  onSync: (id: string) => void
}

const TONE = { ok: "bg-emerald-400", warn: "bg-amber-300", err: "bg-rose-400" }

/** Linke Spalte: alle Posteingänge, Konten mit Ordnern, „nur im Archiv“. */
export function FolderTree({ accounts, folders, selection, onSelect, onAddAccount, onSync }: Props) {
  const groups = groupFolders(folders.filter((f) => f.gone === 0))
  const unreadInbox = folders.filter((f) => f.role === "inbox").reduce((n, f) => n + f.unread, 0)
  const item = (active: boolean) =>
    `flex w-full items-center gap-2 rounded-[4px] px-2 py-1 text-left text-sm ${active ? "bg-[#1d3a52] text-[#e8eef8]" : "text-[#c8d2df] hover:bg-[#151c2b]"}`
  return (
    <nav className="flex h-full min-h-0 flex-col gap-2 overflow-y-auto pr-1" aria-label="Ordner">
      <button type="button" className={item(selection.kind === "all")} onClick={() => onSelect({ kind: "all" })} data-mbx-all="1">
        <Inbox size={14} /><span className="flex-1">Alle Posteingänge</span>
        {unreadInbox > 0 && <span className="text-xs font-bold text-[#69d7ff]">{unreadInbox}</span>}
      </button>
      {groups.map((g) => {
        const acc = accounts.find((a) => a.id === g.accountId)
        const st = accountState(acc?.status ?? "new")
        return (
          <section key={g.accountId} className="space-y-0.5">
            <div className="flex items-center gap-2 px-2 pt-2 text-[11px] uppercase tracking-wide text-[#8d9ab0]">
              <span className={`h-2 w-2 rounded-full ${TONE[st.tone]}`} title={st.text} />
              <span className="min-w-0 flex-1 truncate">{acc?.label ?? g.account}</span>
              <button type="button" onClick={() => onSync(g.accountId)} title="Jetzt abrufen" aria-label="Jetzt abrufen"
                className="rounded p-0.5 hover:bg-[#1c2638]"><RefreshCw size={11} /></button>
            </div>
            {g.folders.map((f) => (
              <button key={f.id} type="button" data-mbx-folder={f.id}
                className={item(selection.kind === "folder" && selection.id === f.id)}
                onClick={() => onSelect({ kind: "folder", id: f.id })}>
                <span className="min-w-0 flex-1 truncate">{folderLabel(f)}</span>
                {f.unread > 0 && <span className="text-xs font-bold text-[#69d7ff]">{f.unread}</span>}
              </button>
            ))}
          </section>
        )
      })}
      <button type="button" className={item(selection.kind === "archive")} onClick={() => onSelect({ kind: "archive" })} data-mbx-archive="1">
        <Archive size={14} /><span className="flex-1">Nur im Archiv</span>
      </button>
      <button type="button" onClick={onAddAccount} data-mbx-add="1"
        className="mt-auto flex items-center gap-2 rounded-[4px] border border-dashed border-[#2a364b] px-2 py-1.5 text-sm text-[#69d7ff] hover:bg-[#151c2b]">
        <Plus size={14} />Konto hinzufügen</button>
    </nav>
  )
}
