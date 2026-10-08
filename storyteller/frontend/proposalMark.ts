// Vorschlags-Markierung je Szene (Hinweis über dem Editor). T1a (Task 29fb3911): Wortzahl der Szene beim Ablegen,
// damit die Oberfläche warnt, wenn ein Vorschlag die Szene stark verkürzen würde.
import type { ProposalInfo } from "./api"

/** Kurzinfo eines abgelegten Vorschlags je Szene. */
export interface ProposalMark {
  words: number; model: string; at: string; source?: "run" | "agent"; note?: string; sceneWords?: number
  /** A2: Agent-Name des Vorschlags und wessen Vorschlag er ersetzt hat. */
  author?: string; replacedFrom?: string
}

/** Unter diesem Anteil der Szene gilt ein Vorschlag als „deutlich kürzer“ (wie der Server, agent_tools/propose.py). */
export const SHRINK = 0.5

export function markOf(p: ProposalInfo): ProposalMark {
  return { words: p.words, model: p.model, at: p.at, source: p.source ?? "run", note: p.note ?? "", sceneWords: p.scene_words ?? 0,
    author: p.author ?? "", replacedFrom: p.replaced_from?.author ?? "" }
}

export function shrinks(m: ProposalMark): boolean {
  return (m.sceneWords ?? 0) > 0 && m.words < (m.sceneWords ?? 0) * SHRINK
}
