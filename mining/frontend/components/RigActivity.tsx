import { useTranslation } from "react-i18next"
import type { Rig } from "../api"
import { formatHashrate } from "../format"
import { type Activity, activityLines, stopReasonKey } from "../rigState"

const VENDOR_LABEL: Record<string, string> = { nvidia: "NVIDIA", amd: "AMD" }

/** Zeile 2 einer Rig-Zeile: Was tut der Rechner gerade? Gemischte Rechner: je Hersteller eine Zeile. */
export function RigActivity({ rig }: { rig: Rig }) {
  const rep = rig.last_report
  const lines = activityLines(rig)
  return (
    <div className="space-y-0.5">
      {lines.map((l) => (
        <div key={l.vendor ?? "all"}>
          {l.vendor && <span className="mr-1.5 rounded bg-white/10 px-1 text-[10px] text-zinc-300">{VENDOR_LABEL[l.vendor] ?? l.vendor}</span>}
          <Line a={l.activity} hashrate={l.hashrate} accepted={l.vendor ? null : rep?.accepted} error={l.vendor ? null : rep?.error} />
        </div>
      ))}
    </div>
  )
}

function Line({ a, hashrate, accepted, error }: {
  a: Activity; hashrate: number | null | undefined; accepted?: number | null; error?: string | null
}) {
  const { t } = useTranslation("mining")
  if (a.kind === "stopped") {
    return <span className="text-zinc-500">{t(stopReasonKey(a.reason))}</span>
  }
  const hr = formatHashrate(hashrate)
  const shares = accepted ? ` · ${t("shares", { n: accepted })}` : ""
  const err = error ? <span className="ml-2 text-rose-300">{error}</span> : null
  if (a.kind === "benchmark") {
    return (
      <span className="text-amber-300">
        {t("benchmarking", { done: Math.min(a.done, a.total), total: a.total })}: {a.coin.toUpperCase()} ({a.miner}) · {hr}{err}
      </span>
    )
  }
  return (
    <span className="text-emerald-300">
      ⛏ {a.coin.toUpperCase()} ({a.miner}) · {hr}{shares}{err}
    </span>
  )
}
