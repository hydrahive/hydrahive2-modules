import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type {
  AtelierCharacter,
  AtelierCI,
  AudioLibraryItem,
  AudioProfile,
  AudioProfileInput,
  CharacterInput,
  GalleryItem,
  GenerateRequest,
  GenerateResult,
  MusicGenerateRequest,
  MusicGenerateResult,
  PresetCatalog,
  VideoJob,
  VideoRequest,
  FilmJob,
  Screenplay,
  Scene,
  SceneInput,
  MediaModelList,
  Shot,
  DecomposeResult,
  RenderJob,
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
  deleteImage: (pid: string, rel: string): Promise<{ ok: boolean }> =>
    api.post<{ ok: boolean }>(`${BASE}/projects/${pid}/gallery/delete`, { rel }),
  generate: (pid: string, req: GenerateRequest): Promise<GenerateResult> =>
    api.post<GenerateResult>(`${BASE}/projects/${pid}/generate`, req),
  promote: (pid: string, charId: string, rel: string): Promise<AtelierCharacter> =>
    api.post<AtelierCharacter>(`${BASE}/projects/${pid}/promote`, { char_id: charId, rel }),
  listVideos: (pid: string): Promise<VideoJob[]> =>
    api.get<VideoJob[]>(`${BASE}/projects/${pid}/videos`),
  createVideo: (pid: string, req: VideoRequest): Promise<VideoJob> =>
    api.post<VideoJob>(`${BASE}/projects/${pid}/videos`, req),
  deleteVideo: (pid: string, jobId: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/projects/${pid}/videos/${jobId}`),
  continueFrame: (pid: string, videoRel: string): Promise<{ rel: string; path: string }> =>
    api.post<{ rel: string; path: string }>(`${BASE}/projects/${pid}/videos/continue`, { video_rel: videoRel }),
  listFilms: (pid: string): Promise<FilmJob[]> =>
    api.get<FilmJob[]>(`${BASE}/projects/${pid}/films`),
  createFilm: (pid: string, clips: string[], resolution: string, musicRel?: string): Promise<FilmJob> =>
    api.post<FilmJob>(`${BASE}/projects/${pid}/films`, { clips, resolution, music_rel: musicRel || "" }),
  deleteFilm: (pid: string, jobId: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/projects/${pid}/films/${jobId}`),

  // ---- Audio (Musik) ----
  getMusicAnchor: (pid: string): Promise<{ music_style_anchor: string }> =>
    api.get<{ music_style_anchor: string }>(`${BASE}/projects/${pid}/audio/anchor`),
  saveMusicAnchor: (pid: string, anchor: string): Promise<{ music_style_anchor: string }> =>
    api.put<{ music_style_anchor: string }>(`${BASE}/projects/${pid}/audio/anchor`, { music_style_anchor: anchor }),
  listAudioProfiles: (pid: string): Promise<AudioProfile[]> =>
    api.get<AudioProfile[]>(`${BASE}/projects/${pid}/audio/profiles`),
  createAudioProfile: (pid: string, body: AudioProfileInput): Promise<AudioProfile> =>
    api.post<AudioProfile>(`${BASE}/projects/${pid}/audio/profiles`, body),
  updateAudioProfile: (pid: string, id: string, body: AudioProfileInput): Promise<AudioProfile> =>
    api.put<AudioProfile>(`${BASE}/projects/${pid}/audio/profiles/${id}`, body),
  deleteAudioProfile: (pid: string, id: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/projects/${pid}/audio/profiles/${id}`),
  audioLibrary: (pid: string): Promise<AudioLibraryItem[]> =>
    api.get<AudioLibraryItem[]>(`${BASE}/projects/${pid}/audio/library`),
  deleteAudioTrack: (pid: string, rel: string): Promise<{ ok: boolean }> =>
    api.post<{ ok: boolean }>(`${BASE}/projects/${pid}/audio/library/delete`, { rel }),
  generateMusic: (pid: string, req: MusicGenerateRequest): Promise<MusicGenerateResult> =>
    api.post<MusicGenerateResult>(`${BASE}/projects/${pid}/audio/generate`, req),
  uploadReference: (pid: string, charId: string, file: File): Promise<AtelierCharacter> => {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<AtelierCharacter>(`${BASE}/projects/${pid}/characters/${charId}/upload`, form)
  },

  // ---- Regie (Screenplay) ----
  getScreenplay: (pid: string): Promise<Screenplay> =>
    api.get<Screenplay>(`${BASE}/projects/${pid}/screenplay`),
  saveScreenplay: (pid: string, body: Partial<Screenplay>): Promise<Screenplay> =>
    api.put<Screenplay>(`${BASE}/projects/${pid}/screenplay`, body),
  listScenes: (pid: string): Promise<Scene[]> =>
    api.get<Scene[]>(`${BASE}/projects/${pid}/screenplay/scenes`),
  createScene: (pid: string, body: Partial<SceneInput>): Promise<Scene> =>
    api.post<Scene>(`${BASE}/projects/${pid}/screenplay/scenes`, body),
  updateScene: (pid: string, id: string, body: Partial<SceneInput>): Promise<Scene> =>
    api.put<Scene>(`${BASE}/projects/${pid}/screenplay/scenes/${id}`, body),
  deleteScene: (pid: string, id: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/projects/${pid}/screenplay/scenes/${id}`),
  reorderScenes: (pid: string, sceneIds: string[]): Promise<Screenplay> =>
    api.post<Screenplay>(`${BASE}/projects/${pid}/screenplay/scenes/reorder`, { scene_ids: sceneIds }),

  // ---- Media-Modelle (Live-Liste von OpenRouter, für Dropdowns) ----
  mediaModels: (category: "video" | "image" | "audio"): Promise<MediaModelList> =>
    api.get<MediaModelList>(`/llm/media-models?category=${category}`),

  // ---- Regieagent: Zerlegen (Phase 1) + Shots ----
  decompose: (pid: string, model?: string): Promise<DecomposeResult> =>
    api.post<DecomposeResult>(`${BASE}/projects/${pid}/screenplay/decompose`, { model: model || "" }),
  listShots: (pid: string, sceneId: string): Promise<Shot[]> =>
    api.get<Shot[]>(`${BASE}/projects/${pid}/screenplay/scenes/${sceneId}/shots`),
  updateShot: (pid: string, sceneId: string, shotId: string, body: Partial<Shot>): Promise<Shot> =>
    api.put<Shot>(`${BASE}/projects/${pid}/screenplay/scenes/${sceneId}/shots/${shotId}`, body),
  deleteShot: (pid: string, sceneId: string, shotId: string): Promise<{ ok: boolean }> =>
    api.delete<{ ok: boolean }>(`${BASE}/projects/${pid}/screenplay/scenes/${sceneId}/shots/${shotId}`),
  startRender: (pid: string, model?: string): Promise<{ status: string }> =>
    api.post<{ status: string }>(`${BASE}/projects/${pid}/screenplay/render`, { model: model || "" }),
  renderStatus: (pid: string): Promise<RenderJob> =>
    api.get<RenderJob>(`${BASE}/projects/${pid}/screenplay/render`),
}

/** Absoluter Dateipfad → /api/files-URL mit Token (Browser-img kann keinen Bearer). */
export function fileUrl(absPath: string): string {
  const token = useAuthStore.getState().token
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api/files?path=${encodeURIComponent(absPath)}${tokenParam}`
}
