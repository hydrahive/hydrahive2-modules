import { AlertTriangle, CheckCircle2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { RegistrationProbeOutcome } from "./types"

type VisibleOutcome = RegistrationProbeOutcome | "request_failed"

interface ProbeResultProps {
  outcome: VisibleOutcome
  toneConfirmation: boolean | null
  onToneConfirmation: (heard: boolean) => void
}

export function ProbeResult({
  outcome,
  toneConfirmation,
  onToneConfirmation,
}: ProbeResultProps) {
  const { t } = useTranslation("voip")
  const toneConfirmed = outcome === "incoming_answered" && toneConfirmation === true
  const resultKey =
    outcome === "incoming_answered" && toneConfirmation !== null
      ? toneConfirmation
        ? "tone_confirmed"
        : "tone_missing"
      : outcome
  const success = outcome === "registered" || toneConfirmed

  return (
    <div
      role="status"
      className={`flex items-start gap-3 rounded-xl border p-4 ${success ? "border-emerald-500/25 bg-emerald-500/5 text-emerald-100" : "border-amber-500/25 bg-amber-500/5 text-amber-100"}`}
    >
      {success ? <CheckCircle2 size={19} /> : <AlertTriangle size={19} />}
      <div>
        <p className="text-sm font-semibold">{t(`probe.results.${resultKey}.title`)}</p>
        <p className="mt-1 text-xs opacity-80">{t(`probe.results.${resultKey}.description`)}</p>
        {outcome === "incoming_answered" && toneConfirmation === null && (
          <div className="mt-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => onToneConfirmation(true)}
              className="rounded-lg bg-emerald-500 px-3 py-2 text-xs font-semibold text-white hover:bg-emerald-400"
            >
              {t("probe.tone_heard")}
            </button>
            <button
              type="button"
              onClick={() => onToneConfirmation(false)}
              className="rounded-lg border border-amber-400/40 px-3 py-2 text-xs font-semibold text-amber-100 hover:bg-amber-500/10"
            >
              {t("probe.tone_not_heard")}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
