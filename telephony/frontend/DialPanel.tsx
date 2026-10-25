import { Loader2, PhoneCall, PhoneOff } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CallList } from "./_CallList"
import { DialRules } from "./_DialRules"
import { telephonyApi } from "./api"
import { cleanNumberInput, dialErrorKey, dialStateKey } from "./dialLogic"
import type { CallEntry, Connection, DialMode, DialStatus } from "./types"

type Configured = Extract<Connection, { configured: true }>
const btn = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
const field = "w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 focus:border-indigo-500 focus:outline-none"

interface Props {
  conn: Configured
  initialNumber?: string
  initialMode?: DialMode
  initialTask?: string
}

/** Anrufen per Knopf: Ansage vorlesen (3a) oder Assistent mit Auftrag (3b). Nur der Nutzer löst aus. */
export function DialPanel({ conn, initialNumber = "", initialMode = "greeting", initialTask = "" }: Props) {
  const { t } = useTranslation("voip")
  const [number, setNumber] = useState(initialNumber)
  const [mode, setMode] = useState<DialMode>(initialMode)
  const [text, setText] = useState("")
  const [task, setTask] = useState(initialTask)
  const [share, setShare] = useState("")
  const [call, setCall] = useState<DialStatus>({ active: false })
  const [calls, setCalls] = useState<CallEntry[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const registered = conn.status === "registered"
  const ready = registered && !busy && number.replace(/\D/g, "").length >= 3 && (mode === "greeting" || task.trim() !== "")

  const loadCalls = useCallback(() => {
    void telephonyApi.calls().then((r) => setCalls(r.calls)).catch(() => undefined)
  }, [])
  const poll = useCallback(() => {
    void telephonyApi.dialStatus().then((s) => { setCall(s); if (!s.active) loadCalls() }).catch(() => undefined)
  }, [loadCalls])
  useEffect(poll, [poll])
  useEffect(() => {
    if (!call.active) return
    const id = window.setInterval(poll, 1000)
    return () => window.clearInterval(id)
  }, [call.active, poll])

  const fail = (e: unknown) => setError(dialErrorKey((e as { code?: string }).code))
  const start = async () => {
    setBusy(true); setError(null)
    try { setCall(await telephonyApi.dial({ number, text, mode, task, may_share: share })) } catch (e) { fail(e) } finally { setBusy(false) }
  }
  const hangup = async () => {
    try { setCall(await telephonyApi.hangup()) } catch { /* Status-Abfrage zeigt den echten Stand */ }
    poll()
  }
  const callback = async (id: number) => {
    setError(null)
    try {
      const r = await telephonyApi.callback(id)
      setNumber(cleanNumberInput(r.number)); setMode("assistant"); setTask(r.task)
      window.scrollTo({ top: 0, behavior: "smooth" })
    } catch (e) { fail(e) }
  }
  const markRead = async (id: number) => { await telephonyApi.markRead(id).catch(() => undefined); loadCalls() }
  const modeBtn = (m: DialMode) => (
    <button key={m} type="button" aria-pressed={mode === m} data-voip-dial-mode={m} onClick={() => setMode(m)}
      className={`rounded-lg px-3 py-1.5 text-sm ${mode === m ? "bg-indigo-500/20 text-indigo-200" : "text-zinc-400 hover:bg-zinc-800"}`}>
      {t(`dial.mode_${m}`)}
    </button>
  )

  return (
    <div className="space-y-5">
      <section className="space-y-5 rounded-xl border border-zinc-800 bg-zinc-900/40 p-5" data-voip-dial="1">
        <div>
          <h2 className="flex items-center gap-2 text-base font-semibold text-zinc-100"><PhoneCall size={17} /> {t("dial.title")}</h2>
          <p className="mt-1 text-sm text-zinc-400">{t("dial.intro")}</p>
        </div>
        {!registered && (
          <p className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-sm text-amber-200"
            data-voip-dial-needs-connection="1">{t("dial.needs_connection")}</p>
        )}
        <div className="flex w-fit gap-1 rounded-lg border border-zinc-800 p-1">{modeBtn("greeting")}{modeBtn("assistant")}</div>
        <div className="grid gap-4 md:grid-cols-2">
          <label className="block space-y-1 text-sm">
            <span className="text-zinc-300">{t("dial.number")}</span>
            <input className={field} inputMode="tel" autoComplete="off" value={number} data-voip-dial-number="1"
              onChange={(e) => setNumber(cleanNumberInput(e.target.value))} placeholder="030 1234567" />
            <span className="text-xs text-zinc-500">{t("dial.number_help")}</span>
          </label>
          {mode === "greeting" ? (
            <label className="block space-y-1 text-sm">
              <span className="text-zinc-300">{t("dial.text")}</span>
              <textarea className={`${field} min-h-20`} maxLength={500} value={text} data-voip-dial-text="1"
                onChange={(e) => setText(e.target.value)} />
              <span className="text-xs text-zinc-500">{t("dial.text_help")}</span>
            </label>
          ) : (
            <div className="space-y-4">
              <label className="block space-y-1 text-sm">
                <span className="text-zinc-300">{t("dial.task")}</span>
                <textarea className={`${field} min-h-24`} maxLength={1000} value={task} data-voip-dial-task="1"
                  onChange={(e) => setTask(e.target.value)} />
                <span className="text-xs text-zinc-500">{t("dial.task_help")}</span>
              </label>
              <label className="block space-y-1 text-sm">
                <span className="text-zinc-300">{t("dial.share")}</span>
                <textarea className={`${field} min-h-16`} maxLength={1000} value={share} data-voip-dial-share="1"
                  onChange={(e) => setShare(e.target.value)} />
                <span className="text-xs text-zinc-500">{t("dial.share_help")}</span>
              </label>
            </div>
          )}
        </div>
        {mode === "assistant" && <p className="text-xs text-zinc-400">{t("dial.assistant_info")}</p>}
        <div className="flex flex-wrap items-center gap-3">
          {!call.active ? (
            <button type="button" className={`${btn} bg-indigo-500 text-white hover:bg-indigo-400`} data-voip-dial-start="1"
              disabled={!ready} onClick={() => void start()}>
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
        <DialRules conn={conn} onError={setError} />
      </section>
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5" data-voip-dial-calls="1">
        <CallList calls={calls} onRead={(id) => void markRead(id)} onCallback={(id) => void callback(id)} />
      </section>
    </div>
  )
}
