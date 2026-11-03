// Fallliste mit Status und Auswahl.
import { useTranslation } from "react-i18next"
import type { CaseSummary } from "./api"
import { MUTED, TEXT, panel } from "./ui"

interface Props {
  cases: CaseSummary[]
  selected: string | null
  onSelect: (caseId: string) => void
  loading: boolean
}

export function CaseList({ cases, selected, onSelect, loading }: Props) {
  const { t } = useTranslation("zerlegewerkstatt")

  if (loading) {
    return (
      <div className={`${panel} h-24 animate-pulse`} aria-hidden="true" />
    )
  }
  if (cases.length === 0) {
    return (
      <div className={`${panel}`}>
        <p className={`text-sm ${MUTED}`}>{t("noCases")}</p>
      </div>
    )
  }

  return (
    <div className={`${panel} space-y-2`}>
      <h2 className={`text-sm font-semibold ${TEXT}`}>{t("caseList")}</h2>
      <ul className="space-y-1">
        {cases.map((item) => (
          <li key={item.id}>
            <button
              onClick={() => onSelect(item.id)}
              aria-current={selected === item.id}
              className={`w-full rounded-lg border px-3 py-2 text-left transition-colors ${
                selected === item.id
                  ? "border-[rgb(var(--hh-s-rand-hover,70_97_127))] bg-[rgb(var(--hh-s-hebung,27_37_54))]"
                  : "border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))]"
              }`}
            >
              <span className={`block text-sm ${TEXT}`}>{item.title}</span>
              <span className={`block text-xs ${MUTED}`}>
                {item.target ? `${item.target} · ` : ""}
                {t("caseCount", { artifacts: item.artifact_count, jobs: item.job_count })}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
