import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { TvwAppCode, TvwAppDevices } from "./api"
import { AppBuildBox } from "./AppBuildBox"
import { AppRow } from "./AppRow"
import { minutesLeft } from "./appLogic"
import { BOX, BOX_HEAD, BTN_MAIN, INPUT, MUTED } from "./ui"

export interface AppDeviceActions {
  onCode: (name: string) => void; onRevoke: (id: string) => void; onRemove: (id: string) => void
  onNotice: (id: string, title: string, body: string, buttons: string[]) => void
  onBuild: () => void; onDownload: () => void
}

/** Bereich „HydraHive-App“ im Reiter Geräte: App bauen/laden, Code zum Koppeln, gekoppelte Geräte, Testmeldung. */
export function AppDevicesPanel({ data, code, ready, busy, now, actions }: {
  data: TvwAppDevices; code: TvwAppCode | null; ready: boolean; busy: boolean; now: Date; actions: AppDeviceActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const [name, setName] = useState("")
  return (
    <section className={BOX} aria-label={t("app.title")}>
      <h2 className={BOX_HEAD}>{t("app.title")}</h2>
      <p className={MUTED}>{t("app.explain")}</p>
      <AppBuildBox job={data.build} apk={data.apk} ready={ready} busy={busy} actions={actions} />
      {data.devices.length === 0 && <p className={MUTED}>{t("app.none")}</p>}
      {data.devices.map((d) => <AppRow key={d.app_id} d={d} now={now} busy={busy} actions={actions} />)}
      <form className="flex flex-wrap gap-2"
        onSubmit={(e) => { e.preventDefault(); if (name.trim()) { actions.onCode(name.trim()); setName("") } }}>
        <input className={`${INPUT} max-w-xs`} value={name} maxLength={40} placeholder={t("app.name_ph")}
          aria-label={t("app.name")} onChange={(e) => setName(e.target.value)} />
        <button type="submit" className={BTN_MAIN} disabled={busy || !name.trim()}>{t("app.new_code")}</button>
      </form>
      {code && (
        <div className="space-y-1 rounded border border-[#69d7ff]/60 p-3" role="status">
          <div className="text-xs text-[#9aa7bc]">{t("app.code_for", { name: code.name })}</div>
          <div className="font-mono text-2xl tracking-widest text-[#69d7ff]">{code.code}</div>
          <div className="text-xs text-[#9aa7bc]">
            {t("app.code_valid", { n: minutesLeft(code.expires_at, now) })} · {t("app.server")}: {code.server}
          </div>
          {code.pin_short && (
            <div className="text-xs text-[#9aa7bc]">
              {t("app.pin")}: <span className="font-mono text-base text-[#e8eef8]">{code.pin_short}</span>
            </div>
          )}
          <p className="text-xs text-[#9aa7bc]">{t(code.pin_short ? "app.code_hint_pin" : "app.code_hint")}</p>
        </div>
      )}
    </section>
  )
}
