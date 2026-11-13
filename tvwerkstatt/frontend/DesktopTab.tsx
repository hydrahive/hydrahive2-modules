import { useTranslation } from "react-i18next"
import type { Mood, TvwDesktop, TvwDevice, TvwLook, TvwState } from "./api"
import * as api from "./api"
import { lastGood } from "./buildLogic"
import { sameLook } from "./desktopLogic"
import { actionView, canInstall, kindKey, ourHome } from "./deviceLogic"
import { errorKey } from "./logic"
import { LookPanel } from "./LookPanel"
import { TvPreview } from "./TvPreview"
import { BOX, BOX_HEAD, BTN, BTN_MAIN, CHIP, CHIP_ON, MUTED, ROW_KV } from "./ui"

export interface DesktopActions {
  onLook: (l: TvwLook) => void; onSave: () => void; onReadApps: () => void; onPushLook: () => void
  onBuild: () => void; onInstall: () => void; onRestore: () => void; onMood: (m: Mood) => void
  onUpload: (m: Mood, f: File) => void; onDeleteWall: (id: string) => void
}

/** Reiter Desktop – Aufbau wie die Demo: links Gerät/Bauumgebung/Stand, Mitte Vorschau und Schritte, rechts Aussehen. */
export function DesktopTab({ s, dev, desk, draft, mood, now, busy, actions }: {
  s: TvwState; dev: TvwDevice; desk: TvwDesktop; draft: TvwLook; mood: Mood; now: Date; busy: boolean
  actions: DesktopActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const dirty = !sameLook(draft, desk.look)
  const built = lastGood(s.builds)
  const ours = ourHome(dev)
  const walls = desk.wallpapers.filter((w) => w.mood === mood)
  const job = [desk.read_job, desk.push_job].find((j) => j?.state === "running")
  const failed = [desk.push_job, desk.read_job].find((j) => j?.state === "failed")
  const act = actionView(dev)
  return (
    <div className="grid gap-4 xl:grid-cols-[260px_minmax(0,1fr)_320px]">
      <div className="space-y-4">
        <section className={BOX}>
          <h2 className={BOX_HEAD}>{t("desk.device")}</h2>
          <KV k={t("device.name")} v={dev.name} />
          <KV k={t("desk.model")} v={dev.model || "–"} />
          <KV k={t("desk.system")} v={[dev.android ? `Android ${dev.android}` : "",
            kindKey(dev.kind) ? t(kindKey(dev.kind)) : ""].filter(Boolean).join(" · ") || "–"} />
          <KV k={t("device.address")} v={dev.address} />
          <KV k={t("desk.debugging")} v={t(`adb.${dev.adb_state ?? "unknown"}`)} />
        </section>
        <section className={BOX}>
          <h2 className={BOX_HEAD}>{t("desk.on_tv")}</h2>
          <KV k={t("desk.home")} v={t(ours ? "desk.home_ours" : dev.current_home ? "desk.home_original" : "desk.unknown")} />
          <KV k={t("desk.look_state")} v={t(desk.pushed_at ? (desk.pushed_current && !dirty ? "desk.look_current"
            : "desk.look_old") : "desk.look_none")} />
          <KV k={t("desk.apps_known")} v={String(desk.apps.length)} />
          <button type="button" className={BTN} disabled={busy} onClick={actions.onReadApps}>{t("desk.read_apps")}</button>
        </section>
        <section className={BOX}>
          <h2 className={BOX_HEAD}>{t("setup.title")}</h2>
          <KV k={t("desk.container")} v={t(`container.${s.container}`)} />
          <KV k={t("desk.home_build")} v={built?.version ? `${built.version} · ${built.commit_id.slice(0, 7)}` : "–"} />
        </section>
      </div>

      <div className="space-y-3">
        <TvPreview apps={desk.apps} look={draft} mood={mood} now={now}
          wallpaper={walls[0] ? api.wallpaperPath(dev.device_id, walls[0].wallpaper_id) : null}
          imagePath={(p) => api.appImagePath(dev.device_id, p)} />
        <div className="flex flex-wrap items-center gap-2 text-xs text-[#9aa7bc]">
          <span>{t("desk.preview_note")}</span>
          {(["morning", "evening", "night"] as Mood[]).map((m) => (
            <button key={m} type="button" className={mood === m ? CHIP_ON : CHIP} aria-pressed={mood === m}
              onClick={() => actions.onMood(m)}>{t(`mood.${m}`)}</button>
          ))}
        </div>
        <section className={BOX}>
          <div className="flex flex-wrap items-center gap-2">
            <button type="button" className={built ? BTN : BTN_MAIN} disabled={busy} onClick={actions.onBuild}>
              {t("desk.step_build")}</button>
            <span className="text-[#9aa7bc]" aria-hidden>→</span>
            <button type="button" className={!ours && built ? BTN_MAIN : BTN}
              disabled={busy || ours || !canInstall(dev, !!built)} onClick={actions.onInstall}>
              {t("desk.step_install")}</button>
            <span className="text-[#9aa7bc]" aria-hidden>→</span>
            <button type="button" className={ours && (dirty || !desk.pushed_current) ? BTN_MAIN : BTN}
              disabled={busy || !ours || dev.adb_state !== "open"} onClick={actions.onPushLook}>
              {t("desk.push_look")}</button>
            <button type="button" className={`${BTN} ml-auto`} disabled={busy || !ours || !dev.stock_home}
              onClick={actions.onRestore}>{t("install.restore")}</button>
          </div>
          <p className={MUTED} role="status">
            {job ? t(`desk.job_${job === desk.read_job ? "read" : "push"}`)
              : act === "installing" ? t("install.running", { step: t(`istep.${dev.action?.step}`) })
                : act === "restoring" ? t("install.restoring")
                  : s.build?.state === "running" ? t("build.running", { n: "…", total: "…" })
                    : t(ours ? (dirty ? "desk.hint_dirty" : "desk.hint_ready") : "desk.hint_not_ours")}
          </p>
          {failed && <p className="text-sm text-red-300" role="alert">{t(errorKey(failed.error_code))}</p>}
          {dev.action?.state === "failed" && (
            <p className="text-sm text-red-300" role="alert">{t(errorKey(dev.action.error_code))}</p>
          )}
        </section>
      </div>

      <div className={BOX}>
        <LookPanel look={draft} apps={desk.apps} walls={desk.wallpapers} mood={mood} onMood={actions.onMood}
          onChange={actions.onLook} onUpload={actions.onUpload} onDeleteWall={actions.onDeleteWall}
          wallPath={(id) => api.wallpaperPath(dev.device_id, id)} />
        <div className="flex gap-2 border-t border-[rgb(var(--hh-s-rand,52_66_92))] pt-3">
          <button type="button" className={dirty ? BTN_MAIN : BTN} disabled={busy || !dirty} onClick={actions.onSave}>
            {t("desk.save")}</button>
          <button type="button" className={BTN} disabled={busy || !dirty} onClick={() => actions.onLook(desk.look)}>
            {t("desk.discard")}</button>
        </div>
      </div>
    </div>
  )
}

function KV({ k, v }: { k: string; v: string }) {
  return <div className={ROW_KV}><span className="text-[#9aa7bc]">{k}</span><span className="text-right">{v}</span></div>
}
