// Ghostwriter G4e – Chat-Fenster im Storyteller ohne React: Zustand (offen, Breite) im Browser merken, Breite
// begrenzen. Das Fenster selbst ist die Kern-Chatansicht (ChatPane), hier nur der Rahmen.
export const DOCK_KEY = "storyteller.chatDock"
export const DOCK_MIN = 360
export const DOCK_DEFAULT = 520
export interface DockState { open: boolean; width: number }

/** Breite zwischen DOCK_MIN und 60 % des Fensters (mindestens DOCK_MIN). */
export function clampWidth(width: number, viewport: number): number {
  const max = Math.max(DOCK_MIN, Math.floor(viewport * 0.6))
  if (!Number.isFinite(width)) return Math.min(DOCK_DEFAULT, max)
  return Math.min(max, Math.max(DOCK_MIN, Math.round(width)))
}

export function readDock(raw: string | null, viewport: number): DockState {
  try {
    const v = JSON.parse(raw ?? "") as Partial<DockState>
    return { open: v.open === true, width: clampWidth(typeof v.width === "number" ? v.width : DOCK_DEFAULT, viewport) }
  } catch {
    return { open: false, width: clampWidth(DOCK_DEFAULT, viewport) }
  }
}
