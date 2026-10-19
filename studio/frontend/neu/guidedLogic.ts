/** Geführter Weg (G1): rein, ohne DOM – damit testbar. Eine Karte = eine Szene (mit genau einem Shot im Normalfall). */
import type { IdeaLength } from "../draftApi"
import type { Job, Plan, PlanElement, Scene } from "../planApi"

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
