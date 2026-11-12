// Chat neben dem Board: Zustand (offen, Breite) im Browser merken, Breite begrenzen. Vorbild: Game Studio.
import type { ChatInfo, ChatStart } from "./types"

export const DOCK_KEY = "blueprint.agentDock"
export const DOCK_MIN = 320
export const DOCK_DEFAULT = 420
export interface DockState { open: boolean; width: number }

/** Breite zwischen Mindestmaß und 45 % des Fensters, damit die Zeichenfläche Platz behält. */
export function clampWidth(width: number, viewport: number): number {
  const max = Math.max(DOCK_MIN, Math.floor(viewport * 0.45))
  if (!Number.isFinite(width)) return Math.min(DOCK_DEFAULT, max)
  return Math.min(max, Math.max(DOCK_MIN, Math.round(width)))
}

export function readDock(raw: string | null, viewport: number): DockState {
  try {
    const value = JSON.parse(raw ?? "") as Partial<DockState>
    const width = typeof value.width === "number" ? value.width : DOCK_DEFAULT
    return { open: value.open === true, width: clampWidth(width, viewport) }
  } catch {
    return { open: false, width: clampWidth(DOCK_DEFAULT, viewport) }
  }
}

/** Gemerkten Zustand laden. Ohne Speicher im Browser (privates Fenster) gilt der Ausgangszustand. */
export function loadDock(): DockState {
  return readDock(storedDock(), window.innerWidth)
}

function storedDock(): string | null {
  try {
    return window.localStorage.getItem(DOCK_KEY)
  } catch {
    return null
  }
}

export function saveDock(state: DockState): void {
  try {
    window.localStorage.setItem(DOCK_KEY, JSON.stringify(state))
  } catch {
    // Ohne Speicher im Browser gilt der Zustand nur bis zum Neuladen.
  }
}

/** Werkzeugliste eines Agenten um die fehlenden ergänzen, ohne vorhandene zu verlieren oder zu verdoppeln. */
export function withTools(have: string[], missing: string[]): string[] {
  return [...have, ...missing.filter((name) => !have.includes(name))]
}

/** Die zwei Abfragen, die das Öffnen braucht (blueprintApi erfüllt das). */
export interface ChatSource {
  chatInfo: (id: number) => Promise<ChatInfo>
  startChat: (id: number) => Promise<ChatStart>
}
export interface ChatOpening { info: ChatInfo; started: ChatStart | null; showIntro: boolean }

/**
 * Chat zum Board öffnen: erst die Auskunft, dann die Sitzung – aber nur, wenn der Nutzer chatten darf.
 * onInfo meldet die Auskunft sofort, damit Hinweise nicht auf die Sitzung warten.
 */
export async function openChat(
  boardId: number, source: ChatSource, onInfo?: (info: ChatInfo) => void,
): Promise<ChatOpening> {
  const info = await source.chatInfo(boardId)
  onInfo?.(info)
  if (!info.can_start) return { info, started: null, showIntro: false }
  const started = await source.startChat(boardId)
  // Der Agent weiß nicht von selbst, um welches Board es geht: Bei einer neuen Sitzung steht der Text offen da.
  return { info, started, showIntro: !started.reused }
}

/** Was das Ergänzen der Werkzeuge braucht (blueprintApi erfüllt das). */
export interface ToolSource {
  addTools: (agentId: string, missing: string[]) => Promise<void>
  chatInfo: (id: number) => Promise<ChatInfo>
}
export interface ToolsResult { info: ChatInfo; toolsError: string | null }

/**
 * Fehlende Werkzeuge am Agenten ergänzen und die Auskunft neu holen. Scheitert das (z. B. ein vom Modul
 * verwalteter Agent, 409 agent_managed), bleibt die Auskunft stehen und der Grund kommt als Text zurück:
 * Der Chat selbst steht ja, nur das Ergänzen ging nicht.
 */
export async function addMissingTools(
  boardId: number, info: ChatInfo, source: ToolSource, describe: (problem: unknown) => string,
): Promise<ToolsResult> {
  if (!info.agent) return { info, toolsError: null }
  try {
    await source.addTools(info.agent.id, info.tools_missing)
    return { info: await source.chatInfo(boardId), toolsError: null }
  } catch (problem) {
    return { info, toolsError: describe(problem) }
  }
}
