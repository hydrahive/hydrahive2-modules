import { Trophy, X } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { createPortal } from "react-dom"
import { useTranslation } from "react-i18next"
import { boardgamesApi } from "../api"
import type { BoardGameModule, LeaderboardEntry } from "../types"

interface Props {
  game: BoardGameModule
  onClose: () => void
}

/** Vollbild-Overlay (Portal). ESC schließt. Hostet die Spiel-Komponente +
 *  globale Bestenliste (meiste Siege). */
export function BoardGameOverlay({ game, onClose }: Props) {
  const { t } = useTranslation("boardgames")
  const [board, setBoard] = useState<LeaderboardEntry[]>([])
  const Game = game.component

  const loadBoard = useCallback(async () => {
    try { setBoard(await boardgamesApi.leaderboard(game.meta.id)) } catch { /* ignore */ }
  }, [game.meta.id])

  useEffect(() => { void loadBoard() }, [loadBoard])

  useEffect(() => {
    function onKey(e: KeyboardEvent) { if (e.key === "Escape") onClose() }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4 overflow-auto">
      <div className="relative flex flex-col lg:flex-row gap-6 items-start">
        <button onClick={onClose} aria-label={t("bg_close")}
          className="absolute -top-2 -right-2 lg:-right-10 z-10 p-2 rounded-full bg-[rgb(var(--hh-s-innen,17_24_39))] text-[#c8d2df] hover:text-white hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] transition-colors">
          <X size={18} />
        </button>

        <div className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32)/0.6)]">
          <Game onExit={onClose} />
        </div>

        <div className="w-full lg:w-56 rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-3">
          <div className="flex items-center gap-1.5 mb-2 text-[#c8d2df]">
            <Trophy size={14} className="text-amber-300" />
            <span className="text-sm font-semibold">{t("bg_leaderboard")}</span>
          </div>
          {board.length === 0 ? (
            <p className="text-[11px] text-[#9aa7bc]">{t("bg_no_wins")}</p>
          ) : (
            <ol className="space-y-1">
              {board.map((e) => (
                <li key={e.rank} className="flex items-center gap-2 text-xs">
                  <span className="w-4 text-right text-[#9aa7bc] tabular-nums">{e.rank}</span>
                  <span className="truncate text-[#c8d2df]">{e.user}</span>
                  <span className="ml-auto tabular-nums text-[#e8eef8]">{e.wins} {t("bg_wins_short")}</span>
                </li>
              ))}
            </ol>
          )}
          <p className="mt-2 text-[10px] text-[#9aa7bc]">{t("bg_leaderboard_hint")}</p>
        </div>
      </div>
    </div>,
    document.body,
  )
}
