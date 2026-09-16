import { AlertTriangle, CheckCircle2, Loader2, ShieldCheck, Wifi } from "lucide-react"
import { useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { telephonyApi } from "./api"
import type { RegistrationProbeOutcome } from "./types"

type VisibleOutcome = RegistrationProbeOutcome | "request_failed"

interface RegistrationProbeSettingsProps {
  registrar: string
  port: number
}

export function RegistrationProbeSettings({ registrar, port }: RegistrationProbeSettingsProps) {
  const { t } = useTranslation("voip")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [testing, setTesting] = useState(false)
  const [outcome, setOutcome] = useState<VisibleOutcome | null>(null)

  const canSubmit = username.length >= 8 && password.length >= 12

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!canSubmit || testing) return
    setTesting(true)
    setOutcome(null)
    try {
      const result = await telephonyApi.testRegistration({
        registrar,
        port: Number(port),
        username,
        password,
      })
      setOutcome(result.outcome)
    } catch {
      setOutcome("request_failed")
    } finally {
      setPassword("")
      setTesting(false)
    }
  }

  const success = outcome === "registered"

  return (
    <section className="space-y-5" aria-labelledby="registration-probe-title">
      <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-5">
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-indigo-500/10 p-2 text-indigo-300">
            <Wifi size={18} />
          </span>
          <div>
            <h2 id="registration-probe-title" className="font-semibold text-zinc-100">
              {t("probe.title")}
            </h2>
            <p className="mt-1 text-sm leading-6 text-zinc-400">{t("probe.description")}</p>
          </div>
        </div>
      </div>

      <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 px-4 py-3">
        <div className="flex items-start gap-2 text-sm text-emerald-100">
          <ShieldCheck size={17} className="mt-0.5 shrink-0 text-emerald-300" />
          <p>{t("probe.ephemeral_notice")}</p>
        </div>
      </div>

      <form
        autoComplete="off"
        onSubmit={(event) => void submit(event)}
        className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5"
      >
        <fieldset disabled={testing} className="grid gap-4 sm:grid-cols-2">
          <label className="space-y-1.5 text-sm text-zinc-300">
            <span>{t("probe.registrar")}</span>
            <input
              required
              inputMode="decimal"
              value={registrar}
              readOnly
              className="w-full cursor-not-allowed rounded-lg border border-zinc-800 bg-zinc-950/70 px-3 py-2.5 text-zinc-500 outline-none"
            />
          </label>
          <label className="space-y-1.5 text-sm text-zinc-300">
            <span>{t("probe.port")}</span>
            <input
              required
              type="number"
              min={1}
              max={65535}
              value={port}
              readOnly
              className="w-full cursor-not-allowed rounded-lg border border-zinc-800 bg-zinc-950/70 px-3 py-2.5 text-zinc-500 outline-none"
            />
          </label>
          <label className="space-y-1.5 text-sm text-zinc-300">
            <span>{t("probe.username")}</span>
            <input
              required
              minLength={8}
              maxLength={64}
              autoComplete="off"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-zinc-100 outline-none focus:border-indigo-400"
            />
          </label>
          <label className="space-y-1.5 text-sm text-zinc-300">
            <span>{t("probe.password")}</span>
            <input
              required
              type="password"
              minLength={12}
              maxLength={128}
              autoComplete="off"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2.5 text-zinc-100 outline-none focus:border-indigo-400"
            />
          </label>
        </fieldset>

        <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-zinc-800 pt-4">
          <button
            type="submit"
            disabled={!canSubmit || testing}
            className="inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-400 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {testing ? <Loader2 size={16} className="animate-spin" /> : <Wifi size={16} />}
            {testing ? t("probe.testing") : t("probe.test_action")}
          </button>
          <p className="text-xs text-zinc-500">{t("probe.requirements")}</p>
        </div>
      </form>

      {outcome && (
        <div
          role="status"
          className={`flex items-start gap-3 rounded-xl border p-4 ${success ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-100" : "border-amber-500/25 bg-amber-500/5 text-amber-100"}`}
        >
          {success ? <CheckCircle2 size={19} /> : <AlertTriangle size={19} />}
          <div>
            <p className="text-sm font-semibold">{t(`probe.results.${outcome}.title`)}</p>
            <p className="mt-1 text-xs opacity-80">{t(`probe.results.${outcome}.description`)}</p>
          </div>
        </div>
      )}
    </section>
  )
}
