import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { miningApi, type MiningConfig, type PowerStatus } from "../api"

interface Props {
  config: MiningConfig
  canEdit: boolean
  onSave: (c: Partial<MiningConfig>) => Promise<void>
}

const input = "w-full rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 disabled:opacity-50"
const POWER_KEYS = ["power_mode", "power_fixed_w", "power_url", "power_field", "power_scale", "power_reserve_w",
  "power_min_minutes", "power_stale_minutes"] as const
type PowerDraft = Pick<MiningConfig, (typeof POWER_KEYS)[number]>
const pick = (c: MiningConfig): PowerDraft => Object.fromEntries(POWER_KEYS.map((k) => [k, c[k]])) as PowerDraft

/** Energie-Steuerung: Rechner mit „folgt Energie“ laufen nur, solange genug Leistung da ist (z. B. PV-Überschuss). */
export function PowerPanel({ config, canEdit, onSave }: Props) {
  const { t } = useTranslation("mining")
  const [draft, setDraft] = useState<PowerDraft>(pick(config))
  const [busy, setBusy] = useState(false)
  const [live, setLive] = useState<PowerStatus | null>(null)
  const set = <K extends keyof PowerDraft>(k: K, v: PowerDraft[K]) => setDraft((d) => ({ ...d, [k]: v }))
  const dirty = JSON.stringify(draft) !== JSON.stringify(pick(config))

  useEffect(() => {
    let alive = true
    const load = () => miningApi.power().then((s) => { if (alive) setLive(s) }).catch(() => undefined)
    load()
    const id = window.setInterval(load, 15_000)
    return () => { alive = false; window.clearInterval(id) }
  }, [config.power_mode])

  const save = async () => {
    setBusy(true)
    try { await onSave(draft) } finally { setBusy(false) }
  }
  const num = (k: keyof PowerDraft, min: number, max: number, step = 1) => (
    <input type="number" className={input} disabled={!canEdit} min={min} max={max} step={step}
      value={draft[k] as number} onChange={(e) => set(k, Number(e.target.value) as never)} />
  )

  return (
    <div className="space-y-3 rounded-xl border border-white/10 bg-zinc-900/40 p-4">
      <div className="flex items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-zinc-200">{t("power_title")}</h2>
        {live && live.mode !== "off" && (
          <span className={`text-xs ${live.available_w === null ? "text-rose-300" : "text-emerald-300"}`}>
            {live.available_w === null ? t("power_no_data") : t("power_available", { w: Math.round(live.available_w) })}
          </span>
        )}
      </div>
      <p className="text-xs text-zinc-500">{t("power_hint")}</p>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1 text-xs text-zinc-400 sm:col-span-2">
          <span>{t("power_mode")}</span>
          <select className={input} disabled={!canEdit} value={draft.power_mode}
            onChange={(e) => set("power_mode", e.target.value as PowerDraft["power_mode"])}>
            {(["off", "fixed", "http"] as const).map((m) => <option key={m} value={m}>{t(`power_mode_${m}`)}</option>)}
          </select>
        </label>
        {draft.power_mode === "fixed" && (
          <label className="space-y-1 text-xs text-zinc-400">
            <span>{t("power_fixed_w")}</span>{num("power_fixed_w", 0, 1_000_000, 50)}
          </label>
        )}
        {draft.power_mode === "http" && (
          <>
            <label className="space-y-1 text-xs text-zinc-400 sm:col-span-2">
              <span>{t("power_url")}</span>
              <input className={input} disabled={!canEdit} value={draft.power_url} maxLength={300}
                placeholder="http://192.168.178.50/api/surplus" onChange={(e) => set("power_url", e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-zinc-400">
              <span>{t("power_field")}</span>
              <input className={input} disabled={!canEdit} value={draft.power_field} maxLength={100}
                placeholder="data.surplus_w" onChange={(e) => set("power_field", e.target.value)} />
            </label>
            <label className="space-y-1 text-xs text-zinc-400">
              <span>{t("power_scale")}</span>{num("power_scale", 0.000001, 1_000_000, 0.001)}
            </label>
            <label className="space-y-1 text-xs text-zinc-400">
              <span>{t("power_stale")}</span>{num("power_stale_minutes", 1, 240)}
            </label>
          </>
        )}
        {draft.power_mode !== "off" && (
          <>
            <label className="space-y-1 text-xs text-zinc-400">
              <span>{t("power_reserve")}</span>{num("power_reserve_w", 0, 100_000, 10)}
            </label>
            <label className="space-y-1 text-xs text-zinc-400">
              <span>{t("power_min_minutes")}</span>{num("power_min_minutes", 1, 240)}
            </label>
          </>
        )}
      </div>
      {canEdit && (
        <button onClick={save} disabled={!dirty || busy}
          className="rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white hover:bg-emerald-500 disabled:opacity-40">
          {t("save")}
        </button>
      )}
    </div>
  )
}
