import { Loader2, PhoneIncoming, Save, Timer } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CallList } from "./_CallList"
import { Switch } from "./_Switch"
import { telephonyApi } from "./api"
import { pendingTest, saveSwitch, secondsLeft } from "./callsLogic"
import { errorKey } from "./connectionLogic"
import type { CallEntry, Connection } from "./types"

const btn = "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium disabled:cursor-not-allowed disabled:opacity-50"
type Configured = Extract<Connection, { configured: true }>

/** Anrufe annehmen: Schalter, Ansagetext, Testanruf mit „Ton gehört?“, letzte Anrufe. */
export function CallSettings({ conn }: { conn: Configured }) {
  const { t } = useTranslation("voip")
  const [answer, setAnswer] = useState(conn.answer_calls)
  const [savedGreeting, setSavedGreeting] = useState(conn.greeting)
  const [greeting, setGreeting] = useState(conn.greeting)
  const [testUntil, setTestUntil] = useState<string | null>(conn.test_until)
  const [left, setLeft] = useState(secondsLeft(conn.test_until))
  const [calls, setCalls] = useState<CallEntry[]>([])
  const [busy, setBusy] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const dirty = greeting !== savedGreeting

  const load = useCallback(() => {
    void telephonyApi.calls().then((r) => setCalls(r.calls)).catch(() => undefined)
  }, [])
  useEffect(load, [load])

  // Während das Testfenster offen ist: Countdown + Liste nachladen
  useEffect(() => {
    if (!testUntil) return
    const id = window.setInterval(() => {
      const s = secondsLeft(testUntil)
      setLeft(s)
      load()
      if (s === 0) setTestUntil(null)
    }, 1000)
    return () => window.clearInterval(id)
  }, [testUntil, load])

  const run = async (fn: () => Promise<void>) => {
    setBusy(true); setError(null); setSaved(false)
    try { await fn() } catch (e) { setError(errorKey((e as { code?: string }).code)) } finally { setBusy(false) }
  }
  const save = () => run(async () => {
    await telephonyApi.saveCalls({ answer_calls: answer, greeting })
    setSavedGreeting(greeting)
    setSaved(true)
  })
  const toggle = async (next: boolean) => {
    setAnswer(next); setBusy(true); setError(null); setSaved(false)
    const r = await saveSwitch(telephonyApi, next, savedGreeting, answer)
    setAnswer(r.value); setBusy(false)
    if (r.error) setError(errorKey(r.error)); else setSaved(true)
  }
  const startTest = () => run(async () => {
    const r = await telephonyApi.startTestCall()
    setTestUntil(r.test_until); setLeft(r.seconds)
  })
  const confirm = (id: number, heard: boolean) => run(async () => {
    await telephonyApi.confirmHeard(id, heard); load()
  })
  const pending = pendingTest(calls)
  const registered = conn.status === "registered"

  return (
    <section className="space-y-4 rounded-xl border border-zinc-800 bg-zinc-900/50 p-5" data-voip-calls="1">
      <h3 className="flex items-center gap-2 font-semibold text-zinc-100">
        <PhoneIncoming size={17} className="text-indigo-300" /> {t("calls.title")}
      </h3>

      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-zinc-200">{t("calls.answer")}</p>
          <p className="mt-0.5 text-xs leading-5 text-zinc-500">{t("calls.answer_help")}</p>
        </div>
        <Switch checked={answer} disabled={busy} onChange={(v) => void toggle(v)} label={t("calls.answer")} />
      </div>

      <label className="block space-y-1.5 text-sm text-zinc-300">
        <span>{t("calls.greeting")}</span>
        <textarea className="min-h-24 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500"
          value={greeting} maxLength={500} placeholder={conn.greeting_default} data-voip-greeting="1"
          onChange={(e) => { setSaved(false); setGreeting(e.target.value) }} />
        <span className="block text-xs text-zinc-500">{t("calls.greeting_help")}</span>
      </label>

      <div className="flex flex-wrap items-center gap-2">
        <button type="button" className={`${btn} bg-zinc-800 text-zinc-100 hover:bg-zinc-700`} disabled={busy || !dirty}
          onClick={() => void save()} data-voip-calls-save="1">
          <Save size={15} /> {t("calls.greeting_save")}
        </button>
        <button type="button" className={`${btn} bg-indigo-500 text-white hover:bg-indigo-400`}
          disabled={busy || !registered || left > 0} onClick={() => void startTest()} data-voip-test-call="1"
          title={registered ? undefined : t("calls.test_needs_connection")}>
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Timer size={15} />}
          {left > 0 ? t("calls.test_running", { seconds: left }) : t("calls.test_start")}
        </button>
        {saved && !error && <span className="text-sm text-emerald-300">{t("conn.saved")}</span>}
      </div>
      {left > 0 && <p className="text-sm text-indigo-200" data-voip-test-hint="1">{t("calls.test_hint")}</p>}
      {error && <p role="alert" className="text-sm text-red-300">{t(`conn.errors.${error}`)}</p>}

      {pending && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-4" data-voip-heard="1">
          <p className="text-sm text-amber-100">{t("calls.heard_question")}</p>
          <div className="mt-3 flex gap-2">
            <button type="button" className={`${btn} bg-emerald-600 text-white hover:bg-emerald-500`} disabled={busy}
              onClick={() => void confirm(pending.id, true)}>{t("calls.heard_yes")}</button>
            <button type="button" className={`${btn} bg-zinc-800 text-zinc-100 hover:bg-zinc-700`} disabled={busy}
              onClick={() => void confirm(pending.id, false)}>{t("calls.heard_no")}</button>
          </div>
        </div>
      )}

      <CallList calls={calls} />
    </section>
  )
}
