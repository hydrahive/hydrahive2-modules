// Brettspiele — gemeinsame Typen: Spiel-Registry + Ergebnis-API.
import type { ComponentType } from "react"

export type GameMode = "hotseat" | "ai" | "llm"
export type GameResult = "win" | "loss" | "draw"

/** Props, die jede Spiel-Komponente vom Overlay bekommt. */
export interface BoardGameProps {
  onExit: () => void
}

export interface BoardGameMeta {
  id: string                 // "chess" — muss zur Server-Whitelist passen
  titleKey: string           // i18n-Key
  icon: string               // lucide-Icon-Name
  accent: string             // rgb-Tripel
}

/** Ein einbaubares Brettspiel: Metadaten + eigene React-Komponente. */
export interface BoardGameModule {
  meta: BoardGameMeta
  component: ComponentType<BoardGameProps>
}

// ---------------------------------------------------------------- Ergebnis-API
export interface MyRecord {
  win: number
  loss: number
  draw: number
  total: number
}

export interface LeaderboardEntry {
  rank: number
  user: string
  wins: number
  games: number
}

// ----------------------------------------------------------------- LLM-Gegner
/** Eintrag aus GET /api/llm/models (auf das Nötige reduziert). */
export interface LlmModel {
  id: string
  label: string
  provider: string
  is_free: boolean
}

/** Antwort von POST /chess/llm-move. move=null → Frontend nutzt Minimax-Fallback. */
export interface LlmMoveResult {
  move: string | null
  index: number
  source: "llm" | "invalid"
}
