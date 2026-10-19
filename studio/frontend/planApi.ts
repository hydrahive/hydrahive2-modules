import { api } from "@/shared/api-client"

/** Planungsdaten des Studios (Backend: backend/plan.py, Spec „Bauplan Etappe 2“). */
export type ElementKind = "character" | "place" | "object"
export const ELEMENT_KINDS: ElementKind[] = ["character", "place", "object"]
export const CAMERA_KEYS = ["shot", "lens", "light", "weather", "time", "mood"] as const
export type CameraKey = (typeof CAMERA_KEYS)[number]
export const MODEL_KEYS = ["video", "image", "voice", "music", "text", "vision"] as const
export const ASPECTS = ["16:9", "9:16", "1:1", "4:3", "21:9"] as const
export const LANGUAGES = ["de", "en", "fr", "es", "it", "nl", "pl", "pt", "tr", "uk", "ru", "sv", "da", "no", "fi", "cs", "ja", "zh"] as const

export interface Head {
  title: string
  logline: string
  description: string
  aspect_ratio: string
  /** Sprache des Films (Untertitel, 6). */
  language?: string
  default_duration: number
  models: Record<(typeof MODEL_KEYS)[number], string>
  look: { style: string; palette: string[] }
  scene_order: string[]
}

export interface Dialogue { element_id: string; line: string; emotion: string }

export interface Shot {
  id: string
  order: number
  shot: string
  prompt: string
  element_ids: string[]
  duration: number
  status: string
  image_rel: string | null
  video_rel: string | null
  variants: string[]
  /** 5c: Sprechtext, Stimme (leer = Standard des Modells), erzeugte Sprache. Fehlt bei älteren Servern. */
  speech?: string
  voice?: string
  voice_rel?: string | null
  /** C2: wer im Bild ist – angehakt oder im Text genannt (vom Server berechnet, nur Anzeige) */
  cast?: string[]
  /** G3: „Mit dabei“ abgewählt – gilt auch, wenn der Name im Text steht */
  excluded_ids?: string[]
  /** G4: „Als Standbild lassen“ – kein Clip, das Bild steht im Film */
  still?: boolean
}

export type BatchKind = "decompose_all" | "images_all" | "videos_all" | "speech_all"
export const BATCH_KINDS: BatchKind[] = ["decompose_all", "images_all", "videos_all", "speech_all"]
export interface BatchPreview { count: number; model: string }

export interface Job {
  id: string
  kind: "image" | "video" | "speech" | "probe" | "film" | "free_images" | "render" | "music" | "transcribe" | "translate" | BatchKind
  target: string
  scene_id: string
  status: "queued" | "running" | "done" | "failed" | "cancelled"
  error: string | null
  result: Record<string, unknown> | null
  created_at: string
  finished_at: string | null
  progress?: { total: number; done: number; failed: number; current: string; current_shot?: string }
  /** Angaben für die Anzeige, z. B. Vorlage eines Films (7c) */
  info?: { aspect?: string; quality?: string; subtitles?: boolean }
}

export interface Scene {
  id: string
  title: string
  description: string
  location: string
  time_of_day: string
  element_ids: string[]
  dialogues: Dialogue[]
  camera: Partial<Record<CameraKey, string>>
  shots: Shot[]
}

export interface PlanElement {
  id: string
  kind: ElementKind
  name: string
  description: string
  style_anchor: string
  palette: string[]
  references: string[]
  /** G2: Probebild (so sieht der Baustein im Film aus), Freigabe „Passt“, „Kein Foto – die KI erfindet …“ */
  probe_rel?: string
  approved?: boolean
  no_photo?: boolean
}

export interface Plan {
  base: string
  screenplay: Head
  scenes: Scene[]
  elements: PlanElement[]
  presets: Partial<Record<CameraKey | "style", string[]>>
}

export interface ImportPreview {
  available: boolean
  scenes: number
  shots: number
  elements: number
  look: boolean
  plan_exists: boolean
}

export type Selection =
  | { kind: "head" }
  | { kind: "scene"; id: string }
  | { kind: "element"; id: string }
  | { kind: "shot"; sceneId: string; id: string }

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/plan`
const one = (id: string) => encodeURIComponent(id)

export const planApi = {
  get: (pid: string) => api.get<Plan>(base(pid)),
  saveHead: (pid: string, head: Partial<Head>) => api.put<Head>(`${base(pid)}/screenplay`, head),
  order: (pid: string, scene_order: string[]) => api.put<Head>(`${base(pid)}/order`, { scene_order }),
  addScene: (pid: string, data: Partial<Scene>) => api.post<Scene>(`${base(pid)}/scenes`, data),
  saveScene: (pid: string, id: string, data: Partial<Scene>) => api.put<Scene>(`${base(pid)}/scenes/${one(id)}`, data),
  deleteScene: (pid: string, id: string) => api.delete<{ deleted: string }>(`${base(pid)}/scenes/${one(id)}`),
  addElement: (pid: string, data: Partial<PlanElement>) => api.post<PlanElement>(`${base(pid)}/elements`, data),
  saveElement: (pid: string, id: string, data: Partial<PlanElement>) => api.put<PlanElement>(`${base(pid)}/elements/${one(id)}`, data),
  /** G2: Probebild des Bausteins erzeugen */
  probe: (pid: string, id: string) => api.post<Job>(`${base(pid)}/elements/${one(id)}/probe`, {}),
  deleteElement: (pid: string, id: string) => api.delete<{ deleted: string }>(`${base(pid)}/elements/${one(id)}`),
  addShot: (pid: string, sid: string, data: Partial<Shot>) => api.post<Shot>(`${base(pid)}/scenes/${one(sid)}/shots`, data),
  saveShot: (pid: string, sid: string, id: string, data: Partial<Shot>) => api.put<Shot>(`${base(pid)}/scenes/${one(sid)}/shots/${one(id)}`, data),
  deleteShot: (pid: string, sid: string, id: string) => api.delete<{ deleted: string }>(`${base(pid)}/scenes/${one(sid)}/shots/${one(id)}`),
  orderShots: (pid: string, sid: string, shot_ids: string[]) => api.put<{ shots: Shot[] }>(`${base(pid)}/scenes/${one(sid)}/shots/order`, { shot_ids }),
  decompose: (pid: string, sid: string, replace: boolean) =>
    api.post<{ shots: Shot[]; count: number }>(`${base(pid)}/scenes/${one(sid)}/decompose`, replace ? { replace: true } : {}),
  generateImage: (pid: string, sid: string, id: string) => api.post<Job>(`${base(pid)}/scenes/${one(sid)}/shots/${one(id)}/image`, {}),
  generateVideo: (pid: string, sid: string, id: string) => api.post<Job>(`${base(pid)}/scenes/${one(sid)}/shots/${one(id)}/video`, {}),
  generateSpeech: (pid: string, sid: string, id: string) => api.post<Job>(`${base(pid)}/scenes/${one(sid)}/shots/${one(id)}/speech`, {}),
  voices: (pid: string) => api.get<{ model: string; voices: string[] }>(`/modules/studio/projects/${encodeURIComponent(pid)}/voices`),
  chooseVariant: (pid: string, sid: string, id: string, image_rel: string) =>
    api.put<Shot>(`${base(pid)}/scenes/${one(sid)}/shots/${one(id)}/variant`, { image_rel }),
  jobs: (pid: string) => api.get<{ jobs: Job[] }>(`${base(pid)}/jobs`),
  batchPreview: (pid: string, kind: BatchKind) => api.get<BatchPreview>(`${base(pid)}/batch/${kind}`),
  batchStart: (pid: string, kind: BatchKind) => api.post<Job>(`${base(pid)}/batch/${kind}`, {}),
  cancelJob: (pid: string, id: string) => api.post<Job>(`${base(pid)}/jobs/${one(id)}/cancel`, {}),
  importPreview: (pid: string) => api.get<ImportPreview>(`${base(pid)}/import/atelier`),
  importRun: (pid: string) => api.post<{ scenes: number; shots: number; elements: number }>(`${base(pid)}/import/atelier`, {}),
}
