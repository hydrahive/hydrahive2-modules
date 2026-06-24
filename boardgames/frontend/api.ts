import { api } from "@/shared/api-client"
import type { GameMode, GameResult, LeaderboardEntry, LlmModel, LlmMoveResult, MyRecord } from "./types"

const BASE = "/modules/boardgames"

export const boardgamesApi = {
  submitResult: (gameId: string, mode: GameMode, result: GameResult, opponent = ""): Promise<{ ok: boolean }> =>
    api.post<{ ok: boolean }>(`${BASE}/results`, { game_id: gameId, mode, result, opponent }),

  myRecord: (gameId: string, mode?: GameMode): Promise<MyRecord> =>
    api.get<MyRecord>(`${BASE}/results/mine?game_id=${encodeURIComponent(gameId)}${mode ? `&mode=${mode}` : ""}`),

  leaderboard: (gameId: string, limit = 10): Promise<LeaderboardEntry[]> =>
    api.get<LeaderboardEntry[]>(`${BASE}/results/leaderboard?game_id=${encodeURIComponent(gameId)}&limit=${limit}`),

  /** Chat-Modelle aus dem zentralen Katalog (für die Gegner-Auswahl). */
  listModels: (): Promise<{ default: string; models: LlmModel[] }> =>
    api.get<{ default: string; models: LlmModel[] }>("/llm/models?modality=chat"),

  /** Lässt das gewählte Modell einen Zug aus `moves` (UCI) wählen. */
  llmMove: (model: string, fen: string, moves: string[], history: string[]): Promise<LlmMoveResult> =>
    api.post<LlmMoveResult>(`${BASE}/chess/llm-move`, { model, fen, moves, history }),
}
