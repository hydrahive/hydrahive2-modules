import { api } from "@/shared/api-client"
import type { PlanElement } from "./planApi"
import { paletteFromText } from "./planLogic"

/** Eigenes Material hochladen (Spec „Bauplan Etappe 7“, 7a). Rein, damit testbar. */
export interface UploadResult { ok: boolean; name: string; kind?: string; rel?: string; size?: number; duration?: number; error?: string }

const IMAGE = [".png", ".jpg", ".jpeg", ".webp", ".gif"]
const VIDEO = [".mp4", ".mov", ".webm", ".mkv", ".m4v"]
const AUDIO = [".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac", ".opus"]

export function acceptFor(target: "library" | "reference"): string {
  return (target === "reference" ? IMAGE : [...IMAGE, ...VIDEO, ...AUDIO]).join(",")
}

const base = (pid: string) => `/modules/studio/projects/${encodeURIComponent(pid)}`
const form = (files: File[]) => { const f = new FormData(); for (const x of files) f.append("files", x, x.name); return f }
export const uploadApi = {
  library: (pid: string, files: File[]) => api.postForm<{ files: UploadResult[] }>(`${base(pid)}/uploads`, form(files)),
  reference: (pid: string, elementId: string, file: File) =>
    api.postForm<PlanElement>(`${base(pid)}/plan/elements/${encodeURIComponent(elementId)}/references`, form([file])),
}

/** Wird eine Datei aus dem Dateimanager gezogen (nicht ein Medium aus der Bibliothek)? */
export function isFileDrag(dt: { types: readonly string[] | DOMStringList } | null): boolean {
  return !!dt && Array.from(dt.types as readonly string[]).includes("Files")
}

export function filesFromDrop(dt: { files: FileList } | null): File[] {
  return dt ? Array.from(dt.files) : []
}

export function uploadSummary(results: UploadResult[]): { key: "upload_done" | "upload_partly" | "upload_failed"; count: number;
  failed: { name: string; error: string }[] } {
  const good = results.filter((r) => r.ok).length
  const failed = results.filter((r) => !r.ok).map((r) => ({ name: r.name, error: r.error ?? "" }))
  return { key: !failed.length ? "upload_done" : good ? "upload_partly" : "upload_failed", count: good, failed }
}

/** Felder, die vor dem Hochladen gespeichert werden müssen (null = nichts geändert). */
export function pendingElement(saved: PlanElement, edited: PlanElement, palette: string): Partial<PlanElement> | null {
  const next = { kind: edited.kind, name: edited.name, description: edited.description, style_anchor: edited.style_anchor,
    palette: paletteFromText(palette), references: edited.references }
  const before = { kind: saved.kind, name: saved.name, description: saved.description, style_anchor: saved.style_anchor,
    palette: saved.palette, references: saved.references }
  return JSON.stringify(next) === JSON.stringify(before) ? null : next
}
