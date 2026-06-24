// Serialisierung für den LLM-Gegner: Move → UCI, State → FEN.
// Reine Lese-Funktionen, keine Spiel-Logik (die bleibt in engine.ts/movegen.ts).
import { BI, K, N, P, Q, R, sqName, W } from "./engine_types"
import type { Move, State } from "./engine_types"

// Promotion-Code → UCI-Suffix (klein, immer aus Sicht der Figur).
const PROMO_CHAR: Record<number, string> = { [Q]: "q", [R]: "r", [BI]: "b", [N]: "n" }

/** Move → UCI, z.B. "e2e4", "e7e8q", "e1g1" (Rochade als König-Zug). */
export function toUci(mv: Move): string {
  const promo = mv.promo !== 0 ? (PROMO_CHAR[Math.abs(mv.promo)] ?? "") : ""
  return sqName(mv.from) + sqName(mv.to) + promo
}

// Piece-Code → FEN-Buchstabe (Großbuchstaben Weiß, Kleinbuchstaben Schwarz).
const FEN_LETTER: Record<number, string> = {
  [P]: "P", [N]: "N", [BI]: "B", [R]: "R", [Q]: "Q", [K]: "K",
}

function pieceLetter(code: number): string {
  const base = FEN_LETTER[Math.abs(code)] ?? ""
  return code < 0 ? base.toLowerCase() : base
}

function castleField(s: State): string {
  let out = ""
  if (s.castle.wK) out += "K"
  if (s.castle.wQ) out += "Q"
  if (s.castle.bK) out += "k"
  if (s.castle.bQ) out += "q"
  return out || "-"
}

/** State → FEN-String (Stellung als Kontext fürs LLM). board: 0=a8 … 63=h1. */
export function fenOf(s: State): string {
  const rows: string[] = []
  for (let r = 0; r < 8; r++) {
    let row = "", empty = 0
    for (let f = 0; f < 8; f++) {
      const code = s.board[r * 8 + f]
      if (code === 0) { empty++; continue }
      if (empty > 0) { row += String(empty); empty = 0 }
      row += pieceLetter(code)
    }
    if (empty > 0) row += String(empty)
    rows.push(row)
  }
  const placement = rows.join("/")
  const active = s.turn === W ? "w" : "b"
  const ep = s.ep >= 0 ? sqName(s.ep) : "-"
  return `${placement} ${active} ${castleField(s)} ${ep} ${s.halfmove} ${s.fullmove}`
}
