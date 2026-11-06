import { CheckCircle2, CircleAlert, Monitor, Share2, ShieldCheck } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { SharingStatus, WorkstationStatus } from "../types"

interface Props {
  status: WorkstationStatus
  sharing: SharingStatus
}

export function WorkstationPanel({ status, sharing }: Props) {
  const { t } = useTranslation("gameStudio")
  const ready = status.ready
  const Icon = ready ? CheckCircle2 : CircleAlert

  return (
    <section className="rounded-2xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-4" aria-labelledby="workstation-title">
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 rounded-xl p-2 ${ready ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-400/10 text-amber-300"}`}>
          <Monitor size={20} aria-hidden="true" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h2 id="workstation-title" className="text-sm font-semibold text-[#e8eef8]">{t("workstation.title")}</h2>
            <Icon size={16} className={ready ? "text-emerald-300" : "text-amber-300"} aria-hidden="true" />
          </div>
          <p className="mt-1 text-xs leading-5 text-[#9aa7bc]">{t(`workstation.${status.code}`)}</p>
          <div className="mt-3 flex items-center gap-2 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2">
            <Share2 size={15} className={`shrink-0 ${sharing.available && sharing.running ? "text-emerald-300" : "text-amber-300"}`} aria-hidden="true" />
            <span className="text-[11px] leading-4 text-[#c8d2df]">{t(sharing.available && sharing.running ? "sharing.available" : "sharing.unavailable")}</span>
          </div>
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2">
            <ShieldCheck size={15} className="shrink-0 text-[#69d7ff]" aria-hidden="true" />
            <span className="text-[11px] leading-4 text-[#c8d2df]">{t("workstation.runnerPending")}</span>
          </div>
        </div>
      </div>
    </section>
  )
}
