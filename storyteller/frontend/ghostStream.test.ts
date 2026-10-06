import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/features/auth/useAuthStore", () => ({
  useAuthStore: { getState: () => ({ token: "tok", logout: vi.fn() }) },
}))

import { StoryApiError } from "./api"
import { parseSse, streamGhostScene } from "./ghostStream"

const enc = new TextEncoder()
function body(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(c) { for (const ch of chunks) c.enqueue(enc.encode(ch)); c.close() },
  })
}

describe("parseSse", () => {
  it("setzt Ereignisse über Stück-Grenzen zusammen", () => {
    const st = { buf: "" }
    const a = parseSse(st, 'event: delta\ndata: {"text":"Hal')
    expect(a).toEqual([])
    const b = parseSse(st, 'lo"}\n\nevent: done\ndata: {"words":1,"model":"","mode":"fill"}\n\n')
    expect(b).toEqual([{ event: "delta", data: { text: "Hallo" } }, { event: "done", data: { words: 1, model: "", mode: "fill" } }])
    expect(st.buf).toBe("")
  })
  it("ignoriert kaputte Blöcke statt abzustürzen", () => {
    expect(parseSse({ buf: "" }, "event: delta\ndata: {kaputt\n\n")).toEqual([])
  })
})

describe("streamGhostScene", () => {
  const fetchMock = vi.fn()
  beforeEach(() => { vi.stubGlobal("fetch", fetchMock) })
  afterEach(() => { fetchMock.mockReset(); vi.unstubAllGlobals() })

  it("liest Text live, meldet Ende; Token im Header, nicht in der URL", async () => {
    fetchMock.mockResolvedValue(new Response(body([
      'event: delta\ndata: {"text":"Als "}\n\nevent: del', 'ta\ndata: {"text":"Gregor"}\n\n',
      'event: done\ndata: {"words":2,"model":"x/y","mode":"fill"}\n\n',
    ]), { status: 200, headers: { "content-type": "text/event-stream" } }))
    const seen: string[] = []
    const done = await streamGhostScene("p", "b", { scene_id: "s" }, (t) => seen.push(t), new AbortController().signal)
    expect(seen.join("")).toBe("Als Gregor")
    expect(done).toEqual({ words: 2, model: "x/y", mode: "fill" })
    const [url, init] = fetchMock.mock.calls[0]
    expect(url).not.toContain("tok")
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok")
  })

  it("Fehler-Ereignis wird zu StoryApiError mit lesbarer Meldung", async () => {
    fetchMock.mockResolvedValue(new Response(body(['event: error\ndata: {"code":"llm_failed","message":"Schlüssel fehlt"}\n\n']), { status: 200 }))
    await expect(streamGhostScene("p", "b", { scene_id: "s" }, () => {}, new AbortController().signal))
      .rejects.toMatchObject({ code: "llm_failed", message: "Schlüssel fehlt" })
  })

  it("HTTP-Fehler vor dem Start (z. B. 409 ai_busy) kommt als StoryApiError", async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ detail: { code: "ai_busy", message: "läuft schon" } }), { status: 409 }))
    const err = await streamGhostScene("p", "b", { scene_id: "s" }, () => {}, new AbortController().signal).catch((e) => e)
    expect(err).toBeInstanceOf(StoryApiError)
    expect(err).toMatchObject({ status: 409, code: "ai_busy" })
  })

  it("Stream endet ohne done → Fehler statt stiller Erfolg", async () => {
    fetchMock.mockResolvedValue(new Response(body(['event: delta\ndata: {"text":"halb"}\n\n']), { status: 200 }))
    await expect(streamGhostScene("p", "b", { scene_id: "s" }, () => {}, new AbortController().signal))
      .rejects.toMatchObject({ code: "stream_incomplete" })
  })

  it("Abbrechen: AbortError wird als „aborted“ gemeldet", async () => {
    const ctrl = new AbortController()
    fetchMock.mockImplementation((_u: string, init: RequestInit) => new Promise((_, rej) => {
      init.signal?.addEventListener("abort", () => rej(new DOMException("aborted", "AbortError")))
    }))
    const p = streamGhostScene("p", "b", { scene_id: "s" }, () => {}, ctrl.signal)
    ctrl.abort()
    await expect(p).rejects.toMatchObject({ code: "aborted" })
  })
})
