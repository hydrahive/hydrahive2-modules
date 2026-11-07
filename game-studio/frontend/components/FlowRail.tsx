import { Check } from "lucide-react"
import { useTranslation } from "react-i18next"
import { FLOW_STEPS } from "../flow"

interface Props {
  activeStep: number
  availableStep: number
  onSelect: (step: number) => void
}

export function FlowRail({ activeStep, availableStep, onSelect }: Props) {
  const { t } = useTranslation("gameStudio")
  return (
    <nav aria-label={t("flow.navigation")} className="grid grid-cols-4 gap-1 rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-1.5">
      {FLOW_STEPS.map((key, index) => {
        const step = index + 1
        const available = step <= availableStep
        const complete = step < availableStep
        const active = step === activeStep
        return (
          <button
            key={key}
            type="button"
            disabled={!available}
            onClick={() => onSelect(step)}
            aria-current={active ? "step" : undefined}
            className={`flex min-w-0 flex-col items-center gap-1 rounded-lg px-1 py-2 text-center transition focus:outline-none focus:ring-2 focus:ring-[#69d7ff]/60 ${active ? "bg-[#69d7ff]/12 text-[#e8eef8]" : available ? "text-[#9aa7bc] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]" : "cursor-not-allowed text-[#596579]"}`}
          >
            <span className={`flex h-6 w-6 items-center justify-center rounded-full text-[11px] font-semibold ${active ? "bg-[#69d7ff] text-[#0d1420]" : complete ? "bg-emerald-400/15 text-emerald-300" : "bg-[rgb(var(--hh-s-box,21_28_43))]"}`}>
              {complete ? <Check size={13} aria-hidden="true" /> : step}
            </span>
            <span className="hidden truncate text-[10px] sm:block">{t(`flow.steps.${key}`)}</span>
          </button>
        )
      })}
    </nav>
  )
}
