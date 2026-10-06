// „Annehmen“ beim Ghostwriter (Spec ghostwriter.md §4) – ohne React, damit testbar (ghostAccept.test.ts).
// Regel: nie still überschreiben. Hat die Szene schon Text, wird er vorher als Schnappschuss gesichert;
// schlägt das fehl, wird nichts eingesetzt. Der neue Text bekommt die Herkunft „KI-Entwurf“. Ist die
// Zusammenfassung leer, wird danach das Gedächtnis angestoßen (Fehler dort ändern nichts mehr).
import type { Scene } from "./model"

export interface AcceptDeps {
  snapshot: (sceneId: string) => Promise<boolean>
  replace: (sceneId: string, text: string, origin: Scene["origin"]) => void
  remember: (sceneId: string) => Promise<void>
}

export type AcceptResult = "accepted" | "empty" | "snapshot_failed"

export async function acceptGhostText(proposal: string, scene: Scene, deps: AcceptDeps): Promise<AcceptResult> {
  const text = proposal.trim()
  if (!text) return "empty"
  if (scene.text.trim() && !(await deps.snapshot(scene.id))) return "snapshot_failed"
  deps.replace(scene.id, text, "ai_draft")
  // Gedächtnis nicht abwarten (eigener KI-Aufruf); Fehler dort ändern nichts – Text ist übernommen.
  if (!scene.summary.trim()) void deps.remember(scene.id).catch(() => {})
  return "accepted"
}
