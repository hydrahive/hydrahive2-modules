import { useTranslation } from "react-i18next"
import type { TvwDebloat, TvwDebloatRow, TvwDevice } from "./api"
import { grouped, listNames, mark, others } from "./debloatLogic"
import { errorKey } from "./logic"
import { BOX, BOX_HEAD, BTN, MUTED, ROW_KV } from "./ui"

const EDGE = "border-[rgb(var(--hh-s-rand,52_66_92))]"
const MARK = {
  off: "border-emerald-400/60 text-emerald-300", todo: "border-amber-400/60 text-amber-200",
  locked: `${EDGE} text-[#9aa7bc]`, on: `${EDGE} text-[#e8eef8]`,
}

/** Reiter Entrümpeln (Teil 1, nur lesen) – Aufbau wie die Demo: links Stand, rechts Liste nach Gruppen. */
export function DebloatTab({ dev, data, busy, onRead }: {
  dev: TvwDevice; data: TvwDebloat | null; busy: boolean; onRead: () => void
}) {
  const { t } = useTranslation("tvwerkstatt")
  const v = data?.view ?? null
  const job = data?.read_job
  const running = job?.state === "running"
  return (
    <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
      <section className={BOX}>
        <h2 className={BOX_HEAD}>{t("deb.state")}</h2>
        {v ? (<>
          <KV k={t("deb.off")} v={String(v.off_count)} />
          <KV k={t("deb.todo")} v={String(v.recommended_on)} />
          <KV k={t("deb.read_at")} v={v.read_at.replace("T", " ").slice(0, 16)} />
          <KV k={t("deb.lists")} v={v.lists_used.length ? t("deb.lists_of", { n: v.lists_used.length, all: v.total_lists })
            : t("deb.no_list")} />
          {v.lists_used.length > 0 && (
            <p className="text-xs text-[#9aa7bc]">{listNames(v.lists_used)}</p>
          )}
        </>) : <p className={MUTED}>{t("deb.never")}</p>}
        <button type="button" className={BTN} disabled={busy || running} onClick={onRead}>
          {running ? t("deb.reading", { step: t(`deb.step.${job?.step ?? "container"}`) }) : t("deb.read")}
        </button>
        {job?.state === "failed" && <p className="text-xs text-red-300" role="alert">{t(errorKey(job.error_code))}</p>}
        <p className="text-xs text-[#9aa7bc]">{t("deb.explain")}</p>
        <p className="text-xs text-[#9aa7bc]">{t("deb.soon")}</p>
      </section>
      <section className={BOX}>
        <h2 className={BOX_HEAD}>{t("deb.title", { name: dev.name })}</h2>
        {!v && <p className={MUTED}>{t("deb.empty")}</p>}
        {v && grouped(v).map(({ group, rows }) => (
          <div key={group} className="space-y-1">
            <h3 className="text-xs font-semibold text-[#69d7ff]">{t(`deb.group.${group}`)}</h3>
            {rows.map((r) => <Row key={r.package} r={r} n={v.lists_used.length} />)}
          </div>
        ))}
        {v && others(v).length > 0 && (
          <details className="space-y-1">
            <summary className="cursor-pointer text-xs font-semibold text-[#9aa7bc]">
              {t("deb.others", { n: others(v).length })}
            </summary>
            {others(v).map((r) => <Row key={r.package} r={r} n={v.lists_used.length} />)}
          </details>
        )}
      </section>
    </div>
  )
}

function Row({ r, n }: { r: TvwDebloatRow; n: number }) {
  const { t } = useTranslation("tvwerkstatt")
  const m = mark(r)
  return (
    <div className={`grid grid-cols-[minmax(0,1fr)_auto_auto] items-center gap-3 border-b ${EDGE} py-1.5`}>
      <div className="min-w-0">
        {r.note && <div className="truncate text-sm text-[#e8eef8]" title={r.note}>{r.note}</div>}
        <code className={`block truncate ${r.note ? "text-xs text-[#9aa7bc]" : "text-sm text-[#e8eef8]"}`}>{r.package}</code>
      </div>
      <span className="text-xs text-[#9aa7bc]" title={t("deb.of_hint")}>
        {n ? t("deb.of", { of: r.of, n }) : ""}{r.kept ? ` · ${t("deb.kept", { n: r.kept })}` : ""}
      </span>
      <span className={`rounded-full border px-2 py-0.5 text-center text-xs ${MARK[m]}`}
        title={r.locked ? t(`deb.lock.${r.locked}`) : undefined}>
        {t(`deb.mark.${m}`)}
      </span>
    </div>
  )
}

function KV({ k, v }: { k: string; v: string }) {
  return <div className={ROW_KV}><span className="text-[#9aa7bc]">{k}</span><span className="text-[#e8eef8]">{v}</span></div>
}
