import {
  AlertTriangle,
  CheckCircle2,
  Loader2,
  PhoneIncoming,
  ShieldCheck,
  Wifi,
} from "lucide-react"
import { useState, type FormEvent } from "react"
import { useTranslation } from "react-i18next"
import { telephonyApi } from "./api"
import type { RegistrationProbeOutcome } from "./types"

type VisibleOutcome = RegistrationProbeOutcome | "request_failed"
type TestingMode = "registration" | "incoming"

interface RegistrationProbeSettingsProps {
  registrar: string
  port: number
}

export function RegistrationProbeSettings({ registrar, port }: RegistrationProbeSettingsProps) {
  const { t } = useTranslation("voip")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [testingMode, setTestingMode] = useState<TestingMode | null>(null)
  const [outcome, setOutcome] = useState<VisibleOutcome | null>(null)

  const canSubmit = username.length >= 8 && password.length >= 12
  const testing = testingMode !== null

  const runProbe = async (mode: TestingMode) => {
    if (!canSubmit || testing) return
    setTestingMode(mode)
    setOutcome(null)
    try {
      const body = { registrar, port: Number(port), username, password }
      const result =
        mode === "incoming"
          ? await telephonyApi.testIncomingCall(body)
          : await telephonyApi.testRegistration(body)
      setOutcome(result.outcome)
    } catch {
      setOutcome("request_failed")
    } finally {
      setPassword("")
      setTestingMode(null)
    }
  }

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    void runProbe("registration")
  }

  const success = outcome === "registered" || outcome === "incoming_answered"

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
        onSubmit={submit}
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
            {testingMode === "registration" ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <Wifi size={16} />
            )}
            {testingMode === "registration" ? t("probe.testing") : t("probe.test_action")}
          </button>
          <button
            type="button"
            disabled={!canSubmit || testing}
            onClick={() => void runProbe("incoming")}
            className="inline-flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-2.5 text-sm font-semibold text-emerald-100 hover:bg-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {testingMode === "incoming" ? (
              <Loader2 size={16} className="animate-spin" />
            ) : (
              <PhoneIncoming size={16} />
            )}
            {testingMode === "incoming"
              ? t("probe.incoming_testing")
              : t("probe.incoming_test_action")}
          </button>
          <p className="basis-full text-xs text-zinc-500">{t("probe.requirements")}</p>
        </div>
      </form>

      {testingMode === "incoming" && (
        <div role="status" className="rounded-xl border border-sky-500/25 bg-sky-500/5 p-4">
          <div className="flex items-start gap-3 text-sky-100">
            <PhoneIncoming size={19} className="mt-0.5 shrink-0" />
            <p className="text-sm leading-6">{t("probe.incoming_instruction")}</p>
          </div>
        </div>
      )}

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
