import { api } from "@/shared/api-client"
import type { LeaderboardEntry, MyScores, SubmitResult } from "./types"

const BASE = "/modules/minigames"

export const minigamesApi = {
  submitScore: (gameId: string, score: number): Promise<SubmitResult> =>
    api.post<SubmitResult>(`${BASE}/scores`, { game_id: gameId, score }),

  myScores: (gameId: string): Promise<MyScores> =>
    api.get<MyScores>(`${BASE}/scores/mine?game_id=${encodeURIComponent(gameId)}`),

  leaderboard: (gameId: string, limit = 10): Promise<LeaderboardEntry[]> =>
    api.get<LeaderboardEntry[]>(
      `${BASE}/scores/leaderboard?game_id=${encodeURIComponent(gameId)}&limit=${limit}`,
    ),
}
