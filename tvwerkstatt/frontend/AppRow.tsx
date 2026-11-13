import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { TvwAppDevice } from "./api"
import type { AppDeviceActions } from "./AppDevicesPanel"
import { appLine, buttonsOf, online } from "./appLogic"
import { BTN, BTN_DANGER, INPUT, ROW } from "./ui"

/** Ein gekoppeltes Gerät: Name, Art, verbunden/nicht, Testmeldung (nur aktiv), sperren bzw. entfernen. */
export function AppRow({ d, now, busy, actions }: { d: TvwAppDevice; now: Date; busy: boolean; actions: AppDeviceActions }) {
  const { t } = useTranslation("tvwerkstatt")
  const [title, setTitle] = useState("")
  const [btns, setBtns] = useState("")
  const on = online(d, now)
  const active = d.status === "active"
  return (
    <div className={`${ROW} flex-col items-stretch`}>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-sm text-[#e8eef8]">{d.name}</div>
          <div className="truncate text-xs text-[#9aa7bc]">{appLine(d) || "–"}</div>
        </div>
        <span className={`shrink-0 text-xs ${!active ? "text-red-300" : on ? "text-emerald-300" : "text-[#9aa7bc]"}`}>
          {t(!active ? "app.revoked" : on ? "app.online" : "app.offline")}
        </span>
      </div>
      {active && (
        <form className="flex flex-wrap gap-2" onSubmit={(e) => {
          e.preventDefault()
          if (title.trim()) { actions.onNotice(d.app_id, title.trim(), "", buttonsOf(btns)); setTitle("") }
        }}>
          <input className={`${INPUT} max-w-xs`} value={title} maxLength={80} placeholder={t("app.notice_ph")}
            aria-label={t("app.notice")} onChange={(e) => setTitle(e.target.value)} />
          <input className={`${INPUT} max-w-[14rem]`} value={btns} maxLength={70} placeholder={t("app.buttons_ph")}
            aria-label={t("app.buttons")} onChange={(e) => setBtns(e.target.value)} />
          <button type="submit" className={BTN} disabled={busy || !title.trim()}>{t("app.send")}</button>
        </form>
      )}
      <div className="flex gap-2">
        {active ? (
          <button type="button" className={BTN_DANGER} disabled={busy} onClick={() => actions.onRevoke(d.app_id)}>
            {t("app.revoke")}</button>
        ) : (
          <button type="button" className={BTN} disabled={busy} onClick={() => actions.onRemove(d.app_id)}>
            {t("app.remove")}</button>
        )}
      </div>
    </div>
  )
}
