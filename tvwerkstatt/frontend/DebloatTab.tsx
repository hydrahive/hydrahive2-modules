import { useTranslation } from "react-i18next"
import type { TvwDebloat, TvwDebloatRow, TvwDevice } from "./api"
import { canPick, grouped, listNames, mark, others, split, stepText, suggested } from "./debloatLogic"
import { errorKey } from "./logic"
import { BOX, BOX_HEAD, BTN, BTN_MAIN, MUTED, ROW_KV } from "./ui"

const EDGE = "border-[rgb(var(--hh-s-rand,52_66_92))]"
const MARK = {
  off: "border-emerald-400/60 text-emerald-300", todo: "border-amber-400/60 text-amber-200",
  locked: `${EDGE} text-[#9aa7bc]`, on: `${EDGE} text-[#e8eef8]`,
}

export interface DebloatActions {
  onRead: () => void; onPick: (pkgs: string[], on: boolean) => void
  onOff: (pkgs: string[]) => void; onOn: (pkgs: string[]) => void; onUndoAll: () => void
}

/** Reiter Entrümpeln – Aufbau wie die Demo: links Stand und Knöpfe, rechts Liste nach Gruppen mit Haken. */
export function DebloatTab({ dev, data, picked, busy, actions }: {
  dev: TvwDevice; data: TvwDebloat | null; picked: Set<string>; busy: boolean; actions: DebloatActions
}) {
  const { t } = useTranslation("tvwerkstatt")
  const v = data?.view ?? null
  const job = [data?.switch_job, data?.read_job].find((j) => j?.state === "running") ?? null
  const failed = [data?.switch_job, data?.read_job].find((j) => j?.state === "failed")
  const sel = v ? split(v, picked) : { off: [], on: [] }
  const stop = busy || !!job
  const step = (s: string) => { const x = stepText(s); return t(x.key, { n: x.n }) }
  return (
    <div className="grid gap-4 xl:grid-cols-[300px_minmax(0,1fr)]">
      <section className={BOX}>
        <h2 className={BOX_HEAD}>{t("deb.state")}</h2>
        {v ? (<>
          <KV k={t("deb.off")} v={String(v.off_count)} />
          <KV k={t("deb.by_us")} v={String(v.ours.length)} />
          <KV k={t("deb.todo")} v={String(v.recommended_on)} />
          <KV k={t("deb.backup")} v={data?.backup_at ? data.backup_at.replace("T", " ").slice(0, 16) : t("deb.none")} />
          <KV k={t("deb.read_at")} v={v.read_at.replace("T", " ").slice(0, 16)} />
          <KV k={t("deb.lists")} v={v.lists_used.length ? t("deb.lists_of", { n: v.lists_used.length, all: v.total_lists })
            : t("deb.no_list")} />
          {v.lists_used.length > 0 && <p className="text-xs text-[#9aa7bc]">{listNames(v.lists_used)}</p>}
        </>) : <p className={MUTED}>{t("deb.never")}</p>}
        {v && v.back_on.length > 0 && (
          <p className="rounded bg-amber-500/10 p-2 text-xs text-amber-200" role="status">
            {t("deb.back_on", { n: v.back_on.length })}
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <button type="button" className={BTN} disabled={stop} onClick={actions.onRead}>
            {t(v ? "deb.check_update" : "deb.read")}
          </button>
          {v && v.ours.length > 0 && (
            <button type="button" className={BTN} disabled={stop} onClick={actions.onUndoAll}>{t("deb.undo_all")}</button>
          )}
        </div>
        {job && <p className="text-xs text-[#69d7ff]" role="status">{t("deb.working", { step: step(job.step) })}</p>}
        {failed && !job && <p className="text-xs text-red-300" role="alert">{t(errorKey(failed.error_code))}</p>}
        <p className="text-xs text-[#9aa7bc]">{t("deb.explain")}</p>
      </section>
      <section className={BOX}>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className={`${BOX_HEAD} mr-auto`}>{t("deb.title", { name: dev.name })}</h2>
          {v && suggested(v).length > 0 && (
            <button type="button" className={BTN} disabled={stop} onClick={() => actions.onPick(suggested(v), true)}>
              {t("deb.pick_suggested", { n: suggested(v).length })}
            </button>
          )}
          <button type="button" className={BTN_MAIN} disabled={stop || !sel.off.length}
            onClick={() => actions.onOff(sel.off)}>{t("deb.switch_off", { n: sel.off.length })}</button>
          {sel.on.length > 0 && (
            <button type="button" className={BTN} disabled={stop} onClick={() => actions.onOn(sel.on)}>
              {t("deb.switch_on", { n: sel.on.length })}
            </button>
          )}
        </div>
        {!v && <p className={MUTED}>{t("deb.empty")}</p>}
        {v && grouped(v).map(({ group, rows }) => (
          <div key={group} className="space-y-1">
            <h3 className="text-xs font-semibold text-[#69d7ff]">{t(`deb.group.${group}`)}</h3>
            {rows.map((r) => <Row key={r.package} r={r} n={v.lists_used.length} picked={picked.has(r.package)}
              disabled={stop} onPick={actions.onPick} />)}
          </div>
        ))}
        {v && others(v).length > 0 && (
          <details className="space-y-1">
            <summary className="cursor-pointer text-xs font-semibold text-[#9aa7bc]">
              {t("deb.others", { n: others(v).length })}
            </summary>
            {others(v).map((r) => <Row key={r.package} r={r} n={v.lists_used.length} picked={picked.has(r.package)}
              disabled={stop} onPick={actions.onPick} />)}
          </details>
        )}
      </section>
    </div>
  )
}

function Row({ r, n, picked, disabled, onPick }: {
  r: TvwDebloatRow; n: number; picked: boolean; disabled: boolean; onPick: (p: string[], on: boolean) => void
}) {
  const { t } = useTranslation("tvwerkstatt")
  const m = mark(r)
  return (
    <label className={`grid grid-cols-[auto_minmax(0,1fr)_auto_auto] items-center gap-3 border-b ${EDGE} py-1.5`}>
      <input type="checkbox" className="accent-[#69d7ff]" checked={picked} disabled={disabled || !canPick(r)}
        aria-label={r.package} onChange={(e) => onPick([r.package], e.target.checked)} />
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
    </label>
  )
}

function KV({ k, v }: { k: string; v: string }) {
  return <div className={ROW_KV}><span className="text-[#9aa7bc]">{k}</span><span className="text-[#e8eef8]">{v}</span></div>
}
