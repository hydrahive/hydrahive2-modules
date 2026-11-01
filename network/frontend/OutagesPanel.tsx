import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { getOutages, getOverview, getSpeedtests, type Outages } from "./api"
import type { Speedtest } from "./logic"
import { OutagesView } from "./OutagesView"
import { INPUT } from "./ui"

const RANGES = [7, 30, 90]

export function OutagesPanel() {
  const { t } = useTranslation("network")
  const [days, setDays] = useState(30)
  const [d, setD] = useState<Outages | null>(null)
  const [st, setSt] = useState<Speedtest[]>([])
  const [planUp, setPlanUp] = useState<number | null>(null)
  useEffect(() => {
    Promise.all([getOutages(days), getSpeedtests(days), getOverview()])
      .then(([o, s, ov]) => { setD(o); setSt(s.items); setPlanUp(ov.plan.up) }).catch(() => {})
  }, [days])
  return (
    <div className="space-y-4">
      <label className="flex items-center gap-2 text-sm text-[#c8d2df]">
        {t("outages.range")}
        <select value={days} onChange={(e) => setDays(Number(e.target.value))} className={`${INPUT} w-auto`}>
          {RANGES.map((n) => <option key={n} value={n}>{t("outages.days", { n })}</option>)}
        </select>
      </label>
      {d ? <OutagesView d={d} speedtests={st} planUp={planUp} /> : <p className="text-sm text-[#c8d2df]">{t("loading")}</p>}
    </div>
  )
}
