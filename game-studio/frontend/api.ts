import { api } from "@/shared/api-client"
import type { ChatInfo, ChatStart, DesignDoc, DesignDocMeta, GameProject, GameStudioOverview, ProjectCreate, ProjectPatch } from "./types"

const BASE = "/modules/game-studio"
const project = (projectId: string) => `${BASE}/projects/${encodeURIComponent(projectId)}`

export const gameStudioApi = {
  overview: (): Promise<GameStudioOverview> => api.get<GameStudioOverview>(`${BASE}/overview`),
  project: (projectId: string): Promise<GameProject> => api.get<GameProject>(project(projectId)),
  createProject: (body: ProjectCreate): Promise<GameProject> => api.post<GameProject>(`${BASE}/projects`, body),
  updateProject: (projectId: string, body: ProjectPatch): Promise<GameProject> =>
    api.patch<GameProject>(project(projectId), body),
  generateUnrealProject: (projectId: string, revision: number): Promise<GameProject> =>
    api.post<GameProject>(`${project(projectId)}/unreal-project`, { revision }),
  designDocs: (projectId: string): Promise<{ docs: DesignDocMeta[]; can_write: boolean }> =>
    api.get(`${project(projectId)}/design`),
  designDoc: (projectId: string, slug: string): Promise<DesignDoc> =>
    api.get(`${project(projectId)}/design/${encodeURIComponent(slug)}`),
  saveDesignDoc: (projectId: string, slug: string, content: string, etag: string | null): Promise<DesignDoc> =>
    api.put(`${project(projectId)}/design/${encodeURIComponent(slug)}`, { content, etag }),
  createDesignDoc: (projectId: string, title: string): Promise<DesignDoc> =>
    api.post(`${project(projectId)}/design`, { title }),
  chatInfo: (projectId: string): Promise<ChatInfo> => api.get(`${project(projectId)}/chat`),
  startChat: (projectId: string): Promise<ChatStart> => api.post(`${project(projectId)}/chat`, {}),
}
