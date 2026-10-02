import type { MediaKind, ProjectSource, Track, TrackMeta } from "./types"

export const MEDIA_ACCEPT: Record<MediaKind, string> = {
  audio: ".mp3,.wav,.ogg,.m4a,.flac",
  video: ".mp4,.webm",
}
const STORAGE_PREFIX = "hh2.musicplayer.kind."

export function filterByKind<T extends { media_kind?: MediaKind; kind?: MediaKind }>(items: T[], kind: MediaKind): T[] {
  return items.filter((item) => (item.media_kind ?? item.kind) === kind)
}
export function groupedSources(sources: ProjectSource[]): Array<[string, ProjectSource[]]> {
  const groups = new Map<string, ProjectSource[]>()
  for (const source of sources) groups.set(source.group, [...(groups.get(source.group) ?? []), source])
  return [...groups]
}
export function trackSubtitle(meta: TrackMeta, maxPrompt = 100): { text: string; promptTitle?: string } {
  const prompt = meta.prompt?.trim()
  const shortPrompt = prompt && prompt.length > maxPrompt ? `${prompt.slice(0, maxPrompt - 1)}…` : prompt
  const details = [meta.model, meta.duration ? String(meta.duration) : undefined].filter(Boolean)
  return { text: [shortPrompt, details.join(" · ")].filter(Boolean).join(" · "), promptTitle: prompt }
}
export function rememberedKind(projectId: string): MediaKind {
  try { return localStorage.getItem(`${STORAGE_PREFIX}${projectId}`) === "video" ? "video" : "audio" } catch { return "audio" }
}
export function rememberKind(projectId: string, kind: MediaKind): void {
  try { localStorage.setItem(`${STORAGE_PREFIX}${projectId}`, kind) } catch { /* optional */ }
}
export function isTrackKind(track: Track, kind: MediaKind): boolean { return track.media_kind === kind }
