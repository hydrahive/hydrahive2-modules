import { api } from "@/shared/api-client"

/** Untertitel (Spec „Bauplan Etappe 6“): eigene Daten je Sprache, nie ins Bild eingebrannt. Rein, damit testbar. */
export interface Cue { id: string; start: number; end: number; text: string }
export interface Subtitles { language: string; source: string; revision: number; cues: Cue[] }
export interface SubtitleFile { filename: string; mime: string; content: string }
export type SubtitleFormat = "srt" | "vtt"

export const MIN_CUE = 0.5
const NEW_CUE = 2

const base = (pid: string, lang: string) => `/modules/studio/projects/${encodeURIComponent(pid)}/subtitles/${encodeURIComponent(lang)}`
export const subtitleApi = {
  get: (pid: string, lang: string) => api.get<Subtitles>(base(pid, lang)),
  save: (pid: string, lang: string, s: { revision: number; cues: Cue[] }) => api.put<Subtitles>(base(pid, lang), s),
  fromSpeech: (pid: string, lang: string, replace: boolean) =>
    api.post<Subtitles & { skipped: number }>(`${base(pid, lang)}/from-speech`, replace ? { replace: true } : {}),
  file: (pid: string, lang: string, format: SubtitleFormat) => api.get<SubtitleFile>(`${base(pid, lang)}/export?format=${format}`),
}

const r3 = (x: number) => Math.round(x * 1000) / 1000

/** Eintrag, der bei Zeit t zu sehen ist (Ende gehört nicht mehr dazu). */
export function cueAt(cues: Cue[], t: number): Cue | null {
  return cues.find((c) => t >= c.start && t < c.end) ?? null
}

/** Text oder Zeiten eines Eintrags ändern. Zeiten bleiben zwischen den Nachbarn und mindestens MIN_CUE lang. */
export function editCue(cues: Cue[], id: string, v: Partial<Pick<Cue, "start" | "end" | "text">>): Cue[] {
  const i = cues.findIndex((c) => c.id === id)
  if (i < 0) return cues
  const c = cues[i]
  const lo = i > 0 ? cues[i - 1].end : 0
  const hi = i < cues.length - 1 ? cues[i + 1].start : Infinity
  let { start, end } = c
  if (v.start !== undefined) start = r3(Math.min(Math.max(v.start, lo), end - MIN_CUE))
  if (v.end !== undefined) end = r3(Math.max(Math.min(v.end, hi), start + MIN_CUE))
  const next = { ...c, start, end, ...(v.text !== undefined ? { text: v.text } : {}) }
  return cues.map((x, k) => (k === i ? next : x))
}

/** Text an der Wortgrenze nahe der Mitte teilen (ein Wort: in beiden Teilen). */
function halves(text: string): [string, string] {
  const words = text.split(/\s+/).filter(Boolean)
  if (words.length < 2) return [text, text]
  const half = text.length / 2
  let best = 1
  for (let k = 1; k < words.length; k++) {
    if (Math.abs(words.slice(0, k).join(" ").length - half) < Math.abs(words.slice(0, best).join(" ").length - half)) best = k
  }
  return [words.slice(0, best).join(" "), words.slice(best).join(" ")]
}

/** Am Abspielkopf teilen; beide Teile mindestens MIN_CUE. */
export function splitCue(cues: Cue[], id: string, t: number, newId: () => string): Cue[] {
  const i = cues.findIndex((c) => c.id === id)
  const c = cues[i]
  if (!c || t - c.start < MIN_CUE || c.end - t < MIN_CUE) return cues
  const [a, b] = halves(c.text)
  return [...cues.slice(0, i), { ...c, end: r3(t), text: a }, { id: newId(), start: r3(t), end: c.end, text: b }, ...cues.slice(i + 1)]
}

/** Mit dem nächsten Eintrag zusammenführen. */
export function joinCues(cues: Cue[], id: string): Cue[] {
  const i = cues.findIndex((c) => c.id === id)
  if (i < 0 || i >= cues.length - 1) return cues
  const a = cues[i], b = cues[i + 1]
  return [...cues.slice(0, i), { ...a, end: b.end, text: `${a.text} ${b.text}`.replace(/\s+/g, " ").trim() }, ...cues.slice(i + 2)]
}

export function removeCue(cues: Cue[], id: string): Cue[] {
  return cues.filter((c) => c.id !== id)
}

/** Neuer Eintrag am Abspielkopf, nur in einer Lücke von mindestens MIN_CUE: 2 s oder bis zum nächsten Eintrag. */
export function addCue(cues: Cue[], t: number, text: string, newId: () => string): { cues: Cue[]; cue: Cue | null } {
  const start = r3(Math.max(0, t))
  if (cueAt(cues, start)) return { cues, cue: null }
  const next = cues.find((c) => c.start > start)
  const end = r3(Math.min(start + NEW_CUE, next ? next.start : Infinity))
  if (end - start < MIN_CUE) return { cues, cue: null }
  const cue = { id: newId(), start, end, text }
  return { cues: [...cues, cue].sort((x, y) => x.start - y.start), cue }
}

/** Zeit für die Liste: m:ss.z bzw. h:mm:ss.z */
export function timeText(t: number): string {
  const tenths = Math.floor(Math.max(0, t) * 10 + 1e-6)
  const h = Math.floor(tenths / 36000), m = Math.floor((tenths % 36000) / 600), s = Math.floor((tenths % 600) / 10), z = tenths % 10
  const ss = `${String(s).padStart(2, "0")}.${z}`
  return h ? `${h}:${String(m).padStart(2, "0")}:${ss}` : `${m}:${ss}`
}

export function saveName(f: Pick<SubtitleFile, "filename">): string {
  return f.filename || "untertitel.srt"
}

/** Datei im Browser speichern (kein Token in einer Adresse). */
export function download(f: SubtitleFile): void {
  const url = URL.createObjectURL(new Blob([f.content], { type: f.mime }))
  const a = document.createElement("a")
  a.href = url
  a.download = saveName(f)
  document.body.appendChild(a)
  a.click()
  a.remove()
  window.setTimeout(() => URL.revokeObjectURL(url), 1000)
}
