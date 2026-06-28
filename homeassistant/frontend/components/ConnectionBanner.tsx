import { AlertTriangle, CheckCircle2 } from "lucide-react"
import type { HATestResult } from "../api"

interface Props {
  test: HATestResult | null
  error: string | null
}

export function ConnectionBanner({ test, error }: Props) {
  if (error) {
    return (
      <div className="flex items-start gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-300">
        <AlertTriangle size={16} className="mt-0.5 shrink-0" />
        <div>
          <div className="font-medium">Keine Verbindung zu Home Assistant</div>
          <div className="text-rose-400/80 text-[13px] mt-0.5">{error}</div>
          <div className="text-rose-400/60 text-[12px] mt-1">
            URL und Token unter System → Einstellungen → Home Assistant prüfen.
          </div>
        </div>
      </div>
    )
  }
  if (test?.ok) {
    const cfg = test.config
    return (
      <div className="flex items-center gap-2 rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-2.5 text-sm text-emerald-300">
        <CheckCircle2 size={16} className="shrink-0" />
        <span>
          Verbunden{cfg?.location_name ? ` mit ${cfg.location_name}` : ""}
          {cfg?.version ? ` · HA ${cfg.version}` : ""}
        </span>
      </div>
    )
  }
  return null
}
