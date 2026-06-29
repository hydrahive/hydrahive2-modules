import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type {
  AtelierCharacter,
  AtelierCI,
  CharacterInput,
  GalleryItem,
  GenerateRequest,
  GenerateResult,
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

  gallery: (pid: string): Promise<GalleryItem[]> =>
    api.get<GalleryItem[]>(`${BASE}/projects/${pid}/gallery`),
  generate: (pid: string, req: GenerateRequest): Promise<GenerateResult> =>
    api.post<GenerateResult>(`${BASE}/projects/${pid}/generate`, req),
  promote: (pid: string, charId: string, rel: string): Promise<AtelierCharacter> =>
    api.post<AtelierCharacter>(`${BASE}/projects/${pid}/promote`, { char_id: charId, rel }),
}

/** Absoluter Dateipfad → /api/files-URL mit Token (Browser-img kann keinen Bearer). */
export function fileUrl(absPath: string): string {
  const token = useAuthStore.getState().token
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api/files?path=${encodeURIComponent(absPath)}${tokenParam}`
}
