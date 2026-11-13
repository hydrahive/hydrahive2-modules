import { useTranslation } from "react-i18next"
import type { TvwAppApk, TvwJob } from "./api"
import type { AppDeviceActions } from "./AppDevicesPanel"
import { appBuildStep, appBuildView } from "./appLogic"
import { shortHash, sizeText } from "./buildLogic"
import { errorKey } from "./logic"
import { BTN, BTN_MAIN, MUTED } from "./ui"

/** App bauen (im Container) und herunterladen (zum Aufspielen von Hand, z. B. auf Tablets). */
export function AppBuildBox({ job, apk, ready, busy, actions }: {
  job: TvwJob | null; apk: TvwAppApk | null; ready: boolean; busy: boolean
  actions: Pick<AppDeviceActions, "onBuild" | "onDownload">
}) {
  const { t } = useTranslation("tvwerkstatt")
  const view = appBuildView(job, !!apk)
  const s = appBuildStep(job?.step ?? "")
  return (
    <div className="space-y-2 rounded border border-[rgb(var(--hh-s-rand,52_66_92))] p-3">
      {view === "running" && (
        <p className="text-sm text-[#69d7ff]" role="status">
          {t("app.build_running", { n: s.n, total: s.total })} · {t(`app.bstep.${job?.step}`, { defaultValue: "" })}
        </p>
      )}
      {view === "failed" && <p className="text-sm text-red-300" role="alert">{t(errorKey(job?.error_code))}</p>}
      {apk && (
        <p className="text-xs text-[#9aa7bc]">
          {t("app.built", { v: apk.version })} · {sizeText(apk.size)} · {t("build.hash", { h: shortHash(apk.sha256) })}
        </p>
      )}
      {!apk && view !== "running" && <p className={MUTED}>{t(ready ? "app.build_none" : "app.build_need_setup")}</p>}
      <div className="flex flex-wrap gap-2">
        <button type="button" className={apk ? BTN : BTN_MAIN} disabled={busy || !ready || view === "running"}
          onClick={actions.onBuild}>{t(apk ? "app.build_again" : "app.build")}</button>
        {apk && <button type="button" className={BTN_MAIN} disabled={busy} onClick={actions.onDownload}>
          {t("app.download")}</button>}
      </div>
      {apk && <p className="text-xs text-[#9aa7bc]">{t("app.download_hint")}</p>}
    </div>
  )
}
