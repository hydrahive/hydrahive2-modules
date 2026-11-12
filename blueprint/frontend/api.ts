import { api } from "@/shared/api-client"
import type { Board, BoardListItem, BoardPatch, BoardState, BoardVersion } from "./types"

const BASE = "/modules/blueprint"

export const blueprintApi = {
  list: (): Promise<BoardListItem[]> => api.get<BoardListItem[]>(`${BASE}/boards`),

  get: (id: number): Promise<Board> => api.get<Board>(`${BASE}/boards/${id}`),

  /** Leichte Abfrage: Zähler der Fassung und Zeit des Vorschlags, ohne den Graphen. */
  state: (id: number): Promise<BoardState> => api.get<BoardState>(`${BASE}/boards/${id}/state`),

  create: (name: string, project_id: string | null = null): Promise<Board> =>
    api.post<Board>(`${BASE}/boards`, { name, project_id }),

  update: (id: number, patch: BoardPatch): Promise<Board> => api.put<Board>(`${BASE}/boards/${id}`, patch),

  remove: (id: number): Promise<{ removed: boolean }> =>
    api.delete<{ removed: boolean }>(`${BASE}/boards/${id}`),

  /** proposal_at: Zeit des Vorschlags, den der Nutzer vor sich hat. Wurde er ersetzt, lehnt der Server ab. */
  acceptProposal: (id: number, proposal_at: string | null): Promise<Board> =>
    api.post<Board>(`${BASE}/boards/${id}/proposal/accept`, { proposal_at }),

  discardProposal: (id: number): Promise<Board> => api.delete<Board>(`${BASE}/boards/${id}/proposal`),

  versions: (id: number): Promise<BoardVersion[]> => api.get<BoardVersion[]>(`${BASE}/boards/${id}/versions`),

  restoreVersion: (id: number, versionId: number): Promise<Board> =>
    api.post<Board>(`${BASE}/boards/${id}/versions/${versionId}/restore`, {}),
}
