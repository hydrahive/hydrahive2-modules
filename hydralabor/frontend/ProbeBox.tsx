import { useTranslation } from "react-i18next"
import { probeView, type ProbeState } from "./probeLogic"
import { BOX, BTN, BTN_MAIN } from "./ui"

interface Props {
  p: ProbeState; job: string; busy: boolean; containerRunning: boolean
  onBuild: () => void; onStart: () => void; onStop: () => void; onOpen: () => void
}

/** L3: Probe-HydraHive aus dem Labor-Stand – bauen, starten, im Browser öffnen, stoppen. */
export function ProbeBoxView({ p, job, busy, containerRunning, onBuild, onStart, onStop, onOpen }: Props) {
  const { t } = useTranslation("hydralabor")
  const v = probeView(p, job)
  const lock = busy || !!job || !containerRunning
  return (
    <section className={BOX}>
      <h2 className="text-sm font-semibold text-[#e8eef8]">{t("probe.title")}</h2>
      <p className="text-sm text-[#c8d2df]">{t("probe.intro")}</p>
      {!containerRunning && <p className="text-sm text-amber-200">{t("probe.lab_off")}</p>}
      {v === "busy" && <p className="text-sm text-amber-200" aria-live="polite">{t(`job.${job}`)}</p>}
      {v === "open" && (
        <div className="space-y-1">
          <p className="text-sm text-emerald-300">{t("probe.where", { port: p.port })}</p>
          <p className="text-sm text-[#c8d2df]">{t("probe.login_hint")}</p>
          <p className="text-sm text-[#c8d2df]">{t("probe.user")}: <span className="font-mono text-[#e8eef8]">{p.user}</span></p>
          {p.password && (
            <p className="flex flex-wrap items-center gap-2 text-sm text-[#c8d2df]">{t("probe.password")}:
              <span className="select-all break-all font-mono text-[#e8eef8]">{p.password}</span>
              <button type="button" className={BTN} disabled={busy}
                onClick={() => navigator.clipboard?.writeText(p.password)}>{t("probe.copy")}</button>
            </p>
          )}
        </div>
      )}
      <div className="flex flex-wrap gap-2">
        {v === "open" && <button type="button" className={BTN_MAIN} disabled={lock} onClick={onOpen}>{t("probe.open")}</button>}
        {v === "open" && <button type="button" className={BTN} disabled={lock} onClick={onStop}>{t("probe.stop")}</button>}
        {v === "stopped" && <button type="button" className={BTN_MAIN} disabled={lock} onClick={onStart}>{t("probe.start")}</button>}
        {!p.built
          ? <button type="button" className={BTN_MAIN} disabled={lock} onClick={onBuild}>{t("probe.build")}</button>
          : <button type="button" className={BTN} disabled={lock} onClick={onBuild}>{t("probe.rebuild")}</button>}
      </div>
    </section>
  )
}
