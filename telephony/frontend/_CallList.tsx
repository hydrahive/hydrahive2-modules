import { PhoneIncoming, PhoneOutgoing } from "lucide-react"
import { useTranslation } from "react-i18next"
import { callTone, hasNote, noteLine, shortTime } from "./callsLogic"
import type { CallEntry } from "./types"

const DOT = { ok: "bg-emerald-400", warn: "bg-amber-400", idle: "bg-zinc-500" }

/** Letzte Anrufe: Zeit, maskierte Nummer, Ergebnis, Notiz des Assistenten – nie Ton oder Wortlaut. */
export function CallList({ calls, onRead }: { calls: CallEntry[]; onRead?: (id: number) => void }) {
  const { t } = useTranslation("voip")
  if (calls.length === 0) return <p className="text-sm text-zinc-500">{t("calls.none")}</p>
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-zinc-500">{t("calls.recent")}</p>
      <ul className="divide-y divide-zinc-800 rounded-lg border border-zinc-800" data-voip-call-list="1">
        {calls.slice(0, 10).map((c) => (
          <li key={c.id} className="px-3 py-2 text-sm">
            <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
              <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[callTone(c)]}`} />
              <span data-voip-direction={c.direction ?? "in"} title={t(`calls.direction.${c.direction ?? "in"}`)}
                className="text-zinc-500">{c.direction === "out" ? <PhoneOutgoing size={13} /> : <PhoneIncoming size={13} />}</span>
              <span className="w-24 text-zinc-400">{shortTime(c.started_at)}</span>
              <span className="w-20 font-mono text-zinc-300">{c.number}</span>
              <span className="text-zinc-200">{t(`calls.result.${c.result}`)}</span>
              {c.is_test && <span className="rounded bg-indigo-500/15 px-1.5 text-xs text-indigo-300">{t("calls.test")}</span>}
              {c.heard === true && <span className="text-xs text-emerald-300">{t("calls.heard_ok")}</span>}
              {c.heard === false && <span className="text-xs text-amber-300">{t("calls.heard_missing")}</span>}
              {!c.notes_read && <span className="rounded bg-amber-500/15 px-1.5 text-xs text-amber-200" data-voip-unread="1">{t("notes.new")}</span>}
              {c.codec && (
                <span className="ml-auto text-xs text-zinc-500">
                  {c.codec} · {t("calls.packets", { out: c.rtp_out, in: c.rtp_in })}
                </span>
              )}
            </div>
            {hasNote(c) && (
              <div className="mt-2 space-y-1 rounded-lg bg-zinc-900/70 p-3" data-voip-note="1">
                {noteLine(c.notes) && <p className="font-medium text-zinc-100">{noteLine(c.notes)}</p>}
                {c.notes.summary && <p className="text-zinc-300">{c.notes.summary}</p>}
                {c.notes.open_questions?.length ? (
                  <p className="text-xs text-zinc-400">{t("notes.open_questions")}: {c.notes.open_questions.join(" · ")}</p>
                ) : null}
                {c.notes.needs_review && <p className="text-xs text-amber-300">{t("notes.needs_review")}</p>}
                {!c.notes_read && onRead && (
                  <button type="button" className="text-xs text-indigo-300 hover:underline" onClick={() => onRead(c.id)}
                    data-voip-mark-read="1">{t("notes.mark_read")}</button>
                )}
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
