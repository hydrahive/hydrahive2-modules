// Schach-Engine — make/unmake, Legalitätsfilter, Spielausgang.
// Teil 2 der Engine (Teil 1: Angriff/Zuggenerierung in movegen.ts).
// 1:1-Port des ProjectX-Schach. legalMoves filtert pseudo-legale Züge per
// make/unmake auf King-Safety.
import { B, idx, K, P, R, rankOf, W } from "./engine_types"
import type { Color, Move, State } from "./engine_types"
import { genMoves, inCheck } from "./movegen"

export { findKing, inCheck } from "./movegen"

// ---------- make / unmake ----------
export function applyMove(state: State, mv: Move): void {
  const b = state.board
  const moving = b[mv.from]
  const captured = b[mv.to]
  const prevCastle = { ...state.castle }
  const prevEP = state.ep
  const prevHalf = state.halfmove

  let epCapturedSq = -1, epCapturedPiece = 0
  let rookFrom = -1, rookTo = -1, rookPiece = 0

  if (mv.ep) {
    epCapturedSq = mv.to + (state.turn === W ? 8 : -8)
    epCapturedPiece = b[epCapturedSq]
    b[epCapturedSq] = 0
  }
  if (mv.castle === "K") {
    const r = state.turn === W ? 7 : 0
    rookFrom = idx(7, r); rookTo = idx(5, r); rookPiece = b[rookFrom]
    b[rookTo] = rookPiece; b[rookFrom] = 0
  } else if (mv.castle === "Q") {
    const r = state.turn === W ? 7 : 0
    rookFrom = idx(0, r); rookTo = idx(3, r); rookPiece = b[rookFrom]
    b[rookTo] = rookPiece; b[rookFrom] = 0
  }

  b[mv.to] = mv.promo !== 0 ? mv.promo : moving
  b[mv.from] = 0

  const movingType = Math.abs(moving)
  if (movingType === K) {
    if (state.turn === W) { state.castle.wK = false; state.castle.wQ = false }
    else { state.castle.bK = false; state.castle.bQ = false }
  } else if (movingType === R) {
    if (mv.from === idx(0, 7)) state.castle.wQ = false
    if (mv.from === idx(7, 7)) state.castle.wK = false
    if (mv.from === idx(0, 0)) state.castle.bQ = false
    if (mv.from === idx(7, 0)) state.castle.bK = false
  }
  if (mv.to === idx(0, 7)) state.castle.wQ = false
  if (mv.to === idx(7, 7)) state.castle.wK = false
  if (mv.to === idx(0, 0)) state.castle.bQ = false
  if (mv.to === idx(7, 0)) state.castle.bK = false

  if (movingType === P && Math.abs(rankOf(mv.to) - rankOf(mv.from)) === 2) {
    state.ep = (mv.from + mv.to) / 2
  } else {
    state.ep = -1
  }

  if (movingType === P || captured !== 0 || mv.ep) state.halfmove = 0
  else state.halfmove++

  if (state.turn === B) state.fullmove++
  state.turn = (-state.turn) as Color

  state.history.push({ mv, captured, prevCastle, prevEP, prevHalf, epCapturedSq, epCapturedPiece, rookFrom, rookTo, rookPiece })
}

export function unmake(state: State): void {
  const h = state.history.pop()
  if (!h) return
  const b = state.board
  state.turn = (-state.turn) as Color
  if (state.turn === B) state.fullmove--

  const movingNow = b[h.mv.to]
  const wasPromo = h.mv.promo !== 0
  b[h.mv.from] = wasPromo ? state.turn * P : movingNow
  b[h.mv.to] = h.captured

  if (h.mv.ep) b[h.epCapturedSq] = h.epCapturedPiece
  if (h.mv.castle) { b[h.rookFrom] = h.rookPiece; b[h.rookTo] = 0 }
  state.castle = h.prevCastle
  state.ep = h.prevEP
  state.halfmove = h.prevHalf
}

export function legalMoves(state: State, color: Color): Move[] {
  const out: Move[] = []
  for (const mv of genMoves(state, color)) {
    applyMove(state, mv)
    if (!inCheck(state, color)) out.push(mv)
    unmake(state)
  }
  return out
}

export type Outcome = "checkmate" | "stalemate" | "ongoing"

export function outcome(state: State): Outcome {
  const moves = legalMoves(state, state.turn)
  if (moves.length > 0) return "ongoing"
  return inCheck(state, state.turn) ? "checkmate" : "stalemate"
}
