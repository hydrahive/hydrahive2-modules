import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { ArrowLeft, Bell, Mail, PenSquare, Search } from "lucide-react"
import { useTranslation } from "react-i18next"
import { mailApi, type Account, type MailAction, type MailDetail, type MailItem, type SavedDraft } from "./api"
import { BulkBar } from "./BulkBar"
import { Composer } from "./Composer"
import { DraftList } from "./DraftList"
import { MessageActions } from "./MessageActions"
import { useComposeOpen } from "./useComposeOpen"
import { useMailKeys, useNewMailNotice } from "./useMailKeys"
import { useSelection } from "./useSelection"
import { AccountDialog } from "./AccountDialog"
import { AccountSettings } from "./AccountSettings"
import { FolderTree, type Selection } from "./FolderTree"
import { MessageList } from "./MessageList"
import { MessageView } from "./MessageView"
import { MsAppButton } from "./MsAppButton"
import { FILTER_HELP, type FolderRow } from "./mailFormat"

const PAGE = 50

/** Webmail mit drei Spalten (Spec §6). Schmal: jeweils eine Spalte. „Alle Posteingänge“ = Suche ordner-Rolle inbox. */
export function MailboxPage() {
  const { t } = useTranslation("mailbox")
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
  const [drafts, setDrafts] = useState<SavedDraft[]>([])
  const [settings, setSettings] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const loadMeta = useCallback(() => {
    mailApi.accounts().then(setAccounts).catch(() => setErr("Konten nicht ladbar"))
    mailApi.folders().then(setFolders).catch(() => {})
    mailApi.drafts().then(setDrafts).catch(() => {})
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
  const searchRef = useRef<HTMLInputElement>(null)
  const selTexts = useMemo(() => ({ done: (n: number) => t("bulk.done", { n }), skipped: (n: number) => t("action.skipped", { n }),
    failed: t("action.failed"), confirmDelete: (n: number) => t("bulk.confirmDelete", { n }) }), [t])
  const bulk = useSelection(items, JSON.stringify([sel, applied]), (m) => { setNotice(m); loadMeta(); void query(0) }, selTexts)
  const unread = folders.filter((f) => f.role === "inbox").reduce((n, f) => n + f.unread, 0)
  const notifyText = useCallback((n: number) => ({ title: t("notify.title"), body: t("notify.body", { n }) }), [t])
  useNewMailNotice(unread, notifyText)

  async function select(id: number) {
    setImages(false)
    try { setOpen(await mailApi.message(id)) } catch { setErr("Mail nicht ladbar") }
  }

  const cmp = useComposeOpen(accounts, () => setErr("Vorlage nicht ladbar"))

  // Nach einer Aktion: Liste/Ordner neu; bei Verschieben/Löschen Lesebereich schließen, sonst Mail neu laden
  async function keyAct(action: "archive" | "delete") {
    if (!open || open.deleted_on_server === 1) return
    if (action === "delete" && !window.confirm(t("bulk.confirmDelete", { n: 1 }))) return
    const r = await mailApi.act([open.id], action).catch(() => null)
    if (r?.done) void changed(action, action === "delete" ? t(open.folder_role === "trash" ? "action.deletedForever" : "action.movedToTrash") : null)
  }
  useMailKeys({ items, open, composing: Boolean(cmp.compose), select: (id) => void select(id), compose: cmp.openNew,
    reply: (m) => { if (open) void cmp.openReply(open, m) }, act: (a) => void keyAct(a), focusSearch: () => searchRef.current?.focus() })

  async function changed(action: MailAction, note: string | null) {
    setNotice(note)
    loadMeta()
    void query(0)
    if (!open) return
    if (action === "move" || action === "delete") setOpen(null)
    else setOpen(await mailApi.message(open.id).catch(() => open))
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
        <MsAppButton />
        {err && <p className="text-xs text-rose-300">{err}</p>}
      </div>
    )
  }

  return (
    <div className="flex h-full min-h-0 flex-col gap-2 p-3">
      <form className="flex items-center gap-2" onSubmit={(e) => { e.preventDefault(); setApplied(q.trim()) }} role="search">
        <Search size={16} className="text-[#8d9ab0]" />
        <input ref={searchRef} value={q} onChange={(e) => setQ(e.target.value)} placeholder="Suchen in allen Mails …" aria-label="Suche" list="mbx-filter"
          className="min-w-0 flex-1 rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-2 py-1.5 text-sm text-[#e8eef8]" />
        <datalist id="mbx-filter">{FILTER_HELP.map(([k, label]) => <option key={k} value={k}>{label}</option>)}</datalist>
        {!fulltext && <span className="text-[11px] text-amber-200" title="SQLite ohne FTS5">Suche nur in Betreff/Kopf</span>}
        <NotifyToggle />
        <MsAppButton />
        <button type="button" onClick={cmp.openNew} data-mbx-new="1" title={t("keys.help")}
          className="inline-flex items-center gap-1 rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff]">
          <PenSquare size={14} />{t("compose.new")}</button>
      </form>
      {err && <p className="text-xs text-rose-300" role="alert">{err}</p>}
      {notice && (
        <p role="status" data-mbx-notice="1" className="flex items-start gap-2 rounded-[4px] border border-amber-300/30 bg-amber-300/10 px-2 py-1 text-xs text-amber-100">
          <span className="flex-1">{notice}</span>
          <button type="button" onClick={() => setNotice(null)} aria-label="×" className="text-amber-200">×</button>
        </p>)}
      <div className="grid min-h-0 flex-1 grid-cols-1 gap-3 md:grid-cols-[14rem_22rem_1fr]">
        <div className={`min-h-0 ${open ? "hidden md:block" : ""}`}>
          <FolderTree accounts={accounts} folders={folders} selection={sel} onSelect={(s) => { setSel(s); setOpen(null) }}
            onAddAccount={() => setDialog(true)} onSync={(id) => void sync(id)} draftCount={drafts.length} onSettings={setSettings} />
        </div>
        <div className={`min-h-0 rounded-[4px] border border-[#2a364b] bg-[#0b1220] ${open ? "hidden md:block" : ""}`}>
          {sel.kind === "drafts" ? <DraftList drafts={drafts} onOpen={(d) => { setOpen(null); cmp.openDraft(d) }} /> :
          <div className="flex h-full min-h-0 flex-col">
            <BulkBar items={items} selected={bulk.checked} busy={bulk.busy} onAct={(a) => void bulk.act(a)} onClear={bulk.clear} />
            <div className="min-h-0 flex-1">
              <MessageList items={items} total={total} selected={open?.id ?? null} onSelect={(id) => void select(id)}
                onMore={() => void query(items.length)} showAccount={accounts.length > 1}
                checked={bulk.checked} onCheck={bulk.check} onCheckAll={bulk.checkAll} />
            </div>
          </div>}
        </div>
        <div className={`min-h-0 ${open || cmp.compose ? "" : "hidden md:block"}`}>
          {cmp.compose ? (
            <Composer key={cmp.compose.key} accounts={accounts} initial={cmp.compose.initial} draftId={cmp.compose.draftId}
              originalAttachments={cmp.compose.originalAttachments}
              onClose={(sent) => { cmp.close(); loadMeta(); if (sent) void query(0) }} />
          ) : open ? (
            <div className="flex h-full min-h-0 flex-col gap-2">
              <button type="button" onClick={() => setOpen(null)} className="inline-flex items-center gap-1 text-xs text-[#69d7ff] md:hidden"><ArrowLeft size={12} />Zurück</button>
              <MessageActions mail={open} folders={folders} onCompose={(mode) => void cmp.openReply(open, mode)}
                onChanged={(a, n) => void changed(a, n)} />
              <MessageView key={open.id} mail={open} images={images} onImages={() => setImages(true)} />
            </div>
          ) : <p className="p-6 text-center text-sm text-[#718097]">Mail auswählen</p>}
        </div>
      </div>
      {settings && accounts.find((a) => a.id === settings) && (
        <AccountSettings account={accounts.find((a) => a.id === settings)!} onClose={() => setSettings(null)}
          onSaved={() => { setSettings(null); loadMeta() }} />)}
      {dialog && <AccountDialog onClose={() => setDialog(false)} onSaved={() => { setDialog(false); loadMeta() }} />}
    </div>
  )
}

/** Browser-Benachrichtigung einschalten (Spec §6) – fragt die Erlaubnis erst auf Klick. */
function NotifyToggle() {
  const { t } = useTranslation("mailbox")
  const [on, setOn] = useState(() => localStorage.getItem("mailbox.notify") === "1")
  if (typeof Notification === "undefined") return null
  async function flip() {
    if (on) { localStorage.removeItem("mailbox.notify"); setOn(false); return }
    if ((await Notification.requestPermission()) === "granted") { localStorage.setItem("mailbox.notify", "1"); setOn(true) }
  }
  return (
    <button type="button" onClick={() => void flip()} title={t("notify.enable")} aria-label={t("notify.enable")} aria-pressed={on}
      data-mbx-notify={on ? "on" : "off"} className={`rounded-[4px] border px-2 py-1.5 ${on ? "border-[#69d7ff]/50 text-[#69d7ff]" : "border-[#2a364b] text-[#8d9ab0]"}`}>
      <Bell size={14} /></button>
  )
}
