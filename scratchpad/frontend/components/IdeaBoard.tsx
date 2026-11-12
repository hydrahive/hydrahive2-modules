import { PenTool, Sparkles } from "lucide-react"
import { Link } from "react-router-dom"
import type { T } from "../texts.de"
import type { IdeaBoardRef } from "../types"
import { BADGE, BUTTON } from "./styles"

interface Props {
  board: IdeaBoardRef | null
  /** Ist das Blueprint-Modul installiert? Ohne Modul gibt es keinen Knopf. */
  installed: boolean
  busy: boolean
  t: T
  onCreate: () => void
}

/** Das Blueprint-Board zur Idee: Verweis zum Öffnen. Ohne Board der Knopf „Als Board skizzieren“. */
export function IdeaBoard({ board, installed, busy, t, onCreate }: Props) {
  if (!board && !installed) return null
  const linked = board !== null && !board.missing

  return (
    <section aria-labelledby="idea-board-title" className="space-y-2">
      <h3 id="idea-board-title" className="text-sm font-bold text-[#e8eef8]">{t("board_title")}</h3>
      {linked ? (
        <div className={"flex flex-wrap items-center gap-2 rounded-[6px] border px-3 py-2 " +
          "border-[rgb(var(--hh-s-rand,52_66_92))] bg-[rgb(var(--hh-s-tief,14_20_31))]"}>
          <PenTool size={14} aria-hidden className="shrink-0 text-[#69d7ff]" />
          <span className="min-w-0 flex-1 break-words text-[13px] font-semibold text-[#e8eef8]">{board.name}</span>
          {board.has_proposal && (
            <span className={`${BADGE} gap-1 border-[#69d7ff]/40 bg-[#69d7ff]/10 text-[#9fe6ff]`}>
              <Sparkles size={11} aria-hidden />{t("board_proposal")}
            </span>
          )}
          <Link to={`/blueprint?board=${board.id}`} className={BUTTON}>{t("board_open")}</Link>
        </div>
      ) : (
        <>
          {board?.missing && <p className="text-xs text-[#9aa7bc]">{t("board_missing")}</p>}
          {installed && (
            <div className="flex flex-wrap items-center gap-3">
              <button type="button" onClick={onCreate} disabled={busy} className={BUTTON}>
                <PenTool size={13} aria-hidden />{t("board_create")}
              </button>
              <p className="min-w-0 flex-1 text-[11px] text-[#9aa7bc]">{t("board_hint")}</p>
            </div>
          )}
        </>
      )}
    </section>
  )
}
