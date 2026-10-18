import { api } from "@/shared/api-client"
import { placeFree, type AudioTrack } from "./cutAudio"
import type { Tracks } from "./cutTracks"
import type { Job } from "./planApi"
import type { TimelineClip } from "./timelineApi"

/** Musik erzeugen (Spec „Nachtrag 5c-2“): Der Server erzeugt nur die Datei; auf die Zeitleiste legt sie der Browser. */
export interface MusicResult { rel: string; duration: number; seconds: number; scene_id: string }
export interface MusicDefaults {
  model: string
  film: { description: string; seconds: number }
  scenes: { id: string; title: string; description: string; seconds: number }[]
}
export interface MusicRequest { description: string; seconds: number; scene_id?: string }

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/music`
export const musicApi = {
  defaults: (pid: string) => api.get<MusicDefaults>(`${base(pid)}/defaults`),
  start: (pid: string, body: MusicRequest) => api.post<Job>(base(pid), body),
}

export const MUSIC_MIN = 5
export const MUSIC_MAX = 180
export const MUSIC_TRACK: AudioTrack = "A2"
const FADE = 2

/** Clip aus dem Ergebnis: höchstens die gewünschte Länge; wurde gekürzt, blendet die Musik die letzten 2 s aus. */
export function musicClip(r: MusicResult, newId: () => string): TimelineClip | null {
  if (!r?.rel || !(r.duration > 0)) return null
  const cut = r.seconds > 0 && r.duration > r.seconds
  const out = cut ? r.seconds : r.duration
  return { id: newId(), kind: "audio", start: 0, in: 0, out, media_rel: r.rel, scene_id: "", shot_id: "",
    label: r.rel.split("/").pop() ?? "", ...(cut ? { fade_out: Math.min(FADE, out / 2) } : {}) }
}

/** Auf A2 ablegen: ganzer Film ab 0, Szene ab ihrem ersten Bildclip, sonst ab dem Abspielkopf; belegt → nächste freie Stelle. */
export function placeMusic(tr: Tracks, clip: TimelineClip, sceneId: string, time: number, fps: number): Tracks {
  const first = sceneId ? tr.V1.filter((c) => c.scene_id === sceneId).sort((a, b) => a.start - b.start)[0] : null
  const want = !sceneId ? 0 : first ? first.start : time
  const start = placeFree(tr[MUSIC_TRACK], want, clip.out - clip.in, fps)
  return { ...tr, [MUSIC_TRACK]: [...tr[MUSIC_TRACK], { ...clip, start }] }
}

/** Ein in diesem Fenster gestarteter Musikauftrag, der fertig (oder fehlgeschlagen) ist – sonst null. */
export function finishedMusic(jobs: Job[], pending: Set<string>): Job | null {
  return jobs.find((j) => j.kind === "music" && pending.has(j.id) && (j.status === "done" || j.status === "failed" || j.status === "cancelled")) ?? null
}
