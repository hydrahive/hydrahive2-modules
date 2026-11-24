import { useTranslation } from "react-i18next"
import { AlertTriangle, Loader2, Power } from "lucide-react"
import type { SeatAction, SeatsView } from "./api"
import { runResult, switchAction } from "./seats"

const btn = "flex items-center gap-2 rounded-[4px] border px-3 py-1.5 text-sm font-semibold disabled:opacity-40"

interface Props {
  v: SeatsView
  confirming: SeatAction | null
  onAsk: (a: SeatAction) => void
  onConfirm: () => void
  onCancel: () => void
}

/** Multiseat M2: Zweiten Arbeitsplatz ein-/ausschalten – Knopf, Bestätigung, Laufanzeige, Ergebnis (reine Anzeige). */
export function SeatsSwitch({ v, confirming, onAsk, onConfirm, onCancel }: Props) {
  const { t } = useTranslation("vitrine")
  const action = switchAction(v)
  const res = runResult(v)
  return (
    <div className="space-y-2 border-t border-[rgb(var(--hh-s-rand,42_54_75))] pt-3" data-part="switch">
      <p className="text-xs text-[#9aa7bc]">{t(v.applied ? "seats_state_on" : "seats_state_off")}</p>
      {v.running && (
        <p className="flex items-center gap-2 text-sm text-[#69d7ff]" data-state="running">
          <Loader2 size={14} className="animate-spin" />{t(`seats_running_${v.running}`)}
        </p>
      )}
      {!v.running && !v.applied && v.saved && v.saved_error && (
        <p className="text-xs text-amber-200" data-hint="saved-error">{t("seats_saved_invalid")} {t(v.saved_error)}</p>
      )}
      {action && !confirming && (
        <button type="button" data-action={action} onClick={() => onAsk(action)}
          className={`${btn} ${action === "apply" ? "border-[#69d7ff]/50 bg-[#69d7ff]/15 text-[#69d7ff]" : "border-amber-400/50 bg-amber-400/10 text-amber-100"}`}>
          <Power size={13} />{t(action === "apply" ? "seats_switch_on" : "seats_switch_off")}
        </button>
      )}
      {confirming && (
        <div role="alertdialog" data-part="confirm" className="space-y-2 rounded-[4px] border border-amber-400/40 bg-amber-400/10 p-3 text-sm text-amber-100">
          <p className="flex items-start gap-2"><AlertTriangle size={14} className="mt-0.5 shrink-0" />{t("seats_confirm_text")}</p>
          <div className="flex gap-2">
            <button type="button" data-action="confirm" onClick={onConfirm} className={`${btn} border-amber-400/60 bg-amber-400/20`}>
              {t(confirming === "apply" ? "seats_switch_on" : "seats_switch_off")}
            </button>
            <button type="button" data-action="cancel" onClick={onCancel} className={`${btn} border-[rgb(var(--hh-s-rand,42_54_75))] text-[#9aa7bc]`}>
              {t("seats_cancel")}
            </button>
          </div>
        </div>
      )}
      {res && (
        <div data-result={res.ok ? "ok" : "fail"} className={`text-xs ${res.ok ? "text-emerald-300" : "text-amber-200"}`}>
          <p>{t(res.msgKey)}</p>
          {res.detail && <pre className="mt-1 whitespace-pre-wrap text-[11px] text-[#9aa7bc]">{res.detail}</pre>}
        </div>
      )}
    </div>
  )
}
