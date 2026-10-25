import { useTranslation } from "react-i18next"
import { callTone, shortTime } from "./callsLogic"
import type { CallEntry } from "./types"

const DOT = { ok: "bg-emerald-400", warn: "bg-amber-400", idle: "bg-zinc-500" }

/** Letzte Anrufe: Zeit, maskierte Nummer, Ergebnis, Ton angekommen? – nie Inhalte. */
export function CallList({ calls }: { calls: CallEntry[] }) {
  const { t } = useTranslation("voip")
  if (calls.length === 0) return <p className="text-sm text-zinc-500">{t("calls.none")}</p>
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{t("calls.recent")}</p>
      <ul className="divide-y divide-zinc-800 rounded-lg border border-zinc-800" data-voip-call-list="1">
        {calls.slice(0, 10).map((c) => (
          <li key={c.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 text-sm">
            <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[callTone(c)]}`} />
            <span className="w-24 text-zinc-400">{shortTime(c.started_at)}</span>
            <span className="w-20 font-mono text-zinc-300">{c.number}</span>
            <span className="text-zinc-200">{t(`calls.result.${c.result}`)}</span>
            {c.is_test && <span className="rounded bg-indigo-500/15 px-1.5 text-xs text-indigo-300">{t("calls.test")}</span>}
            {c.heard === true && <span className="text-xs text-emerald-300">{t("calls.heard_ok")}</span>}
            {c.heard === false && <span className="text-xs text-amber-300">{t("calls.heard_missing")}</span>}
            {c.codec && (
              <span className="ml-auto text-xs text-zinc-500">
                {c.codec} · {t("calls.packets", { out: c.rtp_out, in: c.rtp_in })}
              </span>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
