// Ghostwriter G3 – Server-Aufrufe für das Interview je Kapitel und für das Diktat (Kern-Spracherkennung /api/stt).
import { authHeader, errorFrom, storyBase, StoryApiError } from "./api"
import type { Interview, Question } from "./interviewModel"

async function call<T>(url: string, method: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(url, { method, headers: { "Content-Type": "application/json", ...authHeader() },
      body: body === undefined ? undefined : JSON.stringify(body) })
  } catch (e) {
    throw new StoryApiError(0, "network", undefined, String(e))
  }
  if (!res.ok) throw await errorFrom(res)
  return (await res.json()) as T
}

const iv = (pid: string, bid: string, cid: string) => `${storyBase(pid, bid)}/interviews/${encodeURIComponent(cid)}`

export const interviewApi = {
  get: (pid: string, bid: string, cid: string) => call<Interview>(iv(pid, bid, cid), "GET"),
  save: (pid: string, bid: string, cid: string, baseVersion: number, questions: Question[]) =>
    call<Interview>(iv(pid, bid, cid), "PUT", { base_version: baseVersion, questions }),
  suggest: (pid: string, bid: string, cid: string, count: number) =>
    call<{ questions: string[] }>(`${iv(pid, bid, cid)}/questions`, "POST", { count }),
}

/** Aufnahme an die Kern-Spracherkennung schicken; gibt den erkannten Text zurück. */
export async function transcribe(blob: Blob, mime: string): Promise<string> {
  const form = new FormData()
  const ext = mime.startsWith("audio/mp4") ? "m4a" : mime.startsWith("audio/ogg") ? "ogg" : "webm"
  form.append("audio", blob, `audio.${ext}`)
  let res: Response
  try {
    res = await fetch("/api/stt", { method: "POST", headers: authHeader(), body: form })
  } catch (e) {
    throw new StoryApiError(0, "network", undefined, String(e))
  }
  if (!res.ok) {
    const err = await errorFrom(res)
    throw new StoryApiError(res.status, "stt_failed", undefined, err.message)
  }
  return ((await res.json()) as { text?: string }).text ?? ""
}
