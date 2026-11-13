import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { TvwAddon, TvwAddons, TvwDevice } from "./api"
import { type AddonFilter, addonImagePath, androidOf, FILTERS, fits, shownPerms, visible } from "./addonLogic"
import { errorKey } from "./logic"
import { BOX, BOX_HEAD, BTN, BTN_DANGER, BTN_MAIN, CHIP, CHIP_ON, INPUT, MUTED } from "./ui"
import { useAuthImage } from "./useAuthImage"

export interface AddonsActions {
  onCatalog: () => void; onInstall: (a: TvwAddon) => void; onRemove: (a: TvwAddon) => void
}

const PERM = { red: "border-red-400/60 text-red-300", yellow: "border-amber-400/60 text-amber-200",
  "": "border-[rgb(var(--hh-s-rand,52_66_92))] text-[#9aa7bc]" } as Record<string, string>
const PILL = "whitespace-nowrap rounded-full border px-2 text-[11px]"
const CARD = "flex flex-col gap-2 rounded-lg border border-[rgb(var(--hh-s-rand,52_66_92))] " +
  "bg-[rgb(var(--hh-s-innen,36_48_71))] p-3"

/** Reiter Zusätze wie die Demo: links Stand auf dem Fernseher, rechts Katalog mit Filtern und Karten. */
export function AddonsTab({ dev, data, busy, actions }: {
  dev: TvwDevice; data: TvwAddons | null; busy: boolean; actions: AddonsActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const [f, setF] = useState<AddonFilter>("all")
  const [q, setQ] = useState("")
  const items = data?.items ?? null
  const job = data?.job
  const running = job?.state === "running"
  const stop = busy || running
  const mine = (items ?? []).filter((a) => a.installed)
  return (
    <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
      <section className={BOX}>
        <h2 className={BOX_HEAD}>{t("add.on_tv", { name: dev.name })}</h2>
        {mine.length ? mine.map((a) => (
          <div key={a.id} className="flex justify-between gap-2 text-sm">
            <span className="text-[#e8eef8]">{a.name}</span>
            <span className="text-xs text-[#9aa7bc]">{a.installed?.version}</span>
          </div>
        )) : <p className={MUTED}>{t("add.none_yet")}</p>}
        {running && <p className="text-xs text-[#69d7ff]" role="status">
          {t("add.working", { step: t(`add.step.${job?.step ?? "container"}`, { defaultValue: job?.step }) })}</p>}
        {job?.state === "failed" && <p className="text-xs text-red-300" role="alert">{t(errorKey(job.error_code))}</p>}
        <p className="text-xs text-[#9aa7bc]">{t("add.explain")}</p>
      </section>
      <section className={BOX}>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className={`${BOX_HEAD} mr-auto`}>{t("add.catalog")}</h2>
          {data && <span className="text-xs text-[#9aa7bc]">cleanyourtv · {data.commit_id}</span>}
        </div>
        {!items ? (
          <div className="space-y-2">
            <p className={MUTED}>{t("add.no_catalog")}</p>
            <button type="button" className={BTN_MAIN} disabled={stop} onClick={actions.onCatalog}>{t("add.load")}</button>
          </div>
        ) : (<>
          <div className="flex flex-wrap items-center gap-2">
            <input className={`${INPUT} max-w-xs`} value={q} placeholder={t("add.search")} aria-label={t("add.search")}
              onChange={(e) => setQ(e.target.value)} />
            {FILTERS.map((k) => (
              <button key={k} type="button" className={f === k ? CHIP_ON : CHIP} onClick={() => setF(k)}>
                {t(`add.filter.${k}`)}
              </button>
            ))}
          </div>
          <div className="grid gap-3 [grid-template-columns:repeat(auto-fill,minmax(250px,1fr))]">
            {visible(items, f, q).map((a) => <Card key={a.id} a={a} sdk={dev.sdk} stop={stop} actions={actions} />)}
          </div>
        </>)}
      </section>
    </div>
  )
}

function Card({ a, sdk, stop, actions }: { a: TvwAddon; sdk?: number; stop: boolean; actions: AddonsActions }) {
  const { t } = useTranslation("tvwerkstatt")
  const img = useAuthImage(a.has_image ? addonImagePath(a.id) : null)
  const perms = shownPerms(a)
  const ok = fits(a, sdk)
  return (
    <div className={CARD}>
      {img ? <img src={img} alt="" className="aspect-video w-full rounded object-cover" />
        : <div className="aspect-video w-full rounded bg-[rgb(var(--hh-s-box,23_32_48))]" />}
      <div className="flex items-center gap-2">
        <b className="mr-auto text-sm text-[#e8eef8]">{a.name}</b>
        {a.dream && <span className="text-xs text-[#9aa7bc]">{t("add.dream")}</span>}
        {a.installed && <span className="rounded-full border border-emerald-400/60 px-2 text-xs text-emerald-300">
          {t("add.installed")}</span>}
      </div>
      <p className="line-clamp-3 text-xs text-[#9aa7bc]" title={a.what}>{a.what}</p>
      <div className="flex flex-wrap gap-1">
        {perms.length ? perms.map((p) => (
          <span key={p.name} className={`${PILL} ${PERM[p.level] ?? PERM[""]}`}
            title={p.name}>{t(`add.perm.${p.name}`, { defaultValue: p.name })}</span>
        )) : <span className={`rounded-full border px-2 text-[11px] ${PERM[""]}`}>{t("add.no_perms")}</span>}
      </div>
      {!ok && <p className="text-xs text-amber-200">{t("add.too_old", { v: androidOf(a.min_sdk) })}</p>}
      <div className="mt-auto flex items-center gap-2">
        {a.installed ? (<>
          <button type="button" className={BTN} disabled={stop} onClick={() => actions.onInstall(a)}>
            {t("add.rebuild")}</button>
          <button type="button" className={BTN_DANGER} disabled={stop} onClick={() => actions.onRemove(a)}>
            {t("add.remove")}</button>
        </>) : (
          <button type="button" className={BTN_MAIN} disabled={stop || !ok} onClick={() => actions.onInstall(a)}>
            {t("add.install")}</button>
        )}
        <span className="ml-auto truncate text-[11px] text-[#9aa7bc]" title={a.author}>{a.author}</span>
      </div>
    </div>
  )
}
