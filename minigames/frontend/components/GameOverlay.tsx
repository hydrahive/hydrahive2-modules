import { Trophy, X } from "lucide-react"
import { useCallback, useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { useTranslation } from "react-i18next"
import { minigamesApi } from "../api"
import type { GameModule, LeaderboardEntry } from "../types"
import { GameCanvas } from "./GameCanvas"

interface Props {
  game: GameModule
  onClose: () => void
}

/** Vollbild-Spiel-Overlay (Portal). ESC oder Button schließt. Submittet Score
 *  bei Game-Over und zeigt die globale Bestenliste. */
export function GameOverlay({ game, onClose }: Props) {
  const { t } = useTranslation("minigames")
  const [score, setScore] = useState(0)
  const [best, setBest] = useState<LeaderboardEntry[]>([])
  const [pb, setPb] = useState(false)
  const submittingRef = useRef(false)

  const loadBoard = useCallback(async () => {
    try { setBest(await minigamesApi.leaderboard(game.meta.id)) } catch { /* ignore */ }
  }, [game.meta.id])

  useEffect(() => { void loadBoard() }, [loadBoard])

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  const onGameOver = useCallback(async (finalScore: number) => {
    if (submittingRef.current) return
    submittingRef.current = true
    try {
      const res = await minigamesApi.submitScore(game.meta.id, finalScore)
      setPb(res.is_personal_best)
      await loadBoard()
    } catch { /* ignore */ } finally {
      submittingRef.current = false
    }
  }, [game.meta.id, loadBoard])

  const onScore = useCallback((s: number) => {
    setScore(s)
    if (s === 0) setPb(false)
  }, [])

  return createPortal(
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/85 backdrop-blur-sm p-4">
      <div className="relative flex flex-col lg:flex-row gap-6 items-start">
        <button
          onClick={onClose}
          aria-label={t("mg_close")}
          className="absolute -top-2 -right-2 lg:-right-10 z-10 p-2 rounded-full bg-white/[6%] text-zinc-400 hover:text-white hover:bg-white/[12%] transition-colors"
        >
          <X size={18} />
        </button>

        <div className="flex flex-col items-center gap-3">
          <div className="flex items-center gap-4 w-full">
            <h2 className="text-lg font-bold text-zinc-100">{t(game.meta.titleKey)}</h2>
            <span className="ml-auto tabular-nums text-2xl font-bold" style={{ color: `rgb(${game.meta.accent})` }}>
              {score}
            </span>
            {pb && <span className="text-[11px] font-medium text-amber-300">★ {t("mg_personal_best")}</span>}
          </div>
          <GameCanvas game={game} onScore={onScore} onGameOver={onGameOver} />
          <p className="text-[11px] text-zinc-500">{t("mg_controls_hint")}</p>
        </div>

        <div className="w-full lg:w-56 rounded-xl border border-white/[8%] bg-white/[3%] p-3">
          <div className="flex items-center gap-1.5 mb-2 text-zinc-300">
            <Trophy size={14} className="text-amber-300" />
            <span className="text-sm font-semibold">{t("mg_leaderboard")}</span>
          </div>
          {best.length === 0 ? (
            <p className="text-[11px] text-zinc-600">{t("mg_no_scores")}</p>
          ) : (
            <ol className="space-y-1">
              {best.map((e) => (
                <li key={e.rank} className="flex items-center gap-2 text-xs">
                  <span className="w-4 text-right text-zinc-600 tabular-nums">{e.rank}</span>
                  <span className="truncate text-zinc-300">{e.user}</span>
                  <span className="ml-auto tabular-nums text-zinc-100">{e.score}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>
    </div>,
    document.body,
  )
}
