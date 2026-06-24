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
          className="absolute -top-2 -right-2 lg:-right-10 z-10 p-2 rounded-full bg-white/[6%] text-zinc-400 hover:text-white hover:bg-white/[12%] transition-colors">
          <X size={18} />
        </button>

        <div className="rounded-xl border border-white/[8%] bg-zinc-950/60">
          <Game onExit={onClose} />
        </div>

        <div className="w-full lg:w-56 rounded-xl border border-white/[8%] bg-white/[3%] p-3">
          <div className="flex items-center gap-1.5 mb-2 text-zinc-300">
            <Trophy size={14} className="text-amber-300" />
            <span className="text-sm font-semibold">{t("bg_leaderboard")}</span>
          </div>
          {board.length === 0 ? (
            <p className="text-[11px] text-zinc-600">{t("bg_no_wins")}</p>
          ) : (
            <ol className="space-y-1">
              {board.map((e) => (
                <li key={e.rank} className="flex items-center gap-2 text-xs">
                  <span className="w-4 text-right text-zinc-600 tabular-nums">{e.rank}</span>
                  <span className="truncate text-zinc-300">{e.user}</span>
                  <span className="ml-auto tabular-nums text-zinc-100">{e.wins} {t("bg_wins_short")}</span>
                </li>
              ))}
            </ol>
          )}
          <p className="mt-2 text-[10px] text-zinc-600">{t("bg_leaderboard_hint")}</p>
        </div>
      </div>
    </div>,
    document.body,
  )
}
