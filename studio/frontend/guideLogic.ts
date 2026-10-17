/** Führung durch das Studio (Spec „Etappe B“, B1): wohin zuerst, was als Nächstes. Rein, damit testbar. */
import { WORKSPACES, type Workspace } from "./workspaces"

export interface Overview {
  scenes: number
  shots: number
  with_image: number
  with_video: number
  clips: number
  atelier: boolean
}

export type Step = "plan" | "shots" | "images" | "videos" | "cut"

/** Reiter beim Öffnen: gemerkter Reiter des Projekts, sonst nach Stand (ohne Shots Planen, ohne Schnitt Erzeugen). */
export function startWorkspace(o: Overview | null, remembered: string | null): Workspace {
  if (remembered && (WORKSPACES as readonly string[]).includes(remembered)) return remembered as Workspace
  if (!o || !o.shots) return "plan"
  return o.clips ? "edit" : "generate"
}

/** Nächster offener Schritt mit dem Reiter, in dem er erledigt wird; null = alles da. */
export function nextStep(o: Overview): { step: Step; workspace: Workspace } | null {
  if (!o.scenes) return { step: "plan", workspace: "plan" }
  if (!o.shots) return { step: "shots", workspace: "plan" }
  if (o.with_image < o.shots) return { step: "images", workspace: "generate" }
  if (o.with_video < o.shots) return { step: "videos", workspace: "generate" }
  if (!o.clips) return { step: "cut", workspace: "edit" }
  return null
}

const WS_KEY = "hh.studio.workspace.v1"
const INTRO_KEY = "hh.studio.intro.v1"

/** Zuletzt benutzter Reiter je Projekt (im Browser). */
export function rememberedWorkspace(pid: string, store: Pick<Storage, "getItem"> | undefined = globalThis.localStorage): string | null {
  try { return (JSON.parse(store?.getItem(WS_KEY) || "{}") as Record<string, string>)[pid] ?? null } catch { return null }
}

export function rememberWorkspace(pid: string, ws: Workspace, store: Storage | undefined = globalThis.localStorage): void {
  try {
    const all = JSON.parse(store?.getItem(WS_KEY) || "{}") as Record<string, string>
    store?.setItem(WS_KEY, JSON.stringify({ ...all, [pid]: ws }))
  } catch { /* nicht merken */ }
}

/** Kurzhilfe je Reiter ein- oder ausgeklappt (Standard: an). */
export function introOpen(ws: Workspace, store: Pick<Storage, "getItem"> | undefined = globalThis.localStorage): boolean {
  try { return (JSON.parse(store?.getItem(INTRO_KEY) || "{}") as Record<string, boolean>)[ws] !== false } catch { return true }
}

export function setIntroOpen(ws: Workspace, open: boolean, store: Storage | undefined = globalThis.localStorage): void {
  try {
    const all = JSON.parse(store?.getItem(INTRO_KEY) || "{}") as Record<string, boolean>
    store?.setItem(INTRO_KEY, JSON.stringify({ ...all, [ws]: open }))
  } catch { /* nicht merken */ }
}
