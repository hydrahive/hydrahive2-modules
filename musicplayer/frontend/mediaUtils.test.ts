import { describe, expect, it } from "vitest"
import { filterByKind, groupedSources, MEDIA_ACCEPT, trackSubtitle } from "./mediaUtils"

const video = { media_kind: "video" as const, id: 1 }
const audio = { media_kind: "audio" as const, id: 2 }
describe("Mediaplayer-Helfer", () => {
  it("filtert Bibliothek und Quellen strikt nach Medienart", () => {
    expect(filterByKind([video, audio], "video")).toEqual([video])
    expect(filterByKind([{ ...video, kind: "video" as const }, { ...audio, kind: "audio" as const }], "audio")).toHaveLength(1)
  })
  it("liefert erlaubte Endungen je Medienart", () => {
    expect(MEDIA_ACCEPT.audio).toContain(".flac"); expect(MEDIA_ACCEPT.video).toBe(".mp4,.webm")
  })
  it("gruppiert Quellen und zeigt gekürzten Prompt samt Modell und Dauer", () => {
    const sources = [{ group: "Atelier", path: "a" }, { group: "Atelier", path: "b" }, { group: "Agent", path: "c" }] as never[]
    expect(groupedSources(sources)).toEqual([["Atelier", [sources[0], sources[1]]], ["Agent", [sources[2]]]])
    expect(trackSubtitle({ prompt: "abcdef", model: "X", duration: 12 }, 5)).toEqual({ text: "abcd… · X · 12", promptTitle: "abcdef" })
  })
})
