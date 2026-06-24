// Schach-KI — Minimax mit Alpha-Beta-Pruning + Material/Positions-Bewertung.
// Bewusst kompakt: spielt vernünftig (kein Gratis-Abtausch, sucht Matt), aber
// kein Stockfish. Tiefe konfigurierbar (Schwierigkeit). Nutzt die Engine als
// Regel-Autorität (legalMoves/applyMove/unmake).
import { applyMove, legalMoves, outcome, unmake } from "./engine"
import { B, BI, K, N, P, Q, R, W } from "./engine_types"
import type { Color, Move, State } from "./engine_types"

// Figuren-Grundwerte (Bauer = 100)
const VAL: Record<number, number> = { [P]: 100, [N]: 320, [BI]: 330, [R]: 500, [Q]: 900, [K]: 20000 }

// Piece-Square-Table (Bauer), aus Weiß-Sicht; index 0 = a8 … 63 = h1.
// Fördert Zentrum + Vorrücken. Für andere Figuren genügt eine simple Variante.
const PST_PAWN = [
  0, 0, 0, 0, 0, 0, 0, 0,
  50, 50, 50, 50, 50, 50, 50, 50,
  10, 10, 20, 30, 30, 20, 10, 10,
  5, 5, 10, 25, 25, 10, 5, 5,
  0, 0, 0, 20, 20, 0, 0, 0,
  5, -5, -10, 0, 0, -10, -5, 5,
  5, 10, 10, -20, -20, 10, 10, 5,
  0, 0, 0, 0, 0, 0, 0, 0,
]
const PST_KNIGHT = [
  -50, -40, -30, -30, -30, -30, -40, -50,
  -40, -20, 0, 0, 0, 0, -20, -40,
  -30, 0, 10, 15, 15, 10, 0, -30,
  -30, 5, 15, 20, 20, 15, 5, -30,
  -30, 0, 15, 20, 20, 15, 0, -30,
  -30, 5, 10, 15, 15, 10, 5, -30,
  -40, -20, 0, 5, 5, 0, -20, -40,
  -50, -40, -30, -30, -30, -30, -40, -50,
]

function pst(type: number, sq: number, color: Color): number {
  // Für Schwarz das Feld spiegeln (PST ist aus Weiß-Sicht).
  const i = color === W ? sq : 63 - sq
  if (type === P) return PST_PAWN[i]
  if (type === N) return PST_KNIGHT[i]
  return 0
}

// Statische Bewertung aus Sicht von Weiß (positiv = gut für Weiß).
function evaluate(state: State): number {
  let score = 0
  for (let i = 0; i < 64; i++) {
    const p = state.board[i]
    if (p === 0) continue
    const color = (Math.sign(p)) as Color
    const type = Math.abs(p)
    score += color * (VAL[type] + pst(type, i, color))
  }
  return score
}

function search(state: State, depth: number, alpha: number, beta: number, color: Color): number {
  if (depth === 0) return color * evaluate(state)

  const moves = legalMoves(state, state.turn)
  if (moves.length === 0) {
    // Matt (sehr schlecht, näher = schlimmer) oder Patt (0)
    return outcome(state) === "checkmate" ? -100000 - depth : 0
  }

  let best = -Infinity
  for (const mv of moves) {
    applyMove(state, mv)
    const val = -search(state, depth - 1, -beta, -alpha, (-color) as Color)
    unmake(state)
    if (val > best) best = val
    if (best > alpha) alpha = best
    if (alpha >= beta) break   // Beta-Cutoff
  }
  return best
}

/** Besten Zug für die Seite am Zug suchen. depth 1..4 (Default 3). */
export function bestMove(state: State, depth = 3): Move | null {
  const moves = legalMoves(state, state.turn)
  if (moves.length === 0) return null

  const color = state.turn
  let best: Move | null = null
  let bestVal = -Infinity
  let alpha = -Infinity
  const beta = Infinity

  // Leichte Zufallskomponente bei Gleichstand → nicht immer identische Partie.
  const shuffled = moves
    .map((m) => ({ m, k: Math.random() }))
    .sort((a, b) => a.k - b.k)
    .map((x) => x.m)

  for (const mv of shuffled) {
    applyMove(state, mv)
    const val = -search(state, depth - 1, -beta, -alpha, (-color) as Color)
    unmake(state)
    if (val > bestVal) { bestVal = val; best = mv }
    if (bestVal > alpha) alpha = bestVal
  }
  return best
}

export { B, W }
