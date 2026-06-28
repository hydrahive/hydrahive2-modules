import { api } from "@/shared/api-client"
import type { Board, BoardMeta } from "./types"

const BASE = "/modules/blueprint"

export const blueprintApi = {
  list: (): Promise<BoardMeta[]> => api.get<BoardMeta[]>(`${BASE}/boards`),

  get: (id: number): Promise<Board> => api.get<Board>(`${BASE}/boards/${id}`),

  create: (name: string): Promise<Board> =>
    api.post<Board>(`${BASE}/boards`, { name }),

  update: (id: number, patch: { name?: string; graph_json?: string }): Promise<Board> =>
    api.put<Board>(`${BASE}/boards/${id}`, patch),

  remove: (id: number): Promise<{ removed: boolean }> =>
    api.delete<{ removed: boolean }>(`${BASE}/boards/${id}`),
}
