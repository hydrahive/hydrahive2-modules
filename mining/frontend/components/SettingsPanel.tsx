import { useState } from "react"
import { useTranslation } from "react-i18next"
import { REGIONS, type MiningConfig } from "../api"
import { userHasWorkerSuffix } from "../rigState"

interface Props {
  config: MiningConfig
  canEdit: boolean
  onSave: (c: Partial<MiningConfig>) => Promise<void>
}

const input = "w-full rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-3 py-2 text-sm text-[#e8eef8] disabled:opacity-50"

export function SettingsPanel({ config, canEdit, onSave }: Props) {
  const { t } = useTranslation("mining")
  const [draft, setDraft] = useState<MiningConfig>(config)
  const [busy, setBusy] = useState(false)
  const set = <K extends keyof MiningConfig>(k: K, v: MiningConfig[K]) => setDraft((d) => ({ ...d, [k]: v }))
  const dirty = JSON.stringify(draft) !== JSON.stringify(config)

  const save = async () => {
    setBusy(true)
    try { await onSave(draft) } finally { setBusy(false) }
  }

  return (
    <div className="space-y-3 rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.4)] p-4">
      <h2 className="text-sm font-semibold text-[#e8eef8]">{t("settings")}</h2>
      <div className="grid gap-3 sm:grid-cols-2">
        <label className="space-y-1 text-xs text-[#c8d2df]">
          <span>{t("kryptex_user")}</span>
          <input className={input} disabled={!canEdit} value={draft.kryptex_user} maxLength={128}
            placeholder={t("kryptex_user_ph")} onChange={(e) => set("kryptex_user", e.target.value)} />
          {userHasWorkerSuffix(draft.kryptex_user) && <span className="block text-amber-300">{t("user_has_worker")}</span>}
        </label>
        <label className="space-y-1 text-xs text-[#c8d2df]">
          <span>{t("region")}</span>
          <select className={input} disabled={!canEdit} value={draft.region} onChange={(e) => set("region", e.target.value)}>
            {REGIONS.map((r) => <option key={r} value={r}>{t(`region_${r}`)}</option>)}
          </select>
        </label>
        <label className="space-y-1 text-xs text-[#c8d2df]">
          <span>{t("switch_threshold")}</span>
          <input type="number" className={input} disabled={!canEdit} min={0} max={100} step={1}
            value={Math.round(draft.switch_threshold * 100)}
            onChange={(e) => set("switch_threshold", Number(e.target.value) / 100)} />
        </label>
        <label className="space-y-1 text-xs text-[#c8d2df]">
          <span>{t("min_runtime")}</span>
          <input type="number" className={input} disabled={!canEdit} min={1} max={1440}
            value={draft.min_runtime_min} onChange={(e) => set("min_runtime_min", Number(e.target.value))} />
        </label>
        <label className="space-y-1 text-xs text-[#c8d2df] sm:col-span-2">
          <span>{t("prop_discount")}</span>
          <input type="number" className={input} disabled={!canEdit} min={0} max={50} step={1}
            value={Math.round(draft.prop_discount * 100)}
            onChange={(e) => set("prop_discount", Number(e.target.value) / 100)} />
        </label>
        <label className="flex items-center gap-2 text-xs text-[#c8d2df] sm:col-span-2">
          <input type="checkbox" disabled={!canEdit} checked={draft.clore_dryrun}
            onChange={(e) => set("clore_dryrun", e.target.checked)} />
          <span>{t("clore_switch")}</span>
        </label>
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
