import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
const post = vi.fn((..._a: unknown[]) => Promise.resolve({}))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: (...a: unknown[]) => post(...a), put: vi.fn(), delete: vi.fn() } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import type { LibraryItem } from "./api"
import { afterPhoto, castNames, describeApi, needsDescription } from "./elementPhotoLogic"
import { ElementForm } from "./ElementForm"
import { ElementPhoto } from "./ElementPhoto"
import { MediaActions } from "./MediaActions"
import { studioI18n } from "./i18n"
import type { PlanElement, Shot } from "./planApi"
import { ShotForm } from "./ShotForm"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const el = (p: Partial<PlanElement> = {}): PlanElement => ({ id: "h", kind: "character", name: "Hydra", description: "", style_anchor: "", palette: [], references: [], ...p } as PlanElement)
const shot = (p: Partial<Shot> = {}): Shot => ({ id: "s", shot: "", prompt: "Hydra fliegt", element_ids: [], duration: 5, status: "planned",
  image_rel: null, video_rel: null, variants: [], ...p } as Shot)

describe("C2 – Logik", () => {
  it("Namen im Bild aus `cast`, mit Hinweis auf Foto", () => {
    const els = [el({ id: "h", name: "Hydra", references: ["a.png"] }), el({ id: "l", name: "Leuchtturm", kind: "place" })]
    expect(castNames(["l", "h", "weg"], els)).toEqual([{ id: "l", name: "Leuchtturm", photo: false }, { id: "h", name: "Hydra", photo: true }])
    expect(castNames(undefined, els)).toEqual([])
  })

  it("automatisch beschreiben nur, wenn Foto da und beide Felder leer", () => {
    expect(needsDescription(el({ references: ["a.png"] }))).toBe(true)
    expect(needsDescription(el({ references: ["a.png"], description: "x" }))).toBe(false)
    expect(needsDescription(el({ references: ["a.png"], style_anchor: "x" }))).toBe(false)
    expect(needsDescription(el())).toBe(false)
  })

  it("nach dem Foto: beschreiben nur, wenn nötig", async () => {
    const d = vi.fn()
    expect(await afterPhoto(el({ references: ["a.png"] }), d)).toBe(true)
    expect(d).toHaveBeenCalledTimes(1)
    expect(await afterPhoto(el({ references: ["a.png"], description: "schon da" }), d)).toBe(false)
    expect(await afterPhoto(null, d)).toBe(false)
    expect(d).toHaveBeenCalledTimes(1)
  })

  it("Hochladen ruft danach afterPhoto mit dem gespeicherten Baustein", () => {
    const src = Object.values(import.meta.glob("./useUploads.ts", { query: "?raw", import: "default", eager: true })).join("")
    expect(src).toMatch(/saved = await uploadApi\.reference\(/)
    expect(src).toMatch(/if \(ok\) void afterPhoto\(saved, \(\) => describe\(elementId, null\)\)/)
  })

  it("API: beschreiben und aus Bibliotheksbild anlegen", () => {
    void describeApi.describe("p1", "h")
    expect(post).toHaveBeenLastCalledWith("/modules/studio/projects/p1/plan/elements/h/describe", {})
    void describeApi.fromImage("p1", { rel: "studio/media/uploads/a.png", kind: "place", name: "Leuchtturm" })
    expect(post).toHaveBeenLastCalledWith("/modules/studio/projects/p1/plan/elements/from-image", { rel: "studio/media/uploads/a.png", kind: "place", name: "Leuchtturm" })
  })
})

describe("C2 – Foto ganz oben im Baustein", () => {
  it("ohne Foto: großes Feld „Foto hierher ziehen oder auswählen“ mit Erklärung", () => {
    const out = html(<ElementPhoto element={el()} base="/w" busy={false} uploading={false} describing={false} onUpload={noop} onRemove={noop} onDescribe={noop} />)
    expect(out).toContain("photo_drop")
    expect(out).toContain('photo_why:{"name":"Hydra"}')
    expect(out).toMatch(/<button[^>]*data-element-photo-pick/)
    expect(out).not.toContain("data-element-describe")                              // ohne Foto nichts zu beschreiben
  })

  it("mit Foto: Fotos groß, „Aus dem Foto beschreiben (≈ 0,1 ct)“", () => {
    const onDescribe = vi.fn()
    const out = html(<ElementPhoto element={el({ references: ["studio/media/uploads/a.png"] })} base="/w" busy={false} uploading={false}
      describing={false} onUpload={noop} onRemove={noop} onDescribe={onDescribe} />)
    expect(out).toContain('src="/f/w/studio/media/uploads/a.png"')
    expect(out).toMatch(/<button[^>]*data-element-describe[^>]*>.*photo_describe/s)
    expect(out).toContain("photo_more")
  })

  it("während des Beschreibens: Knopf gesperrt, „Die KI schaut sich das Foto an …“", () => {
    const out = html(<ElementPhoto element={el({ references: ["a.png"] })} base="/w" busy={false} uploading={false} describing onUpload={noop} onRemove={noop} onDescribe={noop} />)
    expect(out).toMatch(/<button[^>]*disabled=""[^>]*data-element-describe/)
    expect(out).toContain("photo_describing")
  })

  it("Formular: Foto-Bereich steht vor Name und Beschreibung", () => {
    const out = html(<ElementForm element={el()} base="/w" images={[]} busy={false} onSave={noop} onDelete={noop} onUploadReference={noop} onDescribe={noop} />)
    expect(out.indexOf("photo_drop")).toBeGreaterThan(-1)
    expect(out.indexOf("photo_drop")).toBeLessThan(out.indexOf('data-field="name"'))
  })
})

describe("C2 – Im Shot sichtbar, wer im Bild ist", () => {
  it("„Mit im Bild: Leuchtturm, Hydra (mit Foto)“; Häkchen heißen „Zusätzlich im Bild“", () => {
    const els = [el({ id: "h", references: ["a.png"] }), el({ id: "l", name: "Leuchtturm", kind: "place" })]
    const out = html(<ShotForm shot={{ ...shot(), cast: ["l", "h"] } as Shot} index={0} elements={els} sceneElementIds={[]} presets={[]} busy={false} onSave={noop} onDelete={noop} />)
    expect(out).toContain("shot_cast_title")
    expect(out).toMatch(/data-shot-cast="l"[^>]*>Leuchtturm/)
    expect(out).toMatch(/data-shot-cast="h"[^>]*>Hydra.*shot_cast_photo/s)
    expect(out).toContain("shot_cast_hint")
    expect(out).toContain("shot_extra_elements")
  })

  it("niemand im Bild: Hinweis, dass Namen im Text reichen", () => {
    const out = html(<ShotForm shot={{ ...shot({ prompt: "Wellen" }), cast: [] } as Shot} index={0} elements={[el()]} sceneElementIds={[]} presets={[]} busy={false} onSave={noop} onDelete={noop} />)
    expect(out).toContain("shot_cast_none")
  })

  it("alle Bausteine zum Anhaken, nicht nur die der Szene", () => {
    const els = [el({ id: "h" }), el({ id: "m", name: "Mira" })]
    const out = html(<ShotForm shot={shot()} index={0} elements={els} sceneElementIds={["h"]} presets={[]} busy={false} onSave={noop} onDelete={noop} />)
    expect(out).toContain('data-shot-element="m"')
    expect(out).toContain('data-shot-element="h"')
  })
})

describe("C2 – Bibliothek: „Als Figur anlegen …“ / „Als Ort anlegen …“", () => {
  const img: LibraryItem = { id: "i", kind: "image", origin: "upload", source: "studio_upload", name: "Hydra Foto", rel: "studio/media/uploads/a.png",
    abs: "/w/studio/media/uploads/a.png", size: 1, created_at: "x", deletable: true }
  it("nur bei Bildern", () => {
    const out = html(<MediaActions item={img} onDelete={noop} onCreateElement={noop} />)
    expect(out).toMatch(/data-media-as="character"[^>]*>.*media_as_character/s)
    expect(out).toMatch(/data-media-as="place"[^>]*>.*media_as_place/s)
    expect(html(<MediaActions item={{ ...img, kind: "video" }} onDelete={noop} onCreateElement={noop} />)).not.toContain("data-media-as")
  })
})

describe("C2 – Texte", () => {
  it("de/en vorhanden", () => {
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio as unknown as Record<string, unknown> & { err: Record<string, string> }
      for (const k of ["photo_drop", "photo_why", "photo_describe", "photo_describing", "photo_more", "photo_described", "shot_cast_title",
        "shot_cast_photo", "shot_cast_hint", "shot_cast_none", "shot_extra_elements", "media_as_character", "media_as_place", "media_as_name",
        "media_as_done"]) expect(s[k], `${lang} ${k}`).toBeTruthy()
      for (const c of ["studio_describe_no_image", "studio_describe_failed", "studio_describe_no_key"]) expect(s.err[c], `${lang} ${c}`).toBeTruthy()
    }
  })
})

describe("C2 – Meldung nach „Als Ort anlegen …“ landet in „Planen“", () => {
  it("useMediaTools gibt planNotice an das Anlegen weiter (nicht die Meldung des Reiters, der gleich verlassen wird)", () => {
    const src = Object.values(import.meta.glob(["./useMediaTools.tsx", "./StudioPage.tsx"], { query: "?raw", import: "default", eager: true })).join("\n")
    expect(src).toMatch(/useElementFromImage\(projectId, \(id\) => \{ clearMedia\(\); openElement\(id\) \}, planNotice\)/)
    expect(src).toMatch(/planNotice: p\.setNotice/)
  })
})
