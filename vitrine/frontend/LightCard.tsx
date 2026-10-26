import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Lightbulb } from "lucide-react"
import { vitrineApi } from "./api"
import { LIGHT_SEASONS, LIGHT_STATES, lightErrors, normalizeLight, toPicker, type LightCfg, type LightStatus } from "./light"
import { LightLookRow, type LookValue } from "./LightLookRow"

const field = "rounded-[4px] border border-[#2a364b] bg-[#0d1420] px-2 py-1 text-xs text-[#e8eef8]"
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, Math.round(v)))

/** S8: Mainboard-Licht – Schalter, Helligkeit, Farbe je Zustand und Jahreszeit, Vorschau, aktueller Stand. */
export function LightCard({ light: raw, onChange }: { light: LightCfg | undefined; onChange: (l: LightCfg) => void }) {
  const { t } = useTranslation("vitrine")
  const light = normalizeLight(raw)
  const errs = lightErrors(light)
  const [st, setSt] = useState<LightStatus | null>(null)
  const [msg, setMsg] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    const load = () => vitrineApi.light().then((s) => { if (alive) setSt(s) }).catch(() => {})
    load()
    const id = window.setInterval(load, 5000)
    return () => { alive = false; window.clearInterval(id) }
  }, [])

  const set = (patch: Partial<LightCfg>) => onChange({ ...light, ...patch })
  const setState = (s: (typeof LIGHT_STATES)[number], v: LookValue & { enabled?: boolean; seconds?: number }) =>
    set({ states: { ...light.states, [s]: { ...light.states[s], ...v } } })
  const preview = async (state: string) => {
    setMsg(null)
    try { const r = await vitrineApi.lightPreview(state); setMsg(t("light_preview_running", { s: r.seconds })) }
    catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
  }

  return (
    <section className="space-y-3 rounded-[6px] border border-[#2a364b] bg-[#111827] p-4">
      <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><Lightbulb size={15} className="text-[#69d7ff]" />{t("light_title")}</h2>
      <p className="text-xs text-[#718097]">{t("light_hint")}</p>

      <div className="flex flex-wrap items-center gap-2 rounded-[4px] bg-[#0d1420] px-3 py-2 text-xs text-[#c8d2df]">
        {!st?.available ? <span className="text-[#718097]">{t("light_no_status")}</span> : <>
          <span className="h-3 w-3 rounded-full border border-white/20" style={{ background: st.effect === "off" || !st.color ? "#000" : toPicker(st.color) }} />
          <span>{st.device ?? t("light_no_device")}</span>
          {st.state && <span className="text-[#8d9ab0]">· {t(`light_state_${st.state}`, { defaultValue: st.state })}{st.label ? ` (${st.label})` : ""}</span>}
          {st.preview && <span className="text-amber-200">· {t("light_preview")}</span>}
          {st.error && <span className="text-rose-300">· {st.error}</span>}
        </>}
      </div>

      <div className="flex flex-wrap items-center gap-4 text-sm text-[#c8d2df]">
        <label className="flex items-center gap-2"><input type="checkbox" checked={light.enabled} onChange={() => set({ enabled: !light.enabled })} />{t("light_enabled")}</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={light.night_off} onChange={() => set({ night_off: !light.night_off })} />{t("light_night_off")}</label>
        <label className="flex items-center gap-2 text-xs text-[#8d9ab0]">{t("light_brightness")}
          <input type="range" min={0} max={100} value={light.brightness} onChange={(e) => set({ brightness: Number(e.target.value) })} />
          <span className="w-9 text-right text-[#e8eef8]">{light.brightness} %</span>
        </label>
      </div>

      <fieldset disabled={!light.enabled} className="space-y-1.5 disabled:opacity-50">
        <legend className="mb-1 text-xs font-bold text-[#8d9ab0]">{t("light_states")}</legend>
        {LIGHT_STATES.map((s) => (
          <LightLookRow key={s} title={t(`light_state_${s}`)} value={light.states[s]} withSpeed withBrightness bad={errs.includes(`states.${s}`)}
            onChange={(v) => setState(s, v)} onPreview={() => void preview(s)}>
            {s === "error" && <label className="flex items-center gap-1 text-[11px] text-[#8d9ab0]">{t("light_blink_seconds")}
              <input type="number" min={0} max={600} className={`${field} w-16`} value={light.error_blink_seconds}
                onChange={(e) => set({ error_blink_seconds: clamp(Number(e.target.value), 0, 600) })} /></label>}
            {s === "done" && <>
              <label className="flex items-center gap-1 text-[11px] text-[#8d9ab0]"><input type="checkbox" checked={!!light.states.done.enabled}
                onChange={() => setState("done", { ...light.states.done, enabled: !light.states.done.enabled })} />{t("light_done_on")}</label>
              <label className="flex items-center gap-1 text-[11px] text-[#8d9ab0]">{t("light_done_seconds")}
                <input type="number" min={2} max={60} className={`${field} w-14`} value={light.states.done.seconds ?? 5}
                  onChange={(e) => setState("done", { ...light.states.done, seconds: clamp(Number(e.target.value), 2, 60) })} /></label>
            </>}
          </LightLookRow>
        ))}
      </fieldset>

      <fieldset disabled={!light.enabled} className="space-y-1.5 disabled:opacity-50">
        <legend className="mb-1 flex items-center gap-2 text-xs font-bold text-[#8d9ab0]">
          <input type="checkbox" checked={light.seasons_enabled} onChange={() => set({ seasons_enabled: !light.seasons_enabled })} />{t("light_seasons")}
        </legend>
        {light.seasons_enabled
          ? LIGHT_SEASONS.map((s) => (
            <LightLookRow key={s} title={t(`season.${s}`)} value={light.seasons[s]} bad={errs.includes(`seasons.${s}`)}
              onChange={(v) => set({ seasons: { ...light.seasons, [s]: { effect: v.effect, color: v.color } } })} onPreview={() => void preview(s)} />))
          : <LightLookRow title={t("light_rest")} value={{ effect: light.rest_effect, color: light.rest_color }} bad={errs.includes("rest")}
              onChange={(v) => set({ rest_effect: v.effect, rest_color: v.color })} onPreview={() => void preview("rest")} />}
        <p className="text-[11px] text-[#5b6b82]">{t("light_occasion_hint")}</p>
      </fieldset>

      {msg && <p className="text-xs text-amber-200">{msg}</p>}
      {errs.length > 0 && <p className="text-xs text-rose-300">{t("light_invalid")}</p>}
      <p className="text-xs text-[#5b6b82]">{t("simulate_saved_only")}</p>
    </section>
  )
}
