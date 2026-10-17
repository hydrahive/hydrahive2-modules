import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { CutInspector } from "./CutInspector"
import { CutTimeline } from "./CutTimeline"
import { CutToolbar } from "./CutToolbar"
import { editAction } from "./cutKeys"
import type { Timeline, TimelineClip } from "./timelineApi"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const clip = (p: Partial<TimelineClip>): TimelineClip => ({ id: "c", kind: "image", start: 0, in: 0, out: 5, media_rel: "studio/media/images/a.png",
  scene_id: "", shot_id: "", label: "x", ...p })
const TL: Timeline = { revision: 1, fps: 25, tracks: [{ id: "V1", kind: "video", clips: [clip({ id: "a", out: 4 }), clip({ id: "b", start: 4, out: 6 })] }] }
const bar = (p: Partial<React.ComponentProps<typeof CutToolbar>> = {}) => html(<CutToolbar save="saved" selected="a" canUndo canRedo={false}
  canSplit snap onAction={noop} onSnap={noop} onReload={noop} {...p} />)

describe("4b – Werkzeugleiste", () => {
  it("Knöpfe für Teilen, Löschen, Verdoppeln, Rückgängig, Wiederholen, Einrasten; ohne Auswahl gesperrt", () => {
    const out = bar()
    for (const a of ["split", "delete", "duplicate", "undo", "redo"]) expect(out).toContain(`data-cut-action="${a}"`)
    expect(out.match(/<button[^>]*data-cut-action="redo"[^>]*>/)?.[0]).toContain(' disabled=""')
    expect(out.match(/<button[^>]*data-cut-action="undo"[^>]*>/)?.[0]).not.toContain(' disabled=""')
    expect(bar({ canUndo: false }).match(/<button[^>]*data-cut-action="undo"[^>]*>/)?.[0]).toContain(' disabled=""')
    expect(out).toMatch(/data-cut-snap[^>]*aria-pressed="true"|aria-pressed="true"[^>]*data-cut-snap/)
    const none = bar({ selected: null, canSplit: false })
    for (const a of ["split", "delete", "duplicate"]) expect(none.match(new RegExp(`<button[^>]*data-cut-action="${a}"[^>]*>`))?.[0]).toContain(' disabled=""')
  })

  it("Speicherstand sichtbar; Konflikt mit „Neu laden“", () => {
    expect(bar({ save: "saved" })).toContain('data-cut-save="saved"')
    expect(bar({ save: "saving" })).toContain("cut_save.saving")
    expect(bar({ save: "error" })).toContain("cut_save.error")
    const c = bar({ save: "conflict" })
    expect(c).toContain("cut_save.conflict")
    expect(c).toContain("data-cut-reload")
    expect(bar({ save: "saved" })).not.toContain("data-cut-reload")
  })
})

describe("4b – Zeitleiste zum Bearbeiten", () => {
  it("Clips haben Griffe zum Kürzen und sind ziehbar; Ablage aus der Bibliothek möglich", () => {
    const out = html(<CutTimeline timeline={TL} base="/w" time={0} view={{ start: 0, span: 10 }} selected="a" busy={false}
      onView={noop} onSeek={noop} onSelect={noop} onFromPlan={noop} edit={{ onMove: noop, onTrim: noop, onDrop: noop, dropAt: null, snapTo: [] }} />)
    expect(out).toContain('data-cut-trim="a:start"')
    expect(out).toContain('data-cut-trim="b:end"')
    expect(out).toMatch(/data-cut-clip="a"[^>]*draggable="true"/)
    expect(out).toContain("data-cut-dropzone")
  })

  it("Einfügemarke beim Ziehen", () => {
    const out = html(<CutTimeline timeline={TL} base="/w" time={0} view={{ start: 0, span: 10 }} selected={null} busy={false}
      onView={noop} onSeek={noop} onSelect={noop} onFromPlan={noop} edit={{ onMove: noop, onTrim: noop, onDrop: noop, dropAt: 4, snapTo: [] }} />)
    expect(out).toMatch(/data-cut-insert[^>]*style="left:40%"/)
  })
})

describe("4b – Bibliothek und Tasten", () => {
  it("Eigenschaften eines Mediums: „An die Zeitleiste anhängen“ nur für Bild/Video", () => {
    expect(html(<CutInspector clip={null} onPlan={noop} media={{ kind: "image", name: "Leuchtturm" }} onAppend={noop} />)).toContain("data-cut-append")
    const music = html(<CutInspector clip={null} onPlan={noop} media={{ kind: "music", name: "M" }} onAppend={noop} />)
    expect(music).not.toContain("data-cut-append")
    expect(music).toContain("cut_no_audio_yet")
  })

  it("Tasten → Bearbeitung (nur im Reiter Schneiden)", () => {
    expect(editAction("split")).toEqual({ kind: "split" })
    expect(editAction("split-left")).toEqual({ kind: "split-keep", drop: "left" })
    expect(editAction("split-right")).toEqual({ kind: "split-keep", drop: "right" })
    expect(editAction("delete")).toEqual({ kind: "delete" })
    expect(editAction("duplicate")).toEqual({ kind: "duplicate" })
    expect(editAction("copy")).toEqual({ kind: "copy" })
    expect(editAction("paste")).toEqual({ kind: "paste" })
    expect(editAction("undo")).toEqual({ kind: "undo" })
    expect(editAction("redo")).toEqual({ kind: "redo" })
    expect(editAction("toggle-play")).toBeNull()
    expect(editAction("marker")).toBeNull()
  })
})
