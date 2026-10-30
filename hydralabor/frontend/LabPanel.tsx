import { useTranslation } from "react-i18next"
import { errorKey, testLine, when, type LabState } from "./logic"
import { BOX, BTN, BTN_DANGER, BTN_MAIN } from "./ui"

interface Props {
  s: LabState; busy: boolean; msg: string | null; onJob: (j: "test" | "probe") => void
  onPower: (a: "start" | "stop") => void; onAskReset: () => void; onAskRemove: () => void
}

/** Labor-Seite nach dem Einrichten (PLAN-L1.md): Stand, Chat, Testlauf, Sperre prüfen, Zurücksetzen, Entfernen. */
export function LabPanel({ s, busy, msg, onJob, onPower, onAskReset, onAskRemove }: Props) {
  const { t } = useTranslation("hydralabor")
  const lock = busy || !!s.running
  const tl = testLine(s.last_test)
  return (
    <div className="space-y-4">
      {s.error_code && (
        <div role="alert" className="rounded border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200">
          {t(errorKey(s.error_code))}</div>
      )}

      <section className={BOX}>
        <p className="text-base font-semibold text-[#e8eef8]">{t("lab.ready")}</p>
        <p className="text-sm text-[#c8d2df]">{t("lab.howto")}</p>
        <a href={`/projects/${s.project_id}`} className={`${BTN_MAIN} inline-block`}>{t("lab.chat")}</a>
      </section>

      <section className={BOX}>
        <p className={`text-sm font-semibold ${s.container_running ? "text-emerald-300" : "text-[#c8d2df]"}`}>
          {s.container_running ? t("lab.running") : t("lab.stopped")}</p>
        <p className="text-sm text-[#c8d2df]">{t("lab.limits", { cpu: s.cpu, ram: s.ram_mb, disk: s.disk_gb })}</p>
        <p className="text-sm text-[#c8d2df]">
          {s.last_net_ok ? t("lab.net_ok", { when: when(s.last_net_ok) }) : t("lab.net_never")}</p>
        {s.running && <p className="text-sm text-amber-200" aria-live="polite">{t(`job.${s.running}`)}</p>}
        <div className="flex flex-wrap gap-2">
          {s.container_running
            ? <button type="button" className={BTN} disabled={lock} onClick={() => onPower("stop")}>{t("lab.stop")}</button>
            : <button type="button" className={BTN} disabled={lock} onClick={() => onPower("start")}>{t("lab.start")}</button>}
          <button type="button" className={BTN} disabled={lock || !s.container_running} onClick={() => onJob("test")}>{t("lab.test")}</button>
          <button type="button" className={BTN} disabled={lock} onClick={() => onJob("probe")}>{t("lab.probe")}</button>
          <button type="button" className={BTN} disabled={lock} onClick={onAskReset}>{t("lab.reset")}</button>
          <button type="button" className={BTN_DANGER} disabled={lock} onClick={onAskRemove}>{t("lab.remove")}</button>
        </div>
        {msg && <p className="text-sm text-red-300">{t(msg)}</p>}
      </section>

      <section className={BOX}>
        {tl ? (
          <>
            <p className={`text-sm font-semibold ${s.last_test.ok ? "text-emerald-300" : "text-red-300"}`}>
              {t(tl.key, { passed: tl.passed, failed: tl.failed })}</p>
            <p className="text-sm text-[#c8d2df]">{t("test.last", { when: when(s.last_test.at ?? "") })}</p>
            {!!s.last_test.failures?.length && (
              <ul className="space-y-0.5 text-xs text-[#c8d2df] break-all">
                {s.last_test.failures.map((f) => <li key={f}>{f}</li>)}</ul>
            )}
          </>
        ) : <p className="text-sm text-[#c8d2df]">{t("test.never")}</p>}
      </section>
    </div>
  )
}
