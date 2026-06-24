// Schach — Angriffs-Erkennung + pseudo-legale Zuggenerierung.
// Teil 1 der Engine (Teil 2: make/unmake/Legalität in engine.ts).
// 1:1-Port des ProjectX-Schach. squareAttacked läuft vom Feld AUSWÄRTS mit den
// Offsets jedes Figurentyps (billiger als alle Züge zu generieren).
import {
  B, BI, BISHOP_DIRS, idx, K, KNIGHT_OFFS, N, onBoard,
  P, Q, R, rankOf, ROOK_DIRS, ALL_DIRS, W, fileOf,
} from "./engine_types"
import type { Color, Move, State } from "./engine_types"

export function squareAttacked(state: State, sq: number, byColor: Color): boolean {
  const b = state.board
  const f = fileOf(sq), r = rankOf(sq)

  const pawnRank = r + byColor
  if (onBoard(f - 1, pawnRank) && b[idx(f - 1, pawnRank)] === byColor * P) return true
  if (onBoard(f + 1, pawnRank) && b[idx(f + 1, pawnRank)] === byColor * P) return true

  for (const [df, dr] of KNIGHT_OFFS) {
    const nf = f + df, nr = r + dr
    if (onBoard(nf, nr) && b[idx(nf, nr)] === byColor * N) return true
  }
  for (let df = -1; df <= 1; df++) for (let dr = -1; dr <= 1; dr++) {
    if (df === 0 && dr === 0) continue
    const nf = f + df, nr = r + dr
    if (onBoard(nf, nr) && b[idx(nf, nr)] === byColor * K) return true
  }
  for (const [df, dr] of ROOK_DIRS) {
    let nf = f + df, nr = r + dr
    while (onBoard(nf, nr)) {
      const p = b[idx(nf, nr)]
      if (p !== 0) { if (p === byColor * R || p === byColor * Q) return true; break }
      nf += df; nr += dr
    }
  }
  for (const [df, dr] of BISHOP_DIRS) {
    let nf = f + df, nr = r + dr
    while (onBoard(nf, nr)) {
      const p = b[idx(nf, nr)]
      if (p !== 0) { if (p === byColor * BI || p === byColor * Q) return true; break }
      nf += df; nr += dr
    }
  }
  return false
}

export function findKing(state: State, color: Color): number {
  const wanted = color * K
  for (let i = 0; i < 64; i++) if (state.board[i] === wanted) return i
  return -1
}

export function inCheck(state: State, color: Color): boolean {
  const k = findKing(state, color)
  return k >= 0 && squareAttacked(state, k, (-color) as Color)
}

// ---------- pseudo-legale Zuggenerierung ----------
function tryStep(b: Int8Array, from: number, nf: number, nr: number, color: Color, out: Move[]): void {
  if (!onBoard(nf, nr)) return
  const to = idx(nf, nr)
  const t = b[to]
  if (t === 0 || Math.sign(t) !== color) out.push({ from, to, promo: 0, ep: false, castle: "" })
}

function genSlide(b: Int8Array, from: number, f: number, r: number, color: Color, dirs: [number, number][], out: Move[]): void {
  for (const [df, dr] of dirs) {
    let nf = f + df, nr = r + dr
    while (onBoard(nf, nr)) {
      const to = idx(nf, nr)
      const t = b[to]
      if (t === 0) {
        out.push({ from, to, promo: 0, ep: false, castle: "" })
      } else {
        if (Math.sign(t) !== color) out.push({ from, to, promo: 0, ep: false, castle: "" })
        break
      }
      nf += df; nr += dr
    }
  }
}

function genPawn(state: State, from: number, color: Color, out: Move[]): void {
  const b = state.board
  const f = fileOf(from), r = rankOf(from)
  const dir = -color
  const startRank = color === W ? 6 : 1
  const promoRank = color === W ? 0 : 7

  const oneR = r + dir
  if (onBoard(f, oneR) && b[idx(f, oneR)] === 0) {
    if (oneR === promoRank) {
      out.push({ from, to: idx(f, oneR), promo: color * Q, ep: false, castle: "" })
    } else {
      out.push({ from, to: idx(f, oneR), promo: 0, ep: false, castle: "" })
      const twoR = r + 2 * dir
      if (r === startRank && b[idx(f, twoR)] === 0) {
        out.push({ from, to: idx(f, twoR), promo: 0, ep: false, castle: "" })
      }
    }
  }
  for (const df of [-1, 1]) {
    const nf = f + df, nr = r + dir
    if (!onBoard(nf, nr)) continue
    const to = idx(nf, nr)
    const t = b[to]
    if (t !== 0 && Math.sign(t) !== color) {
      out.push({ from, to, promo: nr === promoRank ? color * Q : 0, ep: false, castle: "" })
    } else if (to === state.ep) {
      out.push({ from, to, promo: 0, ep: true, castle: "" })
    }
  }
}

function genCastle(state: State, kingSq: number, color: Color, out: Move[]): void {
  if (inCheck(state, color)) return
  const b = state.board
  const rights = state.castle
  const r = color === W ? 7 : 0
  if (kingSq !== idx(4, r)) return

  const canK = color === W ? rights.wK : rights.bK
  if (canK && b[idx(5, r)] === 0 && b[idx(6, r)] === 0 && b[idx(7, r)] === color * R
    && !squareAttacked(state, idx(5, r), (-color) as Color) && !squareAttacked(state, idx(6, r), (-color) as Color)) {
    out.push({ from: kingSq, to: idx(6, r), promo: 0, ep: false, castle: "K" })
  }
  const canQ = color === W ? rights.wQ : rights.bQ
  if (canQ && b[idx(1, r)] === 0 && b[idx(2, r)] === 0 && b[idx(3, r)] === 0 && b[idx(0, r)] === color * R
    && !squareAttacked(state, idx(3, r), (-color) as Color) && !squareAttacked(state, idx(2, r), (-color) as Color)) {
    out.push({ from: kingSq, to: idx(2, r), promo: 0, ep: false, castle: "Q" })
  }
}

export function genMoves(state: State, color: Color): Move[] {
  const b = state.board
  const out: Move[] = []
  for (let i = 0; i < 64; i++) {
    const p = b[i]
    if (p === 0 || Math.sign(p) !== color) continue
    const type = Math.abs(p)
    const f = fileOf(i), r = rankOf(i)
    switch (type) {
      case P: genPawn(state, i, color, out); break
      case N: for (const [df, dr] of KNIGHT_OFFS) tryStep(b, i, f + df, r + dr, color, out); break
      case BI: genSlide(b, i, f, r, color, BISHOP_DIRS, out); break
      case R: genSlide(b, i, f, r, color, ROOK_DIRS, out); break
      case Q: genSlide(b, i, f, r, color, ALL_DIRS, out); break
      case K:
        for (let df = -1; df <= 1; df++) for (let dr = -1; dr <= 1; dr++) {
          if (df === 0 && dr === 0) continue
          tryStep(b, i, f + df, r + dr, color, out)
        }
        genCastle(state, i, color, out)
        break
    }
  }
  return out
}

export { B }
