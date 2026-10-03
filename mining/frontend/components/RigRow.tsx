import { useTranslation } from "react-i18next"
import type { Rig } from "../api"
import { BADGE_CLASS, rigBadge, rigCards, sensorHint } from "../rigState"
import { RigActivity } from "./RigActivity"
import { RigCards } from "./RigCards"

interface Props {
  rig: Rig
  canControl: boolean
  benchTotal: number
  powerActive: boolean
  onApprove: (id: string) => void
  onRevoke: (id: string) => void
  onToggle: (id: string, enabled: boolean) => void
  onRemove: (id: string) => void
  onRebench: (id: string) => void
  onFollowPower: (id: string, follows: boolean, priority: number) => void
}

const btn = "rounded-md px-2 py-1 text-xs hover:bg-white/10"

export function RigRow({ rig, canControl, benchTotal, powerActive, onApprove, onRevoke, onToggle, onRemove,
  onRebench, onFollowPower }: Props) {
  const { t } = useTranslation("mining")
  const badge = rigBadge(rig)
  const live = rig.last_report
  const cards = rigCards(rig)
  const hint = sensorHint(cards)
  const fmt = (v: number | null | undefined, unit: string) => (v === null || v === undefined ? "—" : `${Math.round(v)} ${unit}`)

  return (
    <tr className="align-top">
      <td className="px-3 py-2">
        <div className="font-medium text-zinc-100">{rig.name}</div>
        <div className="text-xs text-zinc-500">{rig.hostname ?? "—"} · {rig.remote_ip ?? "—"}</div>
        {rig.status === "active" && <div className="mt-1 text-xs"><RigActivity rig={rig} benchTotal={benchTotal} /></div>}
      </td>
      <td className="px-3 py-2"><span className={`rounded px-1.5 py-0.5 text-xs ${BADGE_CLASS[badge]}`}>{t(`badge_${badge}`)}</span></td>
      <td className="px-3 py-2 text-zinc-300">
        <div>{rig.gpu_model ?? "—"}</div>
        <div className="text-xs text-zinc-500">{rig.gpu_mem_mb ? `${Math.round(rig.gpu_mem_mb / 1024)} GB` : ""} {rig.driver ? `· ${rig.driver}` : ""}</div>
        {hint && <div className="text-xs text-amber-300" title={t(`sensors_${hint}_hint`)}>{t(`sensors_${hint}`)}</div>}
        <RigCards cards={cards} />
      </td>
      <td className="px-3 py-2 text-right text-zinc-300">{fmt(live?.temp_c, "°C")}</td>
      <td className="px-3 py-2 text-right text-zinc-300">{fmt(live?.power_w, "W")}</td>
      <td className="px-3 py-2 text-right text-zinc-300">{fmt(live?.util_pct, "%")}</td>
      <td className="px-3 py-2 text-xs text-zinc-500">{rig.os ?? "—"}<br />v{rig.client_version ?? "?"}</td>
      {canControl && (
        <td className="space-x-1 whitespace-nowrap px-3 py-2 text-right">
          {rig.status === "pending" && <button className={`${btn} text-emerald-300`} onClick={() => onApprove(rig.id)}>{t("approve")}</button>}
          {rig.status === "active" && (
            <>
              <button className={`${btn} text-zinc-300`} onClick={() => onToggle(rig.id, !rig.enabled)}>{rig.enabled ? t("turn_off") : t("turn_on")}</button>
              <button className={`${btn} text-zinc-400`} title={t("rebench_hint")} onClick={() => onRebench(rig.id)}>{t("rebench")}</button>
              {powerActive && (
                <label className="inline-flex items-center gap-1 text-xs text-zinc-400" title={t("follows_power_hint")}>
                  <input type="checkbox" checked={!!rig.follows_power}
                    onChange={(e) => onFollowPower(rig.id, e.target.checked, rig.priority)} />
                  {t("follows_power")}
                </label>
              )}
            </>
          )}
          {rig.status !== "revoked" && <button className={`${btn} text-rose-300`} onClick={() => onRevoke(rig.id)}>{t("revoke")}</button>}
          {rig.status === "revoked" && <button className={`${btn} text-zinc-400`} onClick={() => onRemove(rig.id)}>{t("remove")}</button>}
        </td>
      )}
    </tr>
  )
}
