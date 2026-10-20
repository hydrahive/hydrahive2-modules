import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Loader2 } from "lucide-react"
import { getAccess, setAccess, type Access } from "./api"
import { errorKey } from "./logic"

/** Nur Admin: Werkzeug für alle Agenten freischalten oder genau das wieder zurücknehmen (Spec §12.4). */
export function AgentsAccess() {
  const { t } = useTranslation("diagramme")
  const [st, setSt] = useState<Access | null>(null)
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState("")

  useEffect(() => { getAccess().then(setSt).catch(() => {}) }, [])

  const run = async (on: boolean) => {
    setBusy(true); setMsg("")
    try {
      const res = await setAccess(on)
      setSt(res)
      setMsg(t("agents_done", { changed: res.changed ?? 0 }))
    } catch (e) {
      setMsg(t(errorKey(e)))
    } finally { setBusy(false) }
  }

  return (
    <section className="flex flex-wrap items-center gap-3 rounded-lg border border-white/10 bg-white/[3%] px-4 py-3" data-agents-access>
      <div className="min-w-0 flex-1">
        <div className="text-sm font-medium text-zinc-100">{t("agents_title")}</div>
        <div className="text-xs text-zinc-400">
          {st ? t("agents_count", { with: st.with_tool, total: st.total }) : t("loading")}
          {msg && <span className="ml-2 text-zinc-300">{msg}</span>}
        </div>
      </div>
      {busy && <Loader2 size={16} className="animate-spin text-zinc-400" />}
      {st && st.with_tool < st.total && (
        <button type="button" disabled={busy} onClick={() => run(true)}
          className="rounded bg-sky-500 px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50">{t("agents_on")}</button>
      )}
      {st && st.unlocked_by_us > 0 && (
        <button type="button" disabled={busy} onClick={() => run(false)}
          className="rounded px-3 py-1.5 text-sm text-zinc-300 hover:text-white disabled:opacity-50">{t("agents_off")}</button>
      )}
    </section>
  )
}
