// Ein Ghostwriter-Lauf ohne React (testbar, ghostRun.test.ts): erst speichern (Zusammenfassung und
// Steckbriefe müssen auf dem Server sein), dann streamen. Der Abbruch-Schalter gilt ab dem ersten
// Moment – auch während noch gespeichert wird, sonst liefe danach ein Lauf los, den keiner mehr will.
import { StoryApiError } from "./api"
import type { GhostDone } from "./ghostStream"

export interface RunDeps {
  flush: () => Promise<unknown>
  stream: (onText: (t: string) => void, signal: AbortSignal) => Promise<GhostDone>
}

export type RunResult =
  | { kind: "done"; text: string; done: GhostDone }
  | { kind: "aborted"; text: string }
  | { kind: "error"; text: string; error: StoryApiError }

export async function runGhost(deps: RunDeps, ctrl: AbortController, onText: (all: string) => void): Promise<RunResult> {
  let text = ""
  try {
    await deps.flush()
    if (ctrl.signal.aborted) return { kind: "aborted", text }
    const done = await deps.stream((t) => { text += t; onText(text) }, ctrl.signal)
    return { kind: "done", text, done }
  } catch (e) {
    const error = e instanceof StoryApiError ? e : new StoryApiError(0, "llm_failed", undefined, String(e))
    return error.code === "aborted" || ctrl.signal.aborted ? { kind: "aborted", text } : { kind: "error", text, error }
  }
}
