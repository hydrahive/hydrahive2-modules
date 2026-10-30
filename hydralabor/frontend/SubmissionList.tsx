import { useTranslation } from "react-i18next"
import { when } from "./logic"
import type { Submission } from "./githubLogic"
import { BOX, BTN } from "./ui"

const STATE_CLS: Record<string, string> = { merged: "text-emerald-300", closed: "text-[#9aa7bc]", submitted: "text-amber-200" }

/** „Meine Einreichungen“ mit Stand; „Stand abfragen“ fragt GitHub nur auf Knopfdruck. */
export function SubmissionList({ items, busy, onRefresh }: { items: Submission[]; busy: boolean; onRefresh: () => void }) {
  const { t } = useTranslation("hydralabor")
  return (
    <section className={BOX}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-[#e8eef8]">{t("subs.title")}</h2>
        {items.length > 0 && <button type="button" className={BTN} disabled={busy} onClick={onRefresh}>{t("subs.refresh")}</button>}
      </div>
      {items.length === 0 ? <p className="text-sm text-[#9aa7bc]">{t("subs.empty")}</p> : (
        <ul className="space-y-1 text-sm">
          {items.map((s) => (
            <li key={s.id} className="flex flex-wrap items-baseline gap-x-2 break-words">
              <span className="text-[#9aa7bc]">{t(`subs.kind.${s.kind}`)}</span>
              <a className="text-[#e8eef8] underline" href={s.url} target="_blank" rel="noreferrer">{s.title} #{s.number}</a>
              <span className={STATE_CLS[s.state] ?? "text-[#c8d2df]"}>{t(`subs.state.${s.state}`)}</span>
              <span className="text-xs text-[#9aa7bc]">{when(s.created_at)}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}
