import { api } from "@/shared/api-client"
import { useAuthStore } from "@/features/auth/useAuthStore"
import type { Rule, Template } from "./rules"

const BASE = "/modules/vitrine"

export interface VitrineStatus {
  running: boolean
  connected: boolean
  frames: number
  fps: number | null
  video: string | null
  error: string | null
  size: [number, number] | null
  rule: string | null
  holiday: string | null
  night: "dim" | "off" | null
  /** Hinweistext während einer Vorschau auf dem Display, sonst null. */
  preview: string | null
  /** Was das Display zeigt: Feiertagsvideo oder Dashboard (Statuszentrale). */
  mode: "video" | "dashboard" | null
  /** „aus“ | „bereit“ | „nicht verfügbar: <Grund>“ | „startet“ – vom Dienst. */
  dashboard: string | null
}

export interface Night {
  enabled: boolean
  from: string
  to: string
  mode: "dim" | "off"
}

import type { DashboardCfg } from "./rules"

export interface VitrineConfig {
  rules: Rule[]
  default_videos: string[]
  night: Night
  rotate_minutes: number
  /** Bildrate 12–30 (Standard 24). */
  fps: number
  /** Standard-Dauer einer Einblendung in Sekunden, 5–120 (Fehler bleiben länger). */
  message_seconds: number
  /** Dashboard → zurück zum Video nach so vielen Sekunden ohne Eingabe, 30–1800 (Standard 120). */
  dashboard_return_seconds: number
  /** Statuszentrale S2: Tasks von, Projekt mit GitHub-Token (nur lesend), Repos owner/repo. */
  dashboard: DashboardCfg
}

export interface VideoFile {
  name: string
  size: number
  modified: number
}

export interface Simulation {
  video: string | null
  rule: string | null
  holiday: string | null
  night: string | null
}

export type MessageKind = "info" | "success" | "warning" | "error"

export interface VitrineMessage {
  id: string
  text: string
  title: string
  kind: MessageKind
  count: number
  created: number
  expires: number
  source: string
}

export const vitrineApi = {
  status: () => api.get<VitrineStatus>(`${BASE}/status`),
  config: () => api.get<VitrineConfig>(`${BASE}/config`),
  saveConfig: (c: VitrineConfig) => api.put<VitrineConfig>(`${BASE}/config`, c),
  templates: () => api.get<Template[]>(`${BASE}/templates`),
  videos: () => api.get<VideoFile[]>(`${BASE}/videos`),
  upload: (file: File) => {
    const form = new FormData()
    form.append("file", file)
    return api.postForm<{ name: string }>(`${BASE}/videos`, form)
  },
  remove: (name: string) => api.delete<void>(`${BASE}/videos/${encodeURIComponent(name)}`),
  messages: () => api.get<VitrineMessage[]>(`${BASE}/messages`),
  sendMessage: (m: { text: string; title?: string; kind: MessageKind; seconds?: number }) =>
    api.post<VitrineMessage>(`${BASE}/messages`, m),
  dismiss: (id: string) => api.delete<void>(`${BASE}/messages/${encodeURIComponent(id)}`),
  simulate: (at: string) => api.post<Simulation>(`${BASE}/simulate`, { at }),
  /** Display zeigt 30 s das Programm dieses Zeitpunkts. */
  startPreview: (at: string) => api.post<{ at: string; seconds: number }>(`${BASE}/preview`, { at }),
  stopPreview: () => api.delete<void>(`${BASE}/preview`),
  /** <img> kann keinen Header setzen → ?token= (wie Mediaplayer-Stream); &t= gegen den Browser-Cache. */
  previewUrl: (t: number) => {
    const token = useAuthStore.getState().token ?? ""
    return `/api${BASE}/preview.jpg?token=${encodeURIComponent(token)}&t=${t}`
  },
}
