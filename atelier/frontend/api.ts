import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type {
  AtelierCharacter,
  AtelierCI,
  CharacterInput,
  GalleryItem,
  GenerateRequest,
  GenerateResult,
  PresetCatalog,
  VideoJob,
  VideoRequest,
} from "./types"

const BASE = "/modules/atelier"

export const atelierApi = {
  meta: (pid: string): Promise<{ root: string }> =>
    api.get<{ root: string }>(`${BASE}/projects/${pid}/meta`),
  getCI: (pid: string): Promise<AtelierCI> =>
    api.get<AtelierCI>(`${BASE}/projects/${pid}/ci`),
  saveCI: (pid: string, ci: AtelierCI): Promise<AtelierCI> =>
    api.put<AtelierCI>(`${BASE}/projects/${pid}/ci`, ci),

  listCharacters: (pid: string): Promise<AtelierCharacter[]> =>
    api.get<AtelierCharacter[]>(`${BASE}/projects/${pid}/characters`),
  createCharacter: (pid: string, body: CharacterInput): Promise<AtelierCharacter> =>
    api.post<AtelierCharacter>(`${BASE}/projects/${pid}/characters`, body),
  updateCharacter: (pid: string, id: string, body: CharacterInput): Promise<AtelierCharacter> =>
    api.put<AtelierCharacter>(`${BASE}/projects/${pid}/characters/${id}`, body),
  deleteCharacter: (pid: string, id: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/projects/${pid}/characters/${id}`),

  presets: (): Promise<PresetCatalog> =>
    api.get<PresetCatalog>(`${BASE}/presets`),
  gallery: (pid: string): Promise<GalleryItem[]> =>
    api.get<GalleryItem[]>(`${BASE}/projects/${pid}/gallery`),
  generate: (pid: string, req: GenerateRequest): Promise<GenerateResult> =>
    api.post<GenerateResult>(`${BASE}/projects/${pid}/generate`, req),
  promote: (pid: string, charId: string, rel: string): Promise<AtelierCharacter> =>
    api.post<AtelierCharacter>(`${BASE}/projects/${pid}/promote`, { char_id: charId, rel }),
  listVideos: (pid: string): Promise<VideoJob[]> =>
    api.get<VideoJob[]>(`${BASE}/projects/${pid}/videos`),
  createVideo: (pid: string, req: VideoRequest): Promise<VideoJob> =>
    api.post<VideoJob>(`${BASE}/projects/${pid}/videos`, req),
  uploadReference: (pid: string, charId: string, file: File): Promise<AtelierCharacter> => {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<AtelierCharacter>(`${BASE}/projects/${pid}/characters/${charId}/upload`, form)
  },
}

/** Absoluter Dateipfad → /api/files-URL mit Token (Browser-img kann keinen Bearer). */
export function fileUrl(absPath: string): string {
  const token = useAuthStore.getState().token
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api/files?path=${encodeURIComponent(absPath)}${tokenParam}`
}
