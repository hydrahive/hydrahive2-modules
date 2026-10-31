import { ListMusic, Shuffle } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import * as api from "./api"
import { ConfirmDialog } from "./ConfirmDialog"
import { MixEditor } from "./MixEditor"
import { PlaylistView } from "./PlaylistView"
import { compactRules, emptyRules, fullRules, programErrorKey, type PlaylistItem, type Preview, type Rules } from "./programLogic"
import { BTN, INPUT } from "./ui"
import { useProgramData } from "./useProgramData"

type Sel = { kind: "playlist" | "mix"; id: string } | { kind: "new-mix" } | null

/** Reiter „Programm“: links Playlisten und Mixe, rechts der gewählte Eintrag. */
export function ProgramPanel({ genres }: { genres: string[] }) {
  const { t } = useTranslation("radiostream")
  const { program, playlists, mixes, reload } = useProgramData()
  const [sel, setSel] = useState<Sel>(null)
  const [items, setItems] = useState<PlaylistItem[]>([])
  const [mix, setMix] = useState<{ name: string; rules: Rules; allowLong: boolean }>({ name: "", rules: emptyRules(), allowLong: false })
  const [preview, setPreview] = useState<Preview | null>(null)
  const [newName, setNewName] = useState("")
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [ask, setAsk] = useState(false)
  const can = !!program?.can_moderate
  const [folders, setFolders] = useState<string[]>([])
  useEffect(() => { api.getFolders().then((r) => setFolders(r.items.map((f) => f.folder))).catch(() => {}) }, [])

  const loadItems = useCallback((id: string) => api.getPlaylist(id).then((p) => setItems(p.items)).catch(() => setItems([])), [])
  useEffect(() => { if (sel?.kind === "playlist") loadItems(sel.id) }, [sel, loadItems])
  useEffect(() => {
    if (sel?.kind !== "mix" && sel?.kind !== "new-mix") return
    const h = setTimeout(() => api.previewMix(compactRules(mix.rules), mix.allowLong).then(setPreview).catch(() => setPreview(null)), 300)
    return () => clearTimeout(h)
  }, [sel, mix.rules, mix.allowLong])

  const run = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true); setMsg(null)
    try { await fn(); if (ok) setMsg({ ok: true, text: t(ok) }); reload(); if (sel?.kind === "playlist") loadItems(sel.id) }
    catch (e) { setMsg({ ok: false, text: t(programErrorKey(e)) }) } finally { setBusy(false) }
  }
  const pickMix = (id: string) => {
    const m = mixes.find((x) => x.id === id)
    if (m) { setMix({ name: m.name, rules: fullRules(m.rules), allowLong: m.allow_long }); setSel({ kind: "mix", id }) }
  }
  const pl = sel?.kind === "playlist" ? playlists.find((p) => p.id === sel.id) : undefined
  const entry = "flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm"
  return (
    <div className="grid gap-4 lg:grid-cols-[18rem_1fr]" data-radiostream-programtab>
      <aside className="space-y-3">
        {can && <div className="flex gap-2">
          <input className={INPUT} value={newName} maxLength={80} placeholder={t("program.new_playlist")} aria-label={t("program.new_playlist")} onChange={(e) => setNewName(e.target.value)} />
          <button type="button" className={BTN} disabled={busy || !newName.trim()} onClick={() => run(async () => { const p = await api.createPlaylist(newName.trim()); setNewName(""); setSel({ kind: "playlist", id: p.id }) })}>{t("program.create")}</button>
        </div>}
        <nav className="space-y-1">
          {playlists.map((p) => (
            <button key={p.id} type="button" data-dropzone={p.id} onClick={() => setSel({ kind: "playlist", id: p.id })}
              className={`${entry} ${sel?.kind === "playlist" && sel.id === p.id ? "bg-[rgb(var(--hh-s-hebung,27_37_54))] text-[#e8eef8]" : "text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"}`}>
              <ListMusic size={14} /><span className="min-w-0 flex-1 truncate">{p.name}</span><span className="text-xs text-[#9aa7bc]">{p.count}</span></button>))}
          {mixes.map((m) => (
            <button key={m.id} type="button" onClick={() => pickMix(m.id)}
              className={`${entry} ${sel?.kind === "mix" && sel.id === m.id ? "bg-[rgb(var(--hh-s-hebung,27_37_54))] text-[#e8eef8]" : "text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"}`}>
              <Shuffle size={14} /><span className="min-w-0 flex-1 truncate">{m.name}</span></button>))}
        </nav>
        {can && <button type="button" className={BTN} disabled={busy} onClick={() => { setMix({ name: "", rules: emptyRules(), allowLong: false }); setSel({ kind: "new-mix" }) }}>+ {t("program.new_mix")}</button>}
        {playlists.length === 0 && mixes.length === 0 && <p className="text-sm text-[#9aa7bc]">{t("program.none")}</p>}
      </aside>
      <div className="min-w-0 space-y-3">
        {msg && <p className={`text-sm ${msg.ok ? "text-emerald-300" : "text-rose-300"}`} role="status">{msg.text}</p>}
        {!sel && <p className="text-sm text-[#9aa7bc]">{t("program.pick")}</p>}
        {pl && <PlaylistView pl={pl} items={items} canModerate={can} busy={busy}
          onChange={(v) => run(() => api.updatePlaylist(pl.id, v))} onMove={(a, b) => run(() => api.movePlaylistItem(pl.id, a, b))}
          onRemove={(i) => run(() => api.removePlaylistItem(pl.id, i))} onDelete={() => setAsk(true)}
          onPlayNow={() => run(() => api.setProgram("playlist", pl.id), "station.skipped")}
          onDropTracks={(ids) => run(() => api.addToPlaylist(pl.id, ids), "track.added")} />}
        {(sel?.kind === "mix" || sel?.kind === "new-mix") && <MixEditor name={mix.name} rules={mix.rules} allowLong={mix.allowLong}
          genres={genres} folders={folders} preview={preview} canModerate={can} busy={busy} isNew={sel.kind === "new-mix"}
          onChange={(v) => setMix((o) => ({ ...o, ...v }))}
          onSave={() => run(async () => {
            if (sel.kind === "new-mix") { const m = await api.createMix(mix.name.trim(), compactRules(mix.rules), mix.allowLong); setSel({ kind: "mix", id: m.id }) }
            else await api.updateMix(sel.id, mix.name.trim(), compactRules(mix.rules), mix.allowLong)
          }, "mix.saved")}
          onDelete={() => setAsk(true)} onPlayNow={() => sel.kind === "mix" && run(() => api.setProgram("mix", sel.id), "station.skipped")} />}
      </div>
      {ask && sel && sel.kind !== "new-mix" && <ConfirmDialog busy={busy}
        title={t(sel.kind === "playlist" ? "playlist.delete_title" : "mix.delete_title")}
        text={t(sel.kind === "playlist" ? "playlist.delete_text" : "mix.delete_text", { name: sel.kind === "playlist" ? pl?.name : mix.name })}
        onCancel={() => setAsk(false)}
        onConfirm={() => { setAsk(false); run(() => (sel.kind === "playlist" ? api.deletePlaylist(sel.id) : api.deleteMix(sel.id))); setSel(null) }} />}
    </div>
  )
}
