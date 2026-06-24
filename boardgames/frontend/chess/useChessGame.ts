// Schach-Spielzustand als Hook: kapselt Brett-State, Zug-Logik, KI-Trigger,
// Modus (Hotseat / vs KI) und Ergebnis-Meldung. Die View rendert nur.
import { useCallback, useEffect, useRef, useState } from "react"
import { boardgamesApi } from "../api"
import type { GameMode, GameResult } from "../types"
import { applyMove, legalMoves, outcome } from "./engine"
import { START, W } from "./engine_types"
import type { Color, Move, State } from "./engine_types"
import { bestMove } from "./minimax"

export interface ChessUI {
  board: Int8Array
  turn: Color
  selected: number
  legalTargets: number[]
  status: "playing" | "checkmate" | "stalemate"
  winner: Color | 0
  thinking: boolean
  lastMove: { from: number; to: number } | null
  onSquare: (sq: number) => void
  reset: () => void
}

const AI_DEPTH = 3
const AI_SIDE: Color = -1 as Color  // KI spielt Schwarz, Mensch Weiß

export function useChessGame(mode: GameMode): ChessUI {
  const stateRef = useRef<State>(START())
  const [, force] = useState(0)
  const rerender = useCallback(() => force((n) => n + 1), [])

  const [selected, setSelected] = useState(-1)
  const [legalTargets, setLegalTargets] = useState<number[]>([])
  const [thinking, setThinking] = useState(false)
  const [lastMove, setLastMove] = useState<{ from: number; to: number } | null>(null)
  const reportedRef = useRef(false)

  const s = stateRef.current
  const oc = outcome(s)
  const status = oc === "ongoing" ? "playing" : oc
  // Bei Matt hat die Seite am Zug verloren → Gewinner ist die andere.
  const winner: Color | 0 = oc === "checkmate" ? ((-s.turn) as Color) : 0

  // Ergebnis genau einmal melden (nur vs KI; Hotseat zählt nicht in die Bilanz).
  useEffect(() => {
    if (status === "playing" || reportedRef.current) return
    reportedRef.current = true
    if (mode === "ai") {
      let result: GameResult = "draw"
      if (status === "checkmate") result = winner === W ? "win" : "loss"
      void boardgamesApi.submitResult("chess", "ai", result).catch(() => {})
    }
  }, [status, winner, mode])

  const doMove = useCallback((mv: Move) => {
    applyMove(stateRef.current, mv)
    setLastMove({ from: mv.from, to: mv.to })
    setSelected(-1)
    setLegalTargets([])
    rerender()
  }, [rerender])

  // KI ziehen lassen, wenn sie dran ist (nur Modus "ai").
  useEffect(() => {
    if (mode !== "ai" || status !== "playing") return
    if (stateRef.current.turn !== AI_SIDE) return
    setThinking(true)
    const t = setTimeout(() => {
      const mv = bestMove(stateRef.current, AI_DEPTH)
      if (mv) doMove(mv)
      setThinking(false)
    }, 350)
    return () => clearTimeout(t)
  }, [mode, status, lastMove, doMove])

  const onSquare = useCallback((sq: number) => {
    const st = stateRef.current
    if (status !== "playing" || thinking) return
    if (mode === "ai" && st.turn === AI_SIDE) return

    const piece = st.board[sq]
    // Zielfeld eines selektierten Steins?
    if (selected >= 0) {
      const moves = legalMoves(st, st.turn).filter((m) => m.from === selected && m.to === sq)
      if (moves.length > 0) { doMove(moves[0]); return }
    }
    // Eigene Figur selektieren
    if (piece !== 0 && Math.sign(piece) === st.turn) {
      setSelected(sq)
      setLegalTargets(legalMoves(st, st.turn).filter((m) => m.from === sq).map((m) => m.to))
    } else {
      setSelected(-1)
      setLegalTargets([])
    }
  }, [selected, status, thinking, mode, doMove])

  const reset = useCallback(() => {
    stateRef.current = START()
    setSelected(-1)
    setLegalTargets([])
    setLastMove(null)
    setThinking(false)
    reportedRef.current = false
    rerender()
  }, [rerender])

  return {
    board: s.board, turn: s.turn, selected, legalTargets,
    status, winner, thinking, lastMove, onSquare, reset,
  }
}
