import { api } from "@/shared/api-client"
import type { DraftCreate, DraftPatch, GameDraft, GameStudioOverview } from "./types"

const BASE = "/modules/game-studio"

export const gameStudioApi = {
  overview: (): Promise<GameStudioOverview> => api.get<GameStudioOverview>(`${BASE}/overview`),
  draft: (draftId: string): Promise<GameDraft> => api.get<GameDraft>(`${BASE}/drafts/${draftId}`),
  createDraft: (body: DraftCreate): Promise<GameDraft> => api.post<GameDraft>(`${BASE}/drafts`, body),
  updateDraft: (draftId: string, body: DraftPatch): Promise<GameDraft> =>
    api.patch<GameDraft>(`${BASE}/drafts/${draftId}`, body),
}
