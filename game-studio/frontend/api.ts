import { api } from "@/shared/api-client"
import type { GameProject, GameStudioOverview, ProjectCreate, ProjectPatch } from "./types"

const BASE = "/modules/game-studio"

export const gameStudioApi = {
  overview: (): Promise<GameStudioOverview> => api.get<GameStudioOverview>(`${BASE}/overview`),
  project: (projectId: string): Promise<GameProject> => api.get<GameProject>(`${BASE}/projects/${projectId}`),
  createProject: (body: ProjectCreate): Promise<GameProject> => api.post<GameProject>(`${BASE}/projects`, body),
  updateProject: (projectId: string, body: ProjectPatch): Promise<GameProject> =>
    api.patch<GameProject>(`${BASE}/projects/${projectId}`, body),
  generateUnrealProject: (projectId: string, revision: number): Promise<GameProject> =>
    api.post<GameProject>(`${BASE}/projects/${projectId}/unreal-project`, { revision }),
}
