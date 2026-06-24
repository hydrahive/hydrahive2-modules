// Schach-Spielzustand als Hook: kapselt Brett-State, Zug-Logik, KI-Trigger,
// Modus (Hotseat / vs Minimax / vs LLM) und Ergebnis-Meldung. Die View rendert nur.
import { useCallback, useEffect, useRef, useState } from "react"
import { boardgamesApi } from "../api"
import type { GameMode, GameResult } from "../types"
import { applyMove, legalMoves, outcome } from "./engine"
import { START, W } from "./engine_types"
import type { Color, Move, State } from "./engine_types"
import { bestMove } from "./minimax"
import { fenOf, toUci } from "./uci"

export interface ChessUI {
  board: Int8Array
  turn: Color
  selected: number
  legalTargets: number[]
  status: "playing" | "checkmate" | "stalemate"
  winner: Color | 0
  thinking: boolean
  lastMove: { from: number; to: number } | null
  moveSource: "llm" | "fallback" | null
  onSquare: (sq: number) => void
  reset: () => void
}

const AI_DEPTH = 3
const AI_SIDE: Color = -1 as Color  // KI/LLM spielt Schwarz, Mensch Weiß

export function useChessGame(mode: GameMode, model?: string): ChessUI {
  const stateRef = useRef<State>(START())
  const historyRef = useRef<string[]>([])      // bisher gespielte Züge als UCI
  const [, force] = useState(0)
  const rerender = useCallback(() => force((n) => n + 1), [])

  const [selected, setSelected] = useState(-1)
  const [legalTargets, setLegalTargets] = useState<number[]>([])
  const [thinking, setThinking] = useState(false)
  const [lastMove, setLastMove] = useState<{ from: number; to: number } | null>(null)
  const [moveSource, setMoveSource] = useState<"llm" | "fallback" | null>(null)
  const reportedRef = useRef(false)

  const s = stateRef.current
  const oc = outcome(s)
  const status = oc === "ongoing" ? "playing" : oc
  // Bei Matt hat die Seite am Zug verloren → Gewinner ist die andere.
  const winner: Color | 0 = oc === "checkmate" ? ((-s.turn) as Color) : 0
  const aiMode = mode === "ai" || mode === "llm"

  // Ergebnis genau einmal melden (nur vs KI/LLM; Hotseat zählt nicht in die Bilanz).
  useEffect(() => {
    if (status === "playing" || reportedRef.current) return
    reportedRef.current = true
    if (!aiMode) return
    let result: GameResult = "draw"
    if (status === "checkmate") result = winner === W ? "win" : "loss"
    const opponent = mode === "llm" ? (model ?? "") : ""
    void boardgamesApi.submitResult("chess", mode, result, opponent).catch(() => {})
  }, [status, winner, mode, aiMode, model])

  const doMove = useCallback((mv: Move) => {
    historyRef.current.push(toUci(mv))
    applyMove(stateRef.current, mv)
    setLastMove({ from: mv.from, to: mv.to })
    setSelected(-1)
    setLegalTargets([])
    rerender()
  }, [rerender])

  // Wählt den KI-Zug: bei "llm" das Modell (mit Minimax-Fallback), sonst Minimax.
  const pickAiMove = useCallback(async (st: State, moves: Move[]): Promise<{ mv: Move; src: "llm" | "fallback" }> => {
    if (mode === "llm" && model) {
      try {
        const uci = moves.map(toUci)
        const res = await boardgamesApi.llmMove(model, fenOf(st), uci, historyRef.current)
        if (res.move) {
          const hit = moves.find((m) => toUci(m) === res.move)
          if (hit) return { mv: hit, src: "llm" }
        }
      } catch {
        // Netz-/Serverfehler → Fallback unten
      }
      const fb = bestMove(st, AI_DEPTH)
      return { mv: fb ?? moves[0], src: "fallback" }
    }
    const mv = bestMove(st, AI_DEPTH)
    return { mv: mv ?? moves[0], src: "fallback" }
  }, [mode, model])

  // KI/LLM ziehen lassen, wenn sie dran ist.
  useEffect(() => {
    if (!aiMode || status !== "playing") return
    const st = stateRef.current
    if (st.turn !== AI_SIDE) return
    let cancelled = false
    setThinking(true)
    const moves = legalMoves(st, st.turn)
    if (moves.length === 0) { setThinking(false); return }
    void pickAiMove(st, moves).then(({ mv, src }) => {
      if (cancelled) return
      setMoveSource(src)
      doMove(mv)
      setThinking(false)
    })
    return () => { cancelled = true }
  }, [aiMode, status, lastMove, doMove, pickAiMove])

  const onSquare = useCallback((sq: number) => {
    const st = stateRef.current
    if (status !== "playing" || thinking) return
    if (aiMode && st.turn === AI_SIDE) return

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
  }, [selected, status, thinking, aiMode, doMove])

  const reset = useCallback(() => {
    stateRef.current = START()
    historyRef.current = []
    setSelected(-1)
    setLegalTargets([])
    setLastMove(null)
    setMoveSource(null)
    setThinking(false)
    reportedRef.current = false
    rerender()
  }, [rerender])

  return {
    board: s.board, turn: s.turn, selected, legalTargets,
    status, winner, thinking, lastMove, moveSource, onSquare, reset,
  }
}
