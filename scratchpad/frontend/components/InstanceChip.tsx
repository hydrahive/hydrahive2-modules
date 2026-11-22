import type { InstanceScope } from "../foreign"
import type { T } from "../texts.de"

// Filter-Chip „Nur diese Instanz / Alle Instanzen“ (Gemeinsame Taskpflege, Spec §Oberfläche).
export function InstanceChip({ scope, t, onChange }: { scope: InstanceScope; t: T; onChange: (s: InstanceScope) => void }) {
  return (
    <button type="button" data-testid="instance-chip" data-scope={scope} title={t("instances_hint")}
      onClick={() => onChange(scope === "all" ? "local" : "all")} aria-pressed={scope === "all"}
      className={`inline-flex items-center rounded-[6px] border px-2 py-1 text-[11px] font-semibold transition-colors ${
        scope === "all"
          ? "border-[#69d7ff]/60 bg-[#69d7ff]/15 text-[#c8f2ff]"
          : "border-[rgb(var(--hh-s-rand,52_66_92))] text-[#9aa7bc] hover:text-[#c8d2df]"}`}>
      {scope === "all" ? t("instances_all") : t("instances_local")}
    </button>
  )
}
