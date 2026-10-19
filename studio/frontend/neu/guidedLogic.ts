/** Geführter Weg (G1): rein, ohne DOM – damit testbar. Eine Karte = eine Szene (mit genau einem Shot im Normalfall). */
import type { IdeaLength } from "../draftApi"
import type { Job, Plan, PlanElement, Scene, Shot } from "../planApi"

export type FilmKind = "trailer" | "explainer" | "short" | "music"
export const FILM_KINDS: FilmKind[] = ["trailer", "explainer", "short", "music"]
export const LENGTH_SECONDS: IdeaLength[] = ["30", "60", "120"]
export type StepId = 1 | 2 | 3 | 4 | 5
export const STEP_IDS: StepId[] = [1, 2, 3, 4, 5]

export interface Card { id: string; text: string }

export function cardsOf(plan: Plan | null): Card[] {
  return (plan?.scenes ?? []).map((s) => ({ id: s.id, text: s.description || s.title }))
}

/** Erste Wörter als Szenentitel: bis zum ersten Satzende, ohne Satzzeichen am Ende, höchstens 60 Zeichen. */
export function titleFrom(text: string): string {
  const first = text.trim().split(/(?<=[.!?])\s/)[0] ?? ""
  return first.replace(/[.!?:;,\s]+$/u, "").slice(0, 60)
}

/** Text einer Karte geändert: Szene bekommt Beschreibung + Titel; hat sie genau einen Shot, dessen Bildbeschreibung mit. */
export function sceneTextPatch(scene: Scene, text: string): { scene: { description: string; title: string }; shot: { id: string; prompt: string } | null } {
  const only = scene.shots.length === 1 ? scene.shots[0] : null
  return { scene: { description: text, title: titleFrom(text) }, shot: only ? { id: only.id, prompt: text } : null }
}

export function sceneFromText(text: string) {
  return { scene: { title: titleFrom(text), description: text }, shot: { prompt: text } }
}

export function ideaBody(idea: string, kind: FilmKind, length: number) {
  return { idea: idea.trim(), length: LENGTH_SECONDS[length] ?? "60", style: "", kind, shots_per_scene: 1 as const }
}

/** Haken links: was ist schon erledigt (Schritt 2 und 5 bekommen ihre Regeln mit G2 und G5). */
export function doneSteps(plan: Plan | null): Record<StepId, boolean> {
  const scenes = plan?.scenes ?? []
  const all = (fn: (s: Scene) => boolean) => scenes.length > 0 && scenes.every(fn)
  return {
    1: scenes.length > 0,
    2: scenes.length > 0 && castOpen(plan?.elements ?? []) === 0,
    3: all((s) => s.shots.some((x) => x.image_rel)),
    4: all((s) => s.shots.some((x) => x.video_rel)),
    5: false,
  }
}

export type CastState = "empty" | "photo" | "busy" | "failed" | "probe" | "approved" | "no_photo"

/** Zustand einer Figur/eines Orts im Schritt 2 – aus dem Baustein und seinem jüngsten Probebild-Auftrag. */
export function castState(el: PlanElement, jobs: Job[]): CastState {
  const job = jobs.filter((j) => j.kind === "probe" && j.target === el.id).sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
  if (job && (job.status === "running" || job.status === "queued")) return "busy"
  if (el.approved && el.probe_rel) return "approved"
  if (el.probe_rel) return "probe"
  if (job?.status === "failed") return "failed"
  if (el.no_photo) return "no_photo"
  return el.references.length ? "photo" : "empty"
}

/** Wie viele sind noch nicht fertig (weder „Passt“ noch „Kein Foto“)? */
export function castOpen(elements: PlanElement[]): number {
  return elements.filter((e) => !(e.approved && e.probe_rel) && !e.no_photo).length
}

// ---- G3 Bilder ------------------------------------------------------------------------------------------------
export interface ImageCardData { n: number; part: number; text: string; sceneId: string; shot: Shot }

/** Eine Karte je Shot. Szene mit genau einem Shot → Szenentext; mehrere → „Teil N“ mit der Bildbeschreibung. */
export function imageCards(plan: Plan | null): ImageCardData[] {
  return (plan?.scenes ?? []).flatMap((sc, i) => sc.shots.map((s, j) => ({
    n: i + 1, part: sc.shots.length > 1 ? j + 1 : 0, sceneId: sc.id, shot: s,
    text: sc.shots.length > 1 ? s.prompt : sc.description || sc.title,
  })))
}

export function missingImages(plan: Plan | null): number {
  return imageCards(plan).filter((c) => !c.shot.image_rel).length
}

const running = (j: Job) => j.status === "running" || j.status === "queued"

/** Entsteht gerade ein Bild für diesen Shot (eigener Auftrag oder Sammelauftrag, der gerade hier ist)? */
export function shotBusy(jobs: Job[], shotId: string, kind: "image" | "video" = "image"): boolean {
  const batch = kind === "image" ? "images_all" : "videos_all"
  return jobs.some((j) => running(j) && ((j.kind === kind && j.target === shotId) || (j.kind === batch && j.progress?.current_shot === shotId)))
}

/** Nächstes/voriges Bild der Varianten (zyklisch); null, wenn es nichts zu blättern gibt. */
export function variantStep(s: Shot, dir: -1 | 1): string | null {
  const v = s.variants
  if (v.length < 2) return null
  const i = v.indexOf(s.image_rel ?? "")
  return v[i < 0 ? 0 : (i + dir + v.length) % v.length]
}

/** „Mit dabei“ antippen: weg → ausschließen; dazu → anhaken und nicht mehr ausschließen. */
export function castToggle(s: Shot, id: string): { element_ids: string[]; excluded_ids: string[] } {
  const ids = s.element_ids.filter((x) => x !== id)
  const ex = (s.excluded_ids ?? []).filter((x) => x !== id)
  return (s.cast ?? []).includes(id) ? { element_ids: ids, excluded_ids: [...ex, id] } : { element_ids: [...ids, id], excluded_ids: ex }
}

/** Gesicht einer Figur: freigegebenes Probebild, sonst erstes Foto, sonst nichts. */
export function faceOf(e: PlanElement): string {
  return (e.approved && e.probe_rel) || e.references[0] || ""
}
