import { useState } from "react"
import { useTranslation } from "react-i18next"
import { CalendarSearch, MonitorPlay, Square } from "lucide-react"
import { vitrineApi, type Simulation } from "./api"

const field = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1.5 text-sm text-[#e8eef8]"

/** „Datum testen“: Was läuft zu diesem Zeitpunkt? Optional 30 s auf dem Display zeigen (Reiter Programm). */
export function SimulateCard() {
  const { t } = useTranslation("vitrine")
  const [at, setAt] = useState(() => `${new Date().getFullYear()}-12-24T19:00`)
  const [sim, setSim] = useState<Simulation | null>(null)
  const [simErr, setSimErr] = useState<string | null>(null)
  const [shown, setShown] = useState<string | null>(null)

  async function test() {
    setSimErr(null)
    try { setSim(await vitrineApi.simulate(at)) } catch (e) { setSim(null); setSimErr(e instanceof Error ? e.message : String(e)) }
  }

  async function showOnDisplay() {
    setSimErr(null)
    try {
      const [s, p] = await Promise.all([vitrineApi.simulate(at), vitrineApi.startPreview(at)])
      setSim(s); setShown(t("preview_running", { s: p.seconds }))
    } catch (e) { setShown(null); setSimErr(e instanceof Error ? e.message : String(e)) }
  }

  async function stopPreview() {
    try { await vitrineApi.stopPreview(); setShown(null) } catch (e) { setSimErr(e instanceof Error ? e.message : String(e)) }
  }

  return (
    <div className="space-y-3 rounded-[6px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-4">
      <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><CalendarSearch size={15} className="text-[#69d7ff]" />{t("simulate")}</h2>
      <p className="text-xs text-[#9aa7bc]">{t("simulate_hint")}</p>
      <div className="flex flex-wrap gap-2">
        <input type="datetime-local" className={field} value={at} onChange={(e) => setAt(e.target.value)} />
        <button type="button" onClick={() => void test()} className="rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-3 py-1 text-xs font-bold text-[#69d7ff]">{t("simulate_go")}</button>
        <button type="button" onClick={() => void showOnDisplay()} className="flex items-center gap-1 rounded-[4px] border border-amber-300/40 bg-amber-300/10 px-3 py-1 text-xs font-bold text-amber-200">
          <MonitorPlay size={13} />{t("preview_show")}
        </button>
        {shown && (
          <button type="button" onClick={() => void stopPreview()} className="flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-3 py-1 text-xs text-[#c8d2df]">
            <Square size={12} />{t("preview_stop")}
          </button>
        )}
      </div>
      {shown && <p className="text-xs text-amber-200">{shown}</p>}
      {simErr && <p className="text-xs text-rose-300">{simErr}</p>}
      {sim && <p className="text-sm text-[#c8d2df]">
        {sim.night ? t(`night_${sim.night}`) : sim.video ? t("simulate_result", { video: sim.video, rule: sim.rule ?? t("rule_none") }) : t("simulate_nothing")}
        {sim.holiday && <span className="ml-1 text-amber-200">({sim.holiday})</span>}
      </p>}
      <p className="text-xs text-[#5b6b82]">{t("simulate_saved_only")}</p>
    </div>
  )
}
