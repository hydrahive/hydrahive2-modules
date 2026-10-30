import { useTranslation } from "react-i18next"
import { MoonStar } from "lucide-react"
import type { VitrineConfig } from "./api"
import { clamp } from "./rules"

const field = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1.5 text-sm text-[#e8eef8]"

/** Reiter Anzeige: Nachtmodus, Wechselintervall, Bildrate, Einblendungsdauer, Rückkehr zum Video. */
export function SettingsCard({ config, onChange }: { config: VitrineConfig; onChange: (c: VitrineConfig) => void }) {
  const { t } = useTranslation("vitrine")
  const n = config.night
  const setNight = (patch: Partial<VitrineConfig["night"]>) => onChange({ ...config, night: { ...n, ...patch } })
  return (
    <section className="max-w-2xl">
      <div className="space-y-3 rounded-[6px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-4">
        <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><MoonStar size={15} className="text-[#69d7ff]" />{t("night")}</h2>
        <label className="flex items-center gap-2 text-sm text-[#c8d2df]"><input type="checkbox" checked={n.enabled} onChange={() => setNight({ enabled: !n.enabled })} />{t("night_enabled")}</label>
        <div className="flex flex-wrap items-center gap-2 text-sm text-[#9aa7bc]">
          {t("from_hm")} <input type="time" className={field} value={n.from} onChange={(e) => setNight({ from: e.target.value })} disabled={!n.enabled} />
          {t("to_hm")} <input type="time" className={field} value={n.to} onChange={(e) => setNight({ to: e.target.value })} disabled={!n.enabled} />
        </div>
        <div className="flex gap-4 text-sm text-[#c8d2df]">
          {(["dim", "off"] as const).map((m) => (
            <label key={m} className="flex items-center gap-1.5"><input type="radio" name="night-mode" checked={n.mode === m} onChange={() => setNight({ mode: m })} disabled={!n.enabled} />{t(`night_${m}`)}</label>
          ))}
        </div>
        <label className="block text-xs text-[#9aa7bc]">{t("rotate")}
          <input type="number" min={0} max={1440} className={`${field} ml-2 w-20`} value={config.rotate_minutes}
            onChange={(e) => onChange({ ...config, rotate_minutes: Math.max(0, Number(e.target.value)) })} />
        </label>
        <label className="block text-xs text-[#9aa7bc]">{t("fps_label")}
          <input type="number" min={12} max={30} className={`${field} ml-2 w-20`} value={config.fps}
            onChange={(e) => onChange({ ...config, fps: clamp(Number(e.target.value), 12, 30) })} />
          <span className="ml-2 text-[#5b6b82]">{t("fps_hint")}</span>
        </label>
        <label className="block text-xs text-[#9aa7bc]">{t("message_seconds_label")}
          <input type="number" min={5} max={120} className={`${field} ml-2 w-20`} value={config.message_seconds}
            onChange={(e) => onChange({ ...config, message_seconds: clamp(Number(e.target.value), 5, 120) })} />
        </label>
        <label className="block text-xs text-[#9aa7bc]">{t("dashboard_return_label")}
          <input type="number" min={30} max={1800} className={`${field} ml-2 w-20`} value={config.dashboard_return_seconds ?? 120}
            onChange={(e) => onChange({ ...config, dashboard_return_seconds: clamp(Number(e.target.value), 30, 1800) })} />
          <span className="ml-2 text-[#5b6b82]">{t("dashboard_return_hint")}</span>
        </label>
      </div>
    </section>
  )
}
