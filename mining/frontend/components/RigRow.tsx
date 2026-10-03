import { useTranslation } from "react-i18next"
import type { Rig } from "../api"
import { BADGE_CLASS, rigBadge } from "../rigState"

interface Props {
  rig: Rig
  canControl: boolean
  onApprove: (id: string) => void
  onRevoke: (id: string) => void
  onToggle: (id: string, enabled: boolean) => void
  onRemove: (id: string) => void
}

const btn = "rounded-md px-2 py-1 text-xs hover:bg-white/10"

export function RigRow({ rig, canControl, onApprove, onRevoke, onToggle, onRemove }: Props) {
  const { t } = useTranslation("mining")
  const badge = rigBadge(rig)
  const live = rig.last_report
  const fmt = (v: number | null | undefined, unit: string) => (v === null || v === undefined ? "—" : `${Math.round(v)} ${unit}`)

  return (
    <tr className="align-top">
      <td className="px-3 py-2">
        <div className="font-medium text-zinc-100">{rig.name}</div>
        <div className="text-xs text-zinc-500">{rig.hostname ?? "—"} · {rig.remote_ip ?? "—"}</div>
      </td>
      <td className="px-3 py-2"><span className={`rounded px-1.5 py-0.5 text-xs ${BADGE_CLASS[badge]}`}>{t(`badge_${badge}`)}</span></td>
      <td className="px-3 py-2 text-zinc-300">
        <div>{rig.gpu_model ?? "—"}</div>
        <div className="text-xs text-zinc-500">{rig.gpu_mem_mb ? `${Math.round(rig.gpu_mem_mb / 1024)} GB` : ""} {rig.driver ? `· ${rig.driver}` : ""}</div>
      </td>
      <td className="px-3 py-2 text-right text-zinc-300">{fmt(live?.temp_c, "°C")}</td>
      <td className="px-3 py-2 text-right text-zinc-300">{fmt(live?.power_w, "W")}</td>
      <td className="px-3 py-2 text-right text-zinc-300">{fmt(live?.util_pct, "%")}</td>
      <td className="px-3 py-2 text-xs text-zinc-500">{rig.os ?? "—"}<br />v{rig.client_version ?? "?"}</td>
      {canControl && (
        <td className="space-x-1 whitespace-nowrap px-3 py-2 text-right">
          {rig.status === "pending" && <button className={`${btn} text-emerald-300`} onClick={() => onApprove(rig.id)}>{t("approve")}</button>}
          {rig.status === "active" && (
            <button className={`${btn} text-zinc-300`} onClick={() => onToggle(rig.id, !rig.enabled)}>{rig.enabled ? t("turn_off") : t("turn_on")}</button>
          )}
          {rig.status !== "revoked" && <button className={`${btn} text-rose-300`} onClick={() => onRevoke(rig.id)}>{t("revoke")}</button>}
          {rig.status === "revoked" && <button className={`${btn} text-zinc-400`} onClick={() => onRemove(rig.id)}>{t("remove")}</button>}
        </td>
      )}
    </tr>
  )
}
