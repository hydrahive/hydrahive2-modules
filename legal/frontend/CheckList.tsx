import { Check, X } from "lucide-react"
import { CHECK_LABEL, checkSummary, type CheckResult } from "./letterFormat"

/** Prüfliste eines Briefs (ohne KI, vom Backend). Nichts blockiert – sie zeigt nur, was fehlt. */
export function CheckList({ check }: { check: CheckResult | null }) {
  const s = checkSummary(check)
  if (!check) return <p className="text-xs text-[#9aa7bc]">Prüfliste lädt …</p>
  return (
    <div className="space-y-2 text-xs">
      <p className={s.ok ? "text-emerald-300" : "text-amber-200"}>
        {s.ok ? "Alle Punkte erfüllt." : `${s.open} von ${s.total} Punkten offen – Übernehmen ist trotzdem möglich.`}
      </p>
      <ul className="space-y-1">
        {check.items.map((i) => (
          <li key={i.key} className="flex gap-1.5">
            {i.ok ? <Check size={13} className="mt-0.5 shrink-0 text-emerald-400" /> : <X size={13} className="mt-0.5 shrink-0 text-rose-400" />}
            <span>
              <span className={i.ok ? "text-[#d7deea]" : "font-semibold text-[#e8eef8]"}>{CHECK_LABEL[i.key] ?? i.key}</span>
              {!i.ok && i.hint && <span className="block text-[#9aa7bc]">{i.hint}</span>}
            </span>
          </li>
        ))}
      </ul>
      {check.norms.length > 0 && (
        <p className="flex flex-wrap gap-1">
          {check.norms.map((n, idx) => (
            <span key={`${n.citation}-${idx}`} title={n.found ? "im Gesetzeskorpus gefunden" : "nicht im Korpus – prüfen!"}
              className={`rounded-[3px] px-1.5 py-0.5 ${n.found ? "bg-emerald-900/50 text-emerald-200" : "bg-rose-900/60 text-rose-200"}`}>
              {n.found ? "✓" : "?"} {n.citation}
            </span>
          ))}
        </p>
      )}
    </div>
  )
}
