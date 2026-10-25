import { Loader2, PhoneCall, PhoneOff } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Switch } from "./_Switch"
import { telephonyApi } from "./api"
import { cleanNumberInput, dialErrorKey, dialStateKey } from "./dialLogic"
import type { Connection, DialStatus } from "./types"

type Configured = Extract<Connection, { configured: true }>
const btn = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
const field = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 focus:border-indigo-500 focus:outline-none"

/** Anrufen per Knopf (Etappe 3a): Nummer + Ansage → HydraHive wählt, liest vor, legt auf. Nur der Nutzer löst aus. */
export function DialPanel({ conn, initialNumber = "" }: { conn: Configured; initialNumber?: string }) {
  const { t } = useTranslation("voip")
  const [number, setNumber] = useState(initialNumber)
  const [text, setText] = useState("")
  const [call, setCall] = useState<DialStatus>({ active: false })
  const [premium, setPremium] = useState(conn.allow_premium)
  const [foreign, setForeign] = useState(conn.allow_foreign)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const registered = conn.status === "registered"

  const poll = useCallback(() => {
    void telephonyApi.dialStatus().then(setCall).catch(() => undefined)
  }, [])
  useEffect(poll, [poll])
  useEffect(() => {
    if (!call.active) return
    const id = window.setInterval(poll, 1000)
    return () => window.clearInterval(id)
  }, [call.active, poll])

  const start = async () => {
    setBusy(true); setError(null)
    try { setCall(await telephonyApi.dial(number, text)) }
    catch (e) { setError(dialErrorKey((e as { code?: string }).code)) }
    finally { setBusy(false) }
  }
  const hangup = async () => {
    try { setCall(await telephonyApi.hangup()) } catch { /* Status-Abfrage zeigt den echten Stand */ }
    poll()
  }
  const saveRules = async (p: boolean, f: boolean) => {
    const before = [premium, foreign]
    setPremium(p); setForeign(f); setError(null)
    try { await telephonyApi.saveDialRules(p, f) }
    catch (e) { setPremium(before[0]); setForeign(before[1]); setError(dialErrorKey((e as { code?: string }).code)) }
  }

  return (
    <section className="space-y-5 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5" data-voip-dial="1">
      <div>
        <h2 className="flex items-center gap-2 text-base font-semibold text-zinc-100"><PhoneCall size={17} /> {t("dial.title")}</h2>
        <p className="mt-1 text-sm text-zinc-400">{t("dial.intro")}</p>
      </div>
      {!registered && (
        <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-200"
          data-voip-dial-needs-connection="1">{t("dial.needs_connection")}</p>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <label className="block space-y-1 text-sm">
          <span className="text-zinc-300">{t("dial.number")}</span>
          <input className={field} inputMode="tel" autoComplete="off" value={number} data-voip-dial-number="1"
            onChange={(e) => setNumber(cleanNumberInput(e.target.value))} placeholder="030 1234567" />
          <span className="text-xs text-zinc-500">{t("dial.number_help")}</span>
        </label>
        <label className="block space-y-1 text-sm">
          <span className="text-zinc-300">{t("dial.text")}</span>
          <textarea className={`${field} min-h-20`} maxLength={500} value={text} data-voip-dial-text="1"
            onChange={(e) => setText(e.target.value)} />
          <span className="text-xs text-zinc-500">{t("dial.text_help")}</span>
        </label>
      </div>
      <div className="flex flex-wrap items-center gap-3">
        {!call.active ? (
          <button type="button" className={`${btn} bg-indigo-500 text-white hover:bg-indigo-400`} data-voip-dial-start="1"
            disabled={!registered || busy || number.replace(/\D/g, "").length < 3} onClick={() => void start()}>
            {busy ? <Loader2 size={15} className="animate-spin" /> : <PhoneCall size={15} />} {t("dial.start")}
          </button>
        ) : (
          <button type="button" className={`${btn} bg-red-500/90 text-white hover:bg-red-500`} data-voip-dial-hangup="1"
            onClick={() => void hangup()}>
            <PhoneOff size={15} /> {t("dial.hangup")}
          </button>
        )}
        {call.active && call.state && (
          <span className="text-sm text-zinc-300" role="status" data-voip-dial-state={call.state}>
            {t(dialStateKey(call.state), { number: call.number })}
          </span>
        )}
        {!call.active && call.state && call.result && (
          <span className="text-sm text-zinc-400" data-voip-dial-last="1">
            {t("dial.last", { number: call.number, result: t(`calls.result.${call.result}`) })}
          </span>
        )}
      </div>
      {error && <p role="alert" className="text-sm text-red-300">{t(error)}</p>}
      <p className="text-xs text-zinc-500">{t("dial.limits")}</p>
      <div className="space-y-3 border-t border-zinc-800 pt-4">
        <p className="text-sm font-medium text-zinc-300">{t("dial.rules_title")}</p>
        <div className="flex items-center gap-3 text-sm text-zinc-300" data-voip-allow="premium">
          <Switch checked={premium} label={t("dial.allow_premium")} onChange={(v) => void saveRules(v, foreign)} />
          {t("dial.allow_premium")}
        </div>
        <div className="flex items-center gap-3 text-sm text-zinc-300" data-voip-allow="foreign">
          <Switch checked={foreign} label={t("dial.allow_foreign")} onChange={(v) => void saveRules(premium, v)} />
          {t("dial.allow_foreign")}
        </div>
        <p className="text-xs text-zinc-500">{t("dial.rules_help")}</p>
      </div>
    </section>
  )
}
