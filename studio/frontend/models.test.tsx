import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})) } }))
import { CATALOG_SOURCES, modelOptions, toCatalog } from "./modelCatalog"
import { ModelPick } from "./ModelPick"
import { studioI18n } from "./i18n"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const CAT = toCatalog({
  default: "google/veo-3.1",
  models: [
    { id: "x-ai/grok-imagine-video-1.5-lite", name: "Grok Imagine Video Lite" },
    { id: "google/veo-3.1" },
    { id: "local:wan", name: "Wan lokal", local: true, provider: "Werkstatt-PC" },
  ],
})

describe("Modelle im Drehbuch – aus dem Katalog", () => {
  it("jede Art hat ihre Quelle im Katalog", () => {
    expect(CATALOG_SOURCES).toEqual({
      video: "/llm/media-models?category=video",
      image: "/llm/media-models?category=image",
      music: "/llm/media-models?category=audio",
      voice: "/llm/models?modality=tts",
      text: "/llm/models?modality=chat",
    })
  })

  it("Katalog-Antwort wird einheitlich (name oder label, Standard, lokal)", () => {
    expect(CAT.default).toBe("google/veo-3.1")
    expect(CAT.models.map((m) => [m.id, m.name, !!m.local])).toEqual([
      ["x-ai/grok-imagine-video-1.5-lite", "Grok Imagine Video Lite", false],
      ["google/veo-3.1", "google/veo-3.1", false],
      ["local:wan", "Wan lokal", true],
    ])
    const reg = toCatalog({ default: "claude-sonnet-4-6", models: [{ id: "openai-codex/gpt-6-astra", label: "GPT-6 Astra", provider: "openai-codex" }] })
    expect(reg.models[0].name).toBe("GPT-6 Astra")
    expect(toCatalog(null)).toEqual({ default: "", models: [] })
    const odd = toCatalog({ models: [{ id: "a/leer", name: "" }, { name: "ohne ID" }, { id: "" }, null, "x", { id: 5 }] })
    expect(odd.models).toEqual([{ id: "a/leer", name: "a/leer" }])                  // leerer Name → ID; ohne gültige ID → weg
    expect(toCatalog({ models: "kaputt" })).toEqual({ default: "", models: [] })
  })

  it("Gruppen: Cloud, lokal je Gerät; gespeicherter Wert außerhalb der Liste bleibt erhalten", () => {
    const g = modelOptions(CAT, "", "")
    expect(g.map((x) => [x.group, x.models.map((m) => m.id)])).toEqual([
      ["cloud", ["x-ai/grok-imagine-video-1.5-lite", "google/veo-3.1"]],
      ["local:Werkstatt-PC", ["local:wan"]],
    ])
    const kept = modelOptions(CAT, "alt/modell-weg", "")
    expect(kept[0]).toEqual({ group: "kept", models: [{ id: "alt/modell-weg", name: "alt/modell-weg" }] })
    expect(modelOptions(CAT, "google/veo-3.1", "")[0].group).toBe("cloud")      // in der Liste → keine Extra-Gruppe
  })

  it("Suche filtert nach ID und Name, die Auswahl bleibt immer sichtbar", () => {
    const g = modelOptions(CAT, "google/veo-3.1", "grok")
    expect(g.flatMap((x) => x.models.map((m) => m.id))).toEqual(["google/veo-3.1", "x-ai/grok-imagine-video-1.5-lite"])
    expect(modelOptions(CAT, "", "WAN LOKAL").flatMap((x) => x.models.map((m) => m.id))).toEqual(["local:wan"])
  })

  it("Auswahlliste: „Standard“ mit Namen des Standards oben, Gruppen, gewählter Wert", () => {
    const out = html(<ModelPick kind="video" value="x-ai/grok-imagine-video-1.5-lite" catalog={CAT} onChange={noop} />)
    expect(out).toMatch(/<select[^>]*data-field="model_video"/)
    expect(out).toContain('<option value="">model_default:{"model":"google/veo-3.1"}</option>')
    expect(out).toContain('label="model_group_cloud"')
    expect(out).toContain('label="model_group_local:{"device":"Werkstatt-PC"}"')
    expect(out).toMatch(/<option value="x-ai\/grok-imagine-video-1\.5-lite" selected="">Grok Imagine Video Lite<\/option>/)
    expect(out).not.toContain("data-model-search")                           // kleine Liste ohne Suche
  })

  it("Auswahlliste und Suchfeld tragen beide einen Namen (Suchfeld nicht im selben <label> wie die Liste)", () => {
    const many = toCatalog({ default: "a/0", models: Array.from({ length: 40 }, (_, i) => ({ id: `a/${i}` })) })
    const out = html(<ModelPick kind="text" value="" catalog={many} onChange={noop} />)
    expect(out).toMatch(/<select[^>]*aria-label="gen\.text"/)
    expect(out).toMatch(/<input[^>]*type="search"[^>]*aria-label="model_search_for:\{"what":"gen\.text"\}"/)
    expect(out).not.toMatch(/<label[^>]*>(?:(?!<\/label>).)*<input[^>]*type="search"/s)      // Suchfeld nicht im Label
  })

  it("große Liste (Text): mit Suchfeld; leerer Katalog: Textfeld mit Hinweis; lädt: Hinweis", () => {
    const many = toCatalog({ default: "a/0", models: Array.from({ length: 40 }, (_, i) => ({ id: `a/${i}` })) })
    expect(html(<ModelPick kind="text" value="" catalog={many} onChange={noop} />)).toContain("data-model-search")
    const empty = html(<ModelPick kind="voice" value="local/piper" catalog={toCatalog({ models: [] })} onChange={noop} />)
    expect(empty).toMatch(/<input[^>]*value="local\/piper"[^>]*data-field="model_voice"|<input[^>]*data-field="model_voice"[^>]*value="local\/piper"/)
    expect(empty).toContain("model_catalog_empty")
    expect(html(<ModelPick kind="image" value="" catalog={null} onChange={noop} />)).toContain("loading")
  })

  it("Beschriftungen der Felder sind übersetzt (kein „gen.video“)", () => {
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio as Record<string, unknown>
      const gen = s.gen as Record<string, string> | undefined
      expect(gen && Object.keys(gen).sort()).toEqual(["image", "music", "text", "video", "voice"])
    }
  })
})
