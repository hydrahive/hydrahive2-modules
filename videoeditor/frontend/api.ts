import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { BrowseEntry, EDL, ExportResult, Job, RenderPreset, UploadResult, VideoMeta } from "./types"

const BASE = "/modules/videoeditor"

export const videoeditorApi = {
  listFiles: (pid: string): Promise<VideoMeta[]> =>
    api.get<VideoMeta[]>(`${BASE}/projects/${pid}/files`),

  /** Alle Videos im GANZEN Projekt-Workspace (kein Silo) — inkl. Import-Status. */
  browse: (pid: string): Promise<BrowseEntry[]> =>
    api.get<BrowseEntry[]>(`${BASE}/projects/${pid}/browse`),

  /** Bereitet ein bestehendes Projekt-Video für den Editor auf (Proxy/Keyframes). */
  importVideo: (pid: string, sourceRel: string): Promise<UploadResult> =>
    api.post<UploadResult>(`${BASE}/projects/${pid}/import`, { source_rel: sourceRel }),

  getMeta: (pid: string, fileId: string): Promise<VideoMeta> =>
    api.get<VideoMeta>(`${BASE}/projects/${pid}/files/${fileId}`),

  getJob: (pid: string, jobId: string): Promise<Job> =>
    api.get<Job>(`${BASE}/projects/${pid}/jobs/${jobId}`),

  saveEdl: (pid: string, fileId: string, edl: EDL): Promise<{ ok: boolean }> =>
    api.put<{ ok: boolean }>(`${BASE}/projects/${pid}/files/${fileId}/edl`, edl),

  presets: (): Promise<RenderPreset[]> =>
    api.get<RenderPreset[]>(`${BASE}/presets`),

  startExport: (pid: string, fileId: string, filename: string, presetId: string): Promise<ExportResult> =>
    api.post<ExportResult>(`${BASE}/projects/${pid}/files/${fileId}/export`, { filename, preset_id: presetId }),

  exportPath: (pid: string, exportId: string): Promise<{ export_abs: string }> =>
    api.get<{ export_abs: string }>(`${BASE}/projects/${pid}/exports/${exportId}`),

  upload: async (pid: string, file: File): Promise<UploadResult> => {
    const token = useAuthStore.getState().token || ""
    const fd = new FormData()
    fd.append("file", file)
    const r = await fetch(`/api${BASE}/projects/${pid}/upload`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: fd,
    })
    if (!r.ok) {
      const text = await r.text()
      try { throw JSON.parse(text) } catch { throw new Error(text || `HTTP ${r.status}`) }
    }
    return r.json()
  },
}

/** Absoluter Dateipfad → /api/files-URL mit Token (Browser <video>/<img>
 *  können keinen Bearer-Header senden, deshalb Token als Query). */
export function fileUrl(absPath: string): string {
  const token = useAuthStore.getState().token
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : ""
  return `/api/files?path=${encodeURIComponent(absPath)}${tokenParam}`
}
