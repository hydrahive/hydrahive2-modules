import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { TvwDesktop, TvwDevice, TvwStore } from "./api"
import { errorKey } from "./logic"
import { nameOf, sorted, sourceKey, validQuery } from "./storeLogic"
import { BOX, BOX_HEAD, BTN, BTN_DANGER, BTN_MAIN, INPUT, MUTED } from "./ui"

export interface AppsActions {
  onRead: () => void; onOpen: (pkg: string) => void; onSearch: (q: string) => void; onUninstall: (pkg: string) => void
}

const ROW_APP = "grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-b " +
  "border-[rgb(var(--hh-s-rand,52_66_92))] py-1.5"
const when = (iso: string) => iso.replace("T", " ").slice(0, 16)

/** Reiter Apps: links Play Store am Fernseher (Suche), rechts die selbst installierten Apps. */
export function AppsTab({ dev, data, desk, busy, actions }: {
  dev: TvwDevice; data: TvwStore | null; desk: TvwDesktop | null; busy: boolean; actions: AppsActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const [q, setQ] = useState("")
  const v = data?.view ?? null
  const job = data?.job
  const running = job?.state === "running"
  const stop = busy || running
  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <section className={BOX}>
        <h2 className={BOX_HEAD}>{t("apps.store_title")}</h2>
        <p className="text-xs text-[#9aa7bc]">{t("apps.store_hint")}</p>
        <form className="flex gap-2"
          onSubmit={(e) => { e.preventDefault(); if (validQuery(q)) actions.onSearch(q.trim()) }}>
          <input className={INPUT} value={q} maxLength={60} placeholder={t("apps.search_ph")}
            aria-label={t("apps.search")} onChange={(e) => setQ(e.target.value)} />
          <button type="submit" className={BTN_MAIN} disabled={stop || !validQuery(q)}>{t("apps.search")}</button>
        </form>
        {q && !validQuery(q) && <p className="text-xs text-amber-200">{t("apps.search_bad")}</p>}
        {running && <p className="text-xs text-[#69d7ff]" role="status">{t(`apps.job.${job?.kind ?? "store_read"}`)}</p>}
        {job?.state === "done" && job.kind === "store_open" && (
          <p className="text-xs text-emerald-300" role="status">{t("apps.opened")}</p>
        )}
        {job?.state === "failed" && <p className="text-xs text-red-300" role="alert">{t(errorKey(job.error_code))}</p>}
      </section>
      <section className={BOX}>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className={`${BOX_HEAD} mr-auto`}>{t("apps.title", { name: dev.name })}</h2>
          {v && <span className="text-xs text-[#9aa7bc]">{t("apps.read_at", { at: when(v.read_at) })}</span>}
          <button type="button" className={BTN} disabled={stop} onClick={actions.onRead}>{t("apps.read")}</button>
        </div>
        {!v && <p className={MUTED}>{t("apps.empty")}</p>}
        {v && sorted(v.apps, desk).map((a) => (
          <div key={a.package} className={ROW_APP}>
            <div className="min-w-0">
              <div className="truncate text-sm text-[#e8eef8]">{nameOf(a, desk)}</div>
              <code className="block truncate text-xs text-[#9aa7bc]">
                {a.package}{a.version_name ? ` · ${a.version_name}` : ""}{a.enabled ? "" : ` · ${t("apps.off")}`}
              </code>
            </div>
            <span className="text-xs text-[#9aa7bc]">{t(sourceKey(a))}</span>
            <div className="flex gap-2">
              {a.store && (
                <button type="button" className={BTN} disabled={stop} onClick={() => actions.onOpen(a.package)}>
                  {t("apps.open")}
                </button>
              )}
              {!a.locked && (
                <button type="button" className={BTN_DANGER} disabled={stop}
                  onClick={() => actions.onUninstall(a.package)}>
                  {t("apps.uninstall")}
                </button>
              )}
            </div>
          </div>
        ))}
        <p className="text-xs text-[#9aa7bc]">{t("apps.preinstalled_hint")}</p>
      </section>
    </div>
  )
}
