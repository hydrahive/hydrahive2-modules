import { useTranslation } from "react-i18next"
import type { Rig } from "../api"
import { formatHashrate } from "../format"
import { activity, stopReasonKey } from "../rigState"

/** Zeile 2 einer Rig-Zeile: Was tut der Rechner gerade? */
export function RigActivity({ rig, benchTotal }: { rig: Rig; benchTotal: number }) {
  const { t } = useTranslation("mining")
  const a = activity(rig, benchTotal)
  const rep = rig.last_report
  if (a.kind === "stopped") {
    return <span className="text-zinc-500">{t(stopReasonKey(a.reason))}</span>
  }
  const hr = formatHashrate(rep?.hashrate)
  const shares = rep?.accepted ? ` · ${t("shares", { n: rep.accepted })}` : ""
  const err = rep?.error ? <span className="ml-2 text-rose-300">{rep.error}</span> : null
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
