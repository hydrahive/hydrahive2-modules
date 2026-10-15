import { useState } from "react"
import { useTranslation } from "react-i18next"
import { CalendarSearch, MoonStar } from "lucide-react"
import { vitrineApi, type Simulation, type VitrineConfig } from "./api"

const field = "rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1.5 text-sm text-[#e8eef8]"

/** Nachtmodus, Wechselintervall und „Datum testen“ (was läuft an Heiligabend?). */
export function SettingsCard({ config, onChange }: { config: VitrineConfig; onChange: (c: VitrineConfig) => void }) {
  const { t } = useTranslation("vitrine")
  const n = config.night
  const setNight = (patch: Partial<VitrineConfig["night"]>) => onChange({ ...config, night: { ...n, ...patch } })
  const [at, setAt] = useState(() => `${new Date().getFullYear()}-12-24T19:00`)
  const [sim, setSim] = useState<Simulation | null>(null)
  const [simErr, setSimErr] = useState<string | null>(null)

  async function test() {
    setSimErr(null)
    try { setSim(await vitrineApi.simulate(at)) } catch (e) { setSim(null); setSimErr(e instanceof Error ? e.message : String(e)) }
  }

  return (
    <section className="grid gap-4 md:grid-cols-2">
      <div className="space-y-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
        <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><MoonStar size={15} className="text-[#69d7ff]" />{t("night")}</h2>
        <label className="flex items-center gap-2 text-sm text-[#c8d2df]"><input type="checkbox" checked={n.enabled} onChange={() => setNight({ enabled: !n.enabled })} />{t("night_enabled")}</label>
        <div className="flex flex-wrap items-center gap-2 text-sm text-[#8d9ab0]">
          {t("from_hm")} <input type="time" className={field} value={n.from} onChange={(e) => setNight({ from: e.target.value })} disabled={!n.enabled} />
          {t("to_hm")} <input type="time" className={field} value={n.to} onChange={(e) => setNight({ to: e.target.value })} disabled={!n.enabled} />
        </div>
        <div className="flex gap-4 text-sm text-[#c8d2df]">
          {(["dim", "off"] as const).map((m) => (
            <label key={m} className="flex items-center gap-1.5"><input type="radio" name="night-mode" checked={n.mode === m} onChange={() => setNight({ mode: m })} disabled={!n.enabled} />{t(`night_${m}`)}</label>
          ))}
        </div>
        <label className="block text-xs text-[#8d9ab0]">{t("rotate")}
          <input type="number" min={0} max={1440} className={`${field} ml-2 w-20`} value={config.rotate_minutes}
            onChange={(e) => onChange({ ...config, rotate_minutes: Math.max(0, Number(e.target.value)) })} />
        </label>
      </div>

      <div className="space-y-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
        <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><CalendarSearch size={15} className="text-[#69d7ff]" />{t("simulate")}</h2>
        <p className="text-xs text-[#718097]">{t("simulate_hint")}</p>
        <div className="flex flex-wrap gap-2">
          <input type="datetime-local" className={field} value={at} onChange={(e) => setAt(e.target.value)} />
          <button type="button" onClick={() => void test()} className="rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-3 py-1 text-xs font-bold text-[#69d7ff]">{t("simulate_go")}</button>
        </div>
        {simErr && <p className="text-xs text-rose-300">{simErr}</p>}
        {sim && <p className="text-sm text-[#c8d2df]">
          {sim.night ? t(`night_${sim.night}`) : sim.video ? t("simulate_result", { video: sim.video, rule: sim.rule ?? t("rule_none") }) : t("simulate_nothing")}
          {sim.holiday && <span className="ml-1 text-amber-200">({sim.holiday})</span>}
        </p>}
        <p className="text-xs text-[#5b6b82]">{t("simulate_saved_only")}</p>
      </div>
    </section>
  )
}
