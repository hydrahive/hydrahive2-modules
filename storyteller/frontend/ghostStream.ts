// Ghostwriter-Stream lesen (Server-Sent Events über fetch, damit das Token im Header bleibt und
// nicht in der URL steht). Liefert Text live über onText, am Ende die Abschlussdaten.
import { authHeader, errorFrom, storyBase, StoryApiError } from "./api"

export interface GhostDone { words: number; model: string; mode: "fill" | "proposal" }
export interface GhostSceneRequest { scene_id: string; length_words?: number; model?: string }
interface SseEvent { event: string; data: Record<string, unknown> }

/** Ereignisse aus einem Stück lesen; Unvollständiges bleibt im Puffer bis zum nächsten Stück. */
export function parseSse(state: { buf: string }, chunk: string): SseEvent[] {
  state.buf += chunk
  const out: SseEvent[] = []
  let i: number
  while ((i = state.buf.indexOf("\n\n")) >= 0) {
    const block = state.buf.slice(0, i)
    state.buf = state.buf.slice(i + 2)
    let event = "message"
    let data = ""
    for (const line of block.split("\n")) {
      if (line.startsWith("event: ")) event = line.slice(7)
      else if (line.startsWith("data: ")) data += line.slice(6)
    }
    try { out.push({ event, data: JSON.parse(data) as Record<string, unknown> }) } catch { /* kaputter Block */ }
  }
  return out
}

export async function streamGhostScene(
  projectId: string, bookId: string, req: GhostSceneRequest, onText: (t: string) => void, signal: AbortSignal,
): Promise<GhostDone> {
  let res: Response
  try {
    res = await fetch(`${storyBase(projectId, bookId)}/ghost/scene`, {
      method: "POST", signal,
      headers: { "Content-Type": "application/json", Accept: "text/event-stream", ...authHeader() },
      body: JSON.stringify(req),
    })
  } catch (e) {
    throw aborted(e) ?? new StoryApiError(0, "network", undefined, String(e))
  }
  if (!res.ok || !res.body) throw await errorFrom(res)
  const reader = res.body.getReader()
  const dec = new TextDecoder()
  const state = { buf: "" }
  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) break
      for (const ev of parseSse(state, dec.decode(value, { stream: true }))) {
        if (ev.event === "delta") onText(String(ev.data.text ?? ""))
        else if (ev.event === "done") return ev.data as unknown as GhostDone
        else if (ev.event === "error") {
          throw new StoryApiError(502, String(ev.data.code ?? "llm_failed"), undefined, String(ev.data.message ?? ""))
        }
      }
    }
  } catch (e) {
    throw aborted(e) ?? e
  } finally {
    reader.releaseLock()
  }
  throw new StoryApiError(502, "stream_incomplete")
}

function aborted(e: unknown): StoryApiError | null {
  return e instanceof DOMException && e.name === "AbortError" ? new StoryApiError(0, "aborted") : null
}
