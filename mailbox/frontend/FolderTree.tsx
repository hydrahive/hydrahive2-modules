import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Archive, ChevronDown, ChevronRight, FileText, Inbox, Plus, RefreshCw, Settings } from "lucide-react"
import type { Account } from "./api"
import { loadExpandedAccounts, saveExpandedAccounts, toggleExpandedAccount } from "./folderCollapse"
import { accountState, folderLabel, groupFolders, syncText, type FolderRow } from "./mailFormat"

export type Selection = { kind: "all" } | { kind: "folder"; id: number } | { kind: "archive" } | { kind: "drafts" }

interface Props {
  accounts: Account[]
  folders: FolderRow[]
  selection: Selection
  onSelect: (s: Selection) => void
  onAddAccount: () => void
  onSync: (id: string) => void
  draftCount?: number
  onSettings?: (id: string) => void
}

const TONE = { ok: "bg-emerald-400", warn: "bg-amber-300", err: "bg-rose-400" }

/** Linke Spalte: alle Posteingänge, Konten mit Ordnern, „nur im Archiv“. */
export function FolderTree({ accounts, folders, selection, onSelect, onAddAccount, onSync, draftCount = 0, onSettings }: Props) {
  const { t } = useTranslation("mailbox")
  const [expanded, setExpanded] = useState(loadExpandedAccounts)
  const groups = groupFolders(folders.filter((f) => f.gone === 0))
  const unreadInbox = folders.filter((f) => f.role === "inbox").reduce((n, f) => n + f.unread, 0)
  const item = (active: boolean) =>
    `flex w-full items-center gap-2 rounded-[4px] px-2 py-1 text-left text-sm ${active ? "bg-[#1d3a52] text-[#e8eef8]" : "text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,21_28_43))]"}`
  const toggle = (accountId: string) => setExpanded((current) => {
    const next = toggleExpandedAccount(current, accountId)
    saveExpandedAccounts(next)
    return next
  })
  return (
    <nav className="flex h-full min-h-0 flex-col gap-2 overflow-y-auto pr-1" aria-label="Ordner">
      <button type="button" className={item(selection.kind === "all")} onClick={() => onSelect({ kind: "all" })} data-mbx-all="1">
        <Inbox size={14} /><span className="flex-1">Alle Posteingänge</span>
        {unreadInbox > 0 && <span className="text-xs font-bold text-[#69d7ff]">{unreadInbox}</span>}
      </button>
      {groups.map((g) => {
        const acc = accounts.find((a) => a.id === g.accountId)
        const st = accountState(acc?.status ?? "new")
        const open = expanded.has(g.accountId)
        const label = acc?.label ?? g.account
        const controls = `mailbox-folders-${g.accountId}`
        return (
          <section key={g.accountId} className="space-y-0.5">
            <div className="flex items-center gap-1 px-1 pt-2 text-[11px] uppercase tracking-wide text-[#9aa7bc]">
              <button type="button" onClick={() => toggle(g.accountId)} aria-expanded={open} aria-controls={controls}
                aria-label={t(open ? "folders.collapse" : "folders.expand", { account: label })} data-mbx-account-toggle={g.accountId}
                className="flex min-w-0 flex-1 items-center gap-1 rounded px-1 py-0.5 text-left hover:bg-[rgb(var(--hh-s-hebung,28_38_56))]">
                {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                <span className={`h-2 w-2 shrink-0 rounded-full ${TONE[st.tone]}`} title={st.text} />
                <span className="min-w-0 flex-1 truncate">{label}</span>
              </button>
              <button type="button" onClick={() => onSync(g.accountId)} title={t("folders.sync")} aria-label={t("folders.sync")}
                className="rounded p-0.5 hover:bg-[rgb(var(--hh-s-hebung,28_38_56))]"><RefreshCw size={11} className={acc?.sync?.running ? "animate-spin" : ""} /></button>
              {onSettings && <button type="button" onClick={() => onSettings(g.accountId)} title={t("settings.open")} aria-label={t("settings.open")}
                data-mbx-settings-open={g.accountId} className="rounded p-0.5 hover:bg-[rgb(var(--hh-s-hebung,28_38_56))]"><Settings size={11} /></button>}
            </div>
            {syncText(acc?.sync) && <p className="px-2 text-[11px] text-[#69d7ff]" data-mbx-sync="1">{syncText(acc?.sync)}</p>}
            {acc && acc.status !== "ok" && acc.status_detail && (
              <p className="px-2 text-[11px] text-rose-300" data-mbx-status="1">{acc.status_detail}</p>)}
            <div id={controls} hidden={!open} className="space-y-0.5">
              {open && g.folders.map((f) => (
                <button key={f.id} type="button" data-mbx-folder={f.id}
                  className={item(selection.kind === "folder" && selection.id === f.id)}
                  onClick={() => onSelect({ kind: "folder", id: f.id })}>
                  <span className="min-w-0 flex-1 truncate">{folderLabel(f)}</span>
                  {f.unread > 0 && <span className="text-xs font-bold text-[#69d7ff]">{f.unread}</span>}
                </button>
              ))}
            </div>
          </section>
        )
      })}
      <button type="button" className={item(selection.kind === "drafts")} onClick={() => onSelect({ kind: "drafts" })} data-mbx-drafts="1">
        <FileText size={14} /><span className="flex-1">Entwürfe</span>
        {draftCount > 0 && <span className="text-xs text-[#9aa7bc]">{draftCount}</span>}
      </button>
      <button type="button" className={item(selection.kind === "archive")} onClick={() => onSelect({ kind: "archive" })} data-mbx-archive="1">
        <Archive size={14} /><span className="flex-1">Nur im Archiv</span>
      </button>
      <button type="button" onClick={onAddAccount} data-mbx-add="1"
        className="mt-auto flex items-center gap-2 rounded-[4px] border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-1.5 text-sm text-[#69d7ff] hover:bg-[rgb(var(--hh-s-hebung,21_28_43))]">
        <Plus size={14} />Konto hinzufügen</button>
    </nav>
  )
}
