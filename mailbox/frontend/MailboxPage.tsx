import { useCallback, useEffect, useState } from "react"
import { ArrowLeft, Mail, Search } from "lucide-react"
import { mailApi, type Account, type MailDetail, type MailItem } from "./api"
import { AccountDialog } from "./AccountDialog"
import { FolderTree, type Selection } from "./FolderTree"
import { MessageList } from "./MessageList"
import { MessageView } from "./MessageView"
import { FILTER_HELP, type FolderRow } from "./mailFormat"

const PAGE = 50

/** Webmail mit drei Spalten (Spec §6). Schmal: jeweils eine Spalte. „Alle Posteingänge“ = Suche ordner-Rolle inbox. */
export function MailboxPage() {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [folders, setFolders] = useState<FolderRow[]>([])
  const [sel, setSel] = useState<Selection>({ kind: "all" })
  const [q, setQ] = useState("")
  const [applied, setApplied] = useState("")
  const [items, setItems] = useState<MailItem[]>([])
  const [total, setTotal] = useState(0)
  const [fulltext, setFulltext] = useState(true)
  const [open, setOpen] = useState<MailDetail | null>(null)
  const [images, setImages] = useState(false)
  const [dialog, setDialog] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const loadMeta = useCallback(() => {
    mailApi.accounts().then(setAccounts).catch(() => setErr("Konten nicht ladbar"))
    mailApi.folders().then(setFolders).catch(() => {})
  }, [])

  // „Alle Posteingänge“ ohne Suche = nur Posteingänge (Filter im Backend); mit Suche = alle Ordner aller Konten.
  const query = useCallback((offset: number) => mailApi.messages({
    q: applied, offset, limit: PAGE, inbox: sel.kind === "all" && !applied,
    folder_id: sel.kind === "folder" ? sel.id : null, deleted: sel.kind === "archive",
  }).then((r) => {
    setItems((old) => (offset ? [...old, ...r.items] : r.items)); setTotal(r.total); setFulltext(r.fulltext)
  }).catch(() => setErr("Mails nicht ladbar")), [sel, applied])

  // Solange ein Konto abgleicht, alle 10 s nachladen (Ordner + erste Seite); sonst alle 30 s nur Konten/Ordner.
  // Liste nur nachladen, solange man auf der ersten Seite ist (sonst springt „Weitere laden“ zurück).
  const busy = accounts.some((a) => a.sync?.running)
  const onFirstPage = items.length <= PAGE
  useEffect(() => {
    loadMeta()
    const id = window.setInterval(() => { loadMeta(); if (busy && onFirstPage) void query(0) }, busy ? 10_000 : 30_000)
    return () => window.clearInterval(id)
  }, [loadMeta, query, busy, onFirstPage])
  useEffect(() => { void query(0) }, [query])

  async function select(id: number) {
    setImages(false)
    try { setOpen(await mailApi.message(id)) } catch { setErr("Mail nicht ladbar") }
  }

  async function sync(id: string) {
    try { await mailApi.syncNow(id); loadMeta(); void query(0) } catch { setErr("Abruf fehlgeschlagen") }
  }

  if (accounts.length === 0 && !dialog) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 p-6 text-center">
        <Mail size={32} className="text-[#69d7ff]" />
        <h1 className="text-xl font-bold text-[#e8eef8]">Mailbox</h1>
        <p className="max-w-md text-sm text-[#8d9ab0]">Webmail für alle deine Konten. Jede Mail wird vollständig archiviert – auch wenn sie auf dem Server gelöscht wird.</p>
        <button type="button" onClick={() => setDialog(true)} data-mbx-first="1"
          className="rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-4 py-2 text-sm font-semibold text-[#69d7ff]">Erstes Konto hinzufügen</button>
        {err && <p className="text-xs text-rose-300">{err}</p>}
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-2 p-3">
      <form className="flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); setApplied(q.trim()) }} role="search">
        <Search size={16} className="text-[#8d9ab0]" />
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Suchen in allen Mails …" aria-label="Suche" list="mbx-filter"
          className="min-w-0 flex-1 rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-2 py-1.5 text-sm text-[#e8eef8]" />
        <datalist id="mbx-filter">{FILTER_HELP.map(([k, label]) => <option key={k} value={k}>{label}</option>)}</datalist>
        {!fulltext && <span className="text-[11px] text-amber-200" title="SQLite ohne FTS5">Suche nur in Betreff/Kopf</span>}
      </form>
      {err && <p className="text-xs text-rose-300" role="alert">{err}</p>}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 md:grid-cols-[14rem_22rem_1fr]">
        <div className={`min-h-0 ${open ? "hidden md:block" : ""}`}>
          <FolderTree accounts={accounts} folders={folders} selection={sel} onSelect={(s) => { setSel(s); setOpen(null) }}
            onAddAccount={() => setDialog(true)} onSync={(id) => void sync(id)} />
        </div>
        <div className={`min-h-0 rounded-[4px] border border-[#2a364b] bg-[#0b1220] ${open ? "hidden md:block" : ""}`}>
          <MessageList items={items} total={total} selected={open?.id ?? null} onSelect={(id) => void select(id)}
            onMore={() => void query(items.length)} showAccount={accounts.length > 1} />
        </div>
        <div className={`min-h-0 ${open ? "" : "hidden md:block"}`}>
          {open ? (
            <div className="flex h-full min-h-0 flex-col gap-2">
              <button type="button" onClick={() => setOpen(null)} className="inline-flex items-center gap-1 text-xs text-[#69d7ff] md:hidden"><ArrowLeft size={12} />Zurück</button>
              <MessageView key={open.id} mail={open} images={images} onImages={() => setImages(true)} />
            </div>
          ) : <p className="p-6 text-center text-sm text-[#718097]">Mail auswählen</p>}
        </div>
      </div>
      {dialog && <AccountDialog onClose={() => setDialog(false)} onSaved={() => { setDialog(false); loadMeta() }} />}
    </div>
  )
}
