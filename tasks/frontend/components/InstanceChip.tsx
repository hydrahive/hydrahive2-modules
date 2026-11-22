import { useTranslation } from "react-i18next"
import type { InstanceScope } from "../foreign"

// Filter-Chip „Nur diese Instanz / Alle Instanzen“ (Gemeinsame Taskpflege, Spec §Oberfläche).
export function InstanceChip({ scope, onChange }: { scope: InstanceScope; onChange: (s: InstanceScope) => void }) {
  const { t } = useTranslation("tasks")
  const next: InstanceScope = scope === "all" ? "local" : "all"
  return (
    <button
      type="button"
      data-testid="instance-chip"
      data-scope={scope}
      onClick={() => onChange(next)}
      title={t("instances_hint")}
      className={`flex-shrink-0 px-2 py-0.5 rounded text-[10px] whitespace-nowrap border transition-colors
        ${scope === "all"
          ? "border-[#69d7ff]/30 text-[#69d7ff]"
          : "border-[rgb(var(--hh-s-rand,42_54_75))] text-[#9aa7bc] hover:text-[#c8d2df]"}`}
    >
      {scope === "all" ? t("instances_all") : t("instances_local")}
    </button>
  )
}
