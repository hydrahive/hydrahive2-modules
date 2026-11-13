import { useTranslation } from "react-i18next"
import type { TvwDevice } from "./api"
import { actionView, canInstall, checkView, kindKey, ourHome } from "./deviceLogic"
import { deviceLine, errorKey } from "./logic"
import { BTN, BTN_DANGER, BTN_MAIN, ROW } from "./ui"

export interface DeviceActions {
  onAdd: (name: string, address: string) => void
  onCheck: (id: string) => void
  onRemove: (id: string) => void
  onInstall: (id: string) => void
  onRestore: (id: string) => void
}

/** Ein Fernseher: Angaben, laufende Aufträge, Fehler, Knöpfe (prüfen, aufspielen bzw. zurück, entfernen). */
export function DeviceRow({ d, busy, hasBuild, actions }: {
  d: TvwDevice; busy: boolean; hasBuild: boolean; actions: DeviceActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const check = checkView(d)
  const act = actionView(d)
  const running = check === "checking" || check === "authorize" || act === "installing" || act === "restoring"
  const kind = kindKey(d.kind)
  return (
    <div className={`${ROW} flex-col items-stretch`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm text-[#e8eef8]">{d.name}</div>
          <div className="truncate text-xs text-[#9aa7bc]">
            {[deviceLine(d), kind ? t(kind) : ""].filter(Boolean).join(" · ")}
          </div>
          {ourHome(d) && <div className="text-xs text-[#69d7ff]">{t("device.our_home")}</div>}
        </div>
        <div className="shrink-0 text-right text-xs text-[#9aa7bc]">
          <div>{d.address}</div>
          <div>{t(`adb.${d.adb_state ?? "unknown"}`)}</div>
        </div>
      </div>
      {check === "checking" && <p className="text-xs text-[#69d7ff]" role="status">{t("device.checking")}</p>}
      {check === "authorize" && (
        <p className="rounded bg-amber-500/10 p-2 text-sm text-amber-200" role="status">{t("device.authorize")}</p>
      )}
      {act === "installing" && (
        <p className="text-xs text-[#69d7ff]" role="status">
          {t("install.running", { step: t(`istep.${d.action?.step}`) })}
        </p>
      )}
      {act === "restoring" && <p className="text-xs text-[#69d7ff]" role="status">{t("install.restoring")}</p>}
      {check === "failed" && d.check && (
        <p className="text-xs text-red-300" role="alert">{t(errorKey(d.check.error_code))}</p>
      )}
      {act === "failed" && d.action && (
        <p className="text-xs text-red-300" role="alert">{t(errorKey(d.action.error_code))}</p>
      )}
      {!running && (
        <div className="flex flex-wrap gap-2">
          {!ourHome(d) && (
            <button type="button" className={BTN_MAIN} disabled={busy || !canInstall(d, hasBuild)}
              onClick={() => actions.onInstall(d.device_id)}>{t("install.start")}</button>
          )}
          {ourHome(d) && d.stock_home && (
            <button type="button" className={BTN} disabled={busy} onClick={() => actions.onRestore(d.device_id)}>
              {t("install.restore")}
            </button>
          )}
          <button type="button" className={BTN} disabled={busy} onClick={() => actions.onCheck(d.device_id)}>
            {t("device.check")}
          </button>
          <button type="button" className={BTN_DANGER} disabled={busy} onClick={() => actions.onRemove(d.device_id)}>
            {t("device.remove")}
          </button>
        </div>
      )}
      {!running && !ourHome(d) && !hasBuild && <p className="text-xs text-[#9aa7bc]">{t("install.need_build")}</p>}
    </div>
  )
}
