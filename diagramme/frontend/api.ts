import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { BASE, listQuery, type Filter } from "./logic"

export interface Item {
  id: string
  title: string
  kind: string
  project_id: string | null
  project_name: string
  created_at: string
  versions: number
  username: string
  deleted_at: string | null
  preview_state: string | null
  version_of: string | null
}

export interface Version { id: string; created_at: string; deleted_at: string | null }
export interface Access { total: number; with_tool: number; unlocked_by_us: number; changed?: number }

export const listItems = (f: Filter) => api.get<Item[]>(listQuery(f))
export const getVersions = async (id: string) => (await api.get<{ versions: Version[] }>(`${BASE}/item/${id}`)).versions
export const toTrash = (id: string) => api.post<void>(`${BASE}/trash/${id}`, {})
export const restore = (id: string) => api.post<void>(`${BASE}/restore/${id}`, {})
export const purge = (id: string) => api.delete<void>(`${BASE}/item/${id}`)
export const getAccess = () => api.get<Access>(`${BASE}/agents-access`)
export const setAccess = (on: boolean) => api.post<Access>(`${BASE}/agents-access`, { on })

/** Mit Anmelde-Kopf laden (Token nie in einer Adresse) und als Blob-Adresse zurückgeben. */
async function authBlob(path: string): Promise<Blob | null> {
  const token = useAuthStore.getState().token
  const res = await fetch(`/api${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
  if (res.status === 401) useAuthStore.getState().logout()
  return res.ok ? res.blob() : null
}

export async function previewUrl(id: string): Promise<string | null> {
  const blob = await authBlob(`${BASE}/preview/${id}`)
  return blob ? URL.createObjectURL(blob) : null
}

export async function download(id: string, title: string): Promise<void> {
  const blob = await authBlob(`${BASE}/download/${id}`)
  if (!blob) throw new Error("download_failed")
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `${title.replace(/[\\/:*?"<>|]+/g, "-").trim() || "diagramm"}.html`
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}
