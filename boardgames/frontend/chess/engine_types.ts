// Schach-Engine — Typen, Konstanten, Koordinaten-Helfer.
// Portiert aus dem ProjectX-Schach (reines JS → TypeScript), unverändert in der
// Logik. board[i]: signed piece code, index 0 = a8, 63 = h1.

export const W = 1
export const B = -1
export const P = 1, N = 2, BI = 3, R = 4, Q = 5, K = 6

export type Color = 1 | -1

export interface Move {
  from: number
  to: number
  promo: number      // Figuren-Code für Umwandlung, 0 sonst
  ep: boolean         // En-Passant-Schlag
  castle: "" | "K" | "Q"
}

export interface CastleRights { wK: boolean; wQ: boolean; bK: boolean; bQ: boolean }

interface HistEntry {
  mv: Move
  captured: number
  prevCastle: CastleRights
  prevEP: number
  prevHalf: number
  epCapturedSq: number
  epCapturedPiece: number
  rookFrom: number
  rookTo: number
  rookPiece: number
}

export interface State {
  board: Int8Array
  turn: Color
  castle: CastleRights
  ep: number          // En-Passant-Zielfeld-Index, -1 = keins
  halfmove: number
  fullmove: number
  history: HistEntry[]
}

export const START = (): State => ({
  board: new Int8Array([
    -R, -N, -BI, -Q, -K, -BI, -N, -R,
    -P, -P, -P, -P, -P, -P, -P, -P,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    0, 0, 0, 0, 0, 0, 0, 0,
    P, P, P, P, P, P, P, P,
    R, N, BI, Q, K, BI, N, R,
  ]),
  turn: W,
  castle: { wK: true, wQ: true, bK: true, bQ: true },
  ep: -1,
  halfmove: 0,
  fullmove: 1,
  history: [],
})

// ---------- Koordinaten-Helfer ----------
export const fileOf = (i: number): number => i & 7
export const rankOf = (i: number): number => i >> 3
export const sqName = (i: number): string => "abcdefgh"[fileOf(i)] + (8 - rankOf(i))
export const onBoard = (f: number, r: number): boolean => f >= 0 && f < 8 && r >= 0 && r < 8
export const idx = (f: number, r: number): number => r * 8 + f

// ---------- Figuren-Glyphen für die UI ----------
export const GLYPHS: Record<number, string> = {
  [P]: "♙", [N]: "♘", [BI]: "♗", [R]: "♖", [Q]: "♕", [K]: "♔",
  [-P]: "♟", [-N]: "♞", [-BI]: "♝", [-R]: "♜", [-Q]: "♛", [-K]: "♚",
  0: "",
}

export const KNIGHT_OFFS: [number, number][] = [[1, 2], [2, 1], [2, -1], [1, -2], [-1, -2], [-2, -1], [-2, 1], [-1, 2]]
export const ROOK_DIRS: [number, number][] = [[1, 0], [-1, 0], [0, 1], [0, -1]]
export const BISHOP_DIRS: [number, number][] = [[1, 1], [1, -1], [-1, 1], [-1, -1]]
export const ALL_DIRS: [number, number][] = ROOK_DIRS.concat(BISHOP_DIRS)
