import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { MessageSquare, Send, X } from "lucide-react"
import { vitrineApi, type MessageKind, type VitrineMessage } from "./api"

const KINDS: MessageKind[] = ["info", "success", "warning", "error"]
const BAR: Record<MessageKind, string> = { info: "bg-[#69d7ff]", success: "bg-emerald-400", warning: "bg-amber-300", error: "bg-rose-400" }

export function MessagesCard() {
  const { t } = useTranslation("vitrine")
  const [list, setList] = useState<VitrineMessage[]>([])
  const [text, setText] = useState("")
  const [kind, setKind] = useState<MessageKind>("info")
  const [err, setErr] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [now, setNow] = useState(() => Date.now() / 1000)

  const load = useCallback(() => { vitrineApi.messages().then(setList).catch(() => {}) }, [])
  useEffect(() => {
    load()
    const id = window.setInterval(() => { load(); setNow(Date.now() / 1000) }, 3000)
    return () => window.clearInterval(id)
  }, [load])

  async function send() {
    setErr(null); setBusy(true)
    try { await vitrineApi.sendMessage({ text: text.trim() || t("message_default"), kind }); setText(""); load() }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    finally { setBusy(false) }
  }

  async function dismiss(id: string) {
    try { await vitrineApi.dismiss(id) } catch { /* schon weg */ }
    load()
  }

  return (
    <section className="space-y-2">
      <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><MessageSquare size={14} className="text-[#69d7ff]" />{t("messages")}</h2>
      <p className="text-xs text-[#9aa7bc]">{t("messages_hint")}</p>
      <div className="flex flex-wrap items-center gap-2">
        <input value={text} maxLength={280} onChange={(e) => setText(e.target.value)} placeholder={t("message_default")}
          aria-label={t("message_text")} onKeyDown={(e) => { if (e.key === "Enter") void send() }}
          className="min-w-[14rem] flex-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_19_31))] px-2 py-1.5 text-sm text-[#e8eef8]" />
        <select value={kind} onChange={(e) => setKind(e.target.value as MessageKind)} aria-label={t("kind_label")}
          className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_19_31))] px-2 py-1.5 text-sm text-[#e8eef8]">
          {KINDS.map((k) => <option key={k} value={k}>{t(`msg_kind.${k}`)}</option>)}
        </select>
        <button type="button" disabled={busy} onClick={() => void send()}
          className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-3 py-1.5 text-xs font-bold text-[#69d7ff] disabled:opacity-50">
          <Send size={13} />{t("message_send")}
        </button>
      </div>
      {err && <p className="text-xs text-rose-300">{err}</p>}
      {list.length === 0
        ? <p className="rounded-[4px] border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] p-3 text-center text-xs text-[#9aa7bc]">{t("no_messages")}</p>
        : (
          <ul className="divide-y divide-[rgb(var(--hh-s-rand,28_38_56))] rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))]">
            {list.map((m) => (
              <li key={m.id} className="flex items-center gap-3 px-3 py-2 text-sm text-[#c8d2df]">
                <span className={`h-8 w-1 shrink-0 rounded ${BAR[m.kind]}`} />
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-bold">{m.title || t(`msg_kind.${m.kind}`)}{m.count > 1 ? `  ×${m.count}` : ""}</span>
                  <span className="block truncate">{m.text}</span>
                </span>
                <span className="shrink-0 text-xs text-[#9aa7bc]">{t("seconds_left", { s: Math.max(0, Math.round(m.expires - now)) })}</span>
                <button type="button" onClick={() => void dismiss(m.id)} title={t("dismiss")} aria-label={t("dismiss")}
                  className="shrink-0 rounded-[4px] p-1 text-[#9aa7bc] hover:bg-rose-500/20 hover:text-rose-200"><X size={14} /></button>
              </li>
            ))}
          </ul>
        )}
    </section>
  )
}
