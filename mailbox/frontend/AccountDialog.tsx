import { useState } from "react"
import { X } from "lucide-react"
import { mailApi, type AccountIn } from "./api"

const EMPTY: AccountIn = { label: "", address: "", imap_host: "", imap_port: 993, imap_tls: "ssl", smtp_host: "",
  smtp_port: 465, smtp_tls: "ssl", username: "", password: "" }
const field = "w-full rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-2 py-1.5 text-sm text-[#e8eef8]"

/** Konto hinzufügen: Adresse eingeben → Vorschlag (Server, Ports, Hinweis z. B. Gmail-App-Passwort) → Test beim Speichern. */
export function AccountDialog({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [a, setA] = useState<AccountIn>(EMPTY)
  const [hint, setHint] = useState("")
  const [more, setMore] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const set = (p: Partial<AccountIn>) => setA((x) => ({ ...x, ...p }))

  async function suggest() {
    if (!a.address.includes("@")) return
    try {
      const s = await mailApi.suggest(a.address)
      set({ imap_host: s.imap_host, imap_port: s.imap_port, imap_tls: s.imap_tls, smtp_host: s.smtp_host,
        smtp_port: s.smtp_port, smtp_tls: s.smtp_tls, username: a.username || a.address, label: a.label || a.address })
      setHint(s.hint)
      if (!s.known) setMore(true)
    } catch { setErr("Adresse ungültig") }
  }

  async function save() {
    setBusy(true); setErr(null)
    try { await mailApi.createAccount(a); onSaved() } catch (e) { setErr(e instanceof Error ? e.message : String(e)) } finally { setBusy(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-label="Konto hinzufügen">
      <div className="w-full max-w-md space-y-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
        <header className="flex items-center justify-between">
          <h2 className="font-bold text-[#e8eef8]">Mailkonto hinzufügen</h2>
          <button type="button" onClick={onClose} aria-label="Schließen" className="text-[#8d9ab0] hover:text-[#e8eef8]"><X size={16} /></button>
        </header>
        <label className="block space-y-1 text-xs text-[#8d9ab0]">Mailadresse
          <input className={field} value={a.address} autoComplete="email" onChange={(e) => set({ address: e.target.value.trim() })} onBlur={() => void suggest()} />
        </label>
        <label className="block space-y-1 text-xs text-[#8d9ab0]">Passwort
          <input className={field} type="password" value={a.password} autoComplete="new-password" onChange={(e) => set({ password: e.target.value })} />
        </label>
        {hint && <p className="rounded-[4px] border border-amber-300/40 bg-amber-300/10 p-2 text-xs text-amber-100" data-mbx-hint="1">{hint}</p>}
        <button type="button" onClick={() => setMore(!more)} className="text-xs text-[#69d7ff] hover:underline">
          {more ? "Weniger" : "Server-Einstellungen"}</button>
        {more && (
          <div className="grid grid-cols-3 gap-2 text-xs text-[#8d9ab0]">
            <label className="col-span-3 space-y-1">Name des Kontos<input className={field} value={a.label} onChange={(e) => set({ label: e.target.value })} /></label>
            <label className="col-span-3 space-y-1">Benutzername<input className={field} value={a.username} onChange={(e) => set({ username: e.target.value })} /></label>
            <label className="col-span-2 space-y-1">IMAP-Server<input className={field} value={a.imap_host} onChange={(e) => set({ imap_host: e.target.value.trim() })} /></label>
            <label className="space-y-1">Port<select className={field} value={a.imap_port} onChange={(e) => {
              const p = Number(e.target.value); set({ imap_port: p, imap_tls: p === 143 ? "starttls" : "ssl" }) }}>
              <option value={993}>993 (SSL)</option><option value={143}>143 (STARTTLS)</option></select></label>
            <label className="col-span-2 space-y-1">SMTP-Server<input className={field} value={a.smtp_host} onChange={(e) => set({ smtp_host: e.target.value.trim() })} /></label>
            <label className="space-y-1">Port<select className={field} value={a.smtp_port} onChange={(e) => {
              const p = Number(e.target.value); set({ smtp_port: p, smtp_tls: p === 465 ? "ssl" : "starttls" }) }}>
              <option value={465}>465 (SSL)</option><option value={587}>587 (STARTTLS)</option></select></label>
          </div>
        )}
        {err && <p className="text-xs text-rose-300" data-mbx-error="1">{err}</p>}
        <p className="text-[11px] text-[#718097]">Beim Speichern wird die Anmeldung geprüft. Danach holt Mailbox alle Ordner und alle Jahre ins Archiv – das kann bei großen Postfächern Stunden dauern.</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-sm text-[#c8d2df] hover:bg-[#1c2638]">Abbrechen</button>
          <button type="button" onClick={() => void save()} data-mbx-save="1"
            disabled={busy || !a.address || !a.password || !a.imap_host}
            className="rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff] disabled:opacity-40">
            {busy ? "Prüfe Anmeldung …" : "Speichern"}</button>
        </div>
      </div>
    </div>
  )
}
