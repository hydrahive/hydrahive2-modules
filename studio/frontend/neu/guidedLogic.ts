/** Geführter Weg (G1): rein, ohne DOM – damit testbar. Eine Karte = eine Szene (mit genau einem Shot im Normalfall). */
import type { IdeaLength } from "../draftApi"
import type { Plan, Scene } from "../planApi"

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
    2: false,
    3: all((s) => s.shots.some((x) => x.image_rel)),
    4: all((s) => s.shots.some((x) => x.video_rel)),
    5: false,
  }
}
