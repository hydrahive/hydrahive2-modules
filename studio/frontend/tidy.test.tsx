import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string, o?: Record<string, unknown>) => (o ? `${k}:${JSON.stringify(o)}` : k) }) }))
vi.mock("@/shared/api-client", () => ({ api: { get: vi.fn(() => new Promise(() => {})), post: vi.fn(), put: vi.fn(), delete: vi.fn() } }))
vi.mock("@/shared/files", () => ({ fileUrl: (p: string) => `/f${p}` }))
import { ColorPick } from "./ColorPick"
import { colorAdd, colorRemove, colorSet, MAX_COLORS } from "./colorLogic"
import { FormActions } from "./formParts"
import { GenerateSideBar } from "./GenerateSideBar"
import { studioI18n } from "./i18n"

const noop = () => {}
const html = (el: React.ReactElement) => renderToStaticMarkup(el).replace(/&quot;/g, '"')
const plan = { scenes: [{ id: "a", title: "Hafen", shots: [] }] } as never

describe("C4 – ein Weg zum Shot", () => {
  it("„Erzeugen“ links: nur noch „Einzelbild (ohne Szene)“, kein „+ Shot“", () => {
    const out = html(<GenerateSideBar plan={plan} free={false} busy={false} onFree={noop} />)
    expect(out).not.toContain("data-gen-add-shot")
    expect(out).toMatch(/<button[^>]*data-gen-free[^>]*>.*gen_free/s)
    expect(out).toContain("gen_free_hint")
  })
})

describe("C4 – Speichern und Löschen im Formular", () => {
  it("ohne Änderung „✓ Gespeichert“ als Text, mit Änderung Knopf „Speichern“", () => {
    const clean = html(<FormActions busy={false} dirty={false} onSave={noop} onDelete={noop} />)
    expect(clean).not.toMatch(/<button[^>]*data-plan-save/)
    expect(clean).toMatch(/data-plan-saved[^>]*>.*saved/s)
    const dirty = html(<FormActions busy={false} dirty onSave={noop} onDelete={noop} />)
    expect(dirty).toMatch(/<button[^>]*data-plan-save[^>]*>.*save/s)
    expect(dirty).not.toContain("data-plan-saved")
  })
  it("„Löschen …“ ist ein beschrifteter Knopf", () => {
    expect(html(<FormActions busy={false} dirty={false} onSave={noop} onDelete={noop} />)).toMatch(/<button[^>]*data-plan-delete[^>]*>.*form_delete/s)
  })
})

describe("C4 – Farben mit Farbwähler", () => {
  it("Logik: setzen, hinzufügen, entfernen, höchstens 12, nur #rrggbb", () => {
    expect(colorSet(["#111111", "#222222"], 1, "#ABCDEF")).toEqual(["#111111", "#abcdef"])
    expect(colorSet(["#111111"], 0, "rot")).toEqual(["#111111"])
    expect(colorAdd(["#111111"])).toEqual(["#111111", "#888888"])
    expect(colorAdd(Array(MAX_COLORS).fill("#000000"))).toHaveLength(MAX_COLORS)
    expect(colorRemove(["#111111", "#222222"], 0)).toEqual(["#222222"])
    expect(MAX_COLORS).toBe(12)
    expect(colorSet(["#abc"], 0, "#123456")).toEqual(["#123456"])
  })
  it("je Farbe ein Farbfeld mit ×, dazu „+ Farbe“; ohne Farben Hinweis", () => {
    const out = html(<ColorPick label="Farben" colors={["#111111", "#ff0000"]} onChange={noop} />)
    expect((out.match(/<input[^>]*type="color"/g) || []).length).toBe(2)
    expect(out).toContain('value="#ff0000"')
    expect((out.match(/data-color-remove/g) || []).length).toBe(2)
    expect(out).toMatch(/<button[^>]*data-color-add[^>]*>.*color_add/s)
    expect(html(<ColorPick label="Farben" colors={[]} onChange={noop} />)).toContain("color_none")
  })
  it("kurze Schreibweise (#abc) wird fürs Farbfeld ausgeschrieben", () => {
    expect(html(<ColorPick label="Farben" colors={["#abc"]} onChange={noop} />)).toContain('value="#aabbcc"')
  })
  it("Baustein und Drehbuch-Kopf benutzen den Farbwähler statt des Textfelds", () => {
    const src = Object.values(import.meta.glob(["./ElementForm.tsx", "./HeadForm.tsx"], { query: "?raw", import: "default", eager: true }))
    for (const s of src) {
      expect(String(s)).toContain("<ColorPick")
      expect(String(s)).not.toContain('name="palette"')
    }
  })
})

describe("C4 – Texte", () => {
  it("de/en vorhanden", () => {
    for (const lang of ["de", "en"] as const) {
      const s = studioI18n[lang].studio as unknown as Record<string, unknown>
      for (const k of ["gen_free_hint", "form_delete", "color_add", "color_none", "color_remove", "color_pick"]) expect(s[k], `${lang} ${k}`).toBeTruthy()
      expect(String(s.gen_free)).toMatch(lang === "de" ? /Einzelbild/ : /Single image/)
    }
  })
})

type El = { type?: unknown; props: Record<string, unknown> & { children?: unknown } }
const find = (node: unknown, ok: (e: El) => boolean, out: El[] = []): El[] => {
  if (Array.isArray(node)) node.forEach((n) => find(n, ok, out))
  else if (node && typeof node === "object" && "props" in node) {
    const el = node as El
    if (ok(el)) out.push(el)
    find(el.props.children, ok, out)
  }
  return out
}

describe("C4 – Farbfelder bedienen", () => {
  it("Feld ändern, × entfernt genau diese Farbe, „+ Farbe“ hängt an; bei 12 kein „+“", () => {
    const onChange = vi.fn()
    const tree = ColorPick({ label: "Farben", colors: ["#111111", "#222222", "#333333"], onChange })
    const inputs = find(tree, (e) => e.type === "input")
    ;(inputs[1].props.onChange as (e: unknown) => void)({ target: { value: "#00ff00" } })
    expect(onChange).toHaveBeenLastCalledWith(["#111111", "#00ff00", "#333333"])
    ;(find(tree, (e) => e.props["data-color-remove"] !== undefined)[1].props.onClick as () => void)()
    expect(onChange).toHaveBeenLastCalledWith(["#111111", "#333333"])
    ;(find(tree, (e) => e.props["data-color-add"] !== undefined)[0].props.onClick as () => void)()
    expect(onChange).toHaveBeenLastCalledWith(["#111111", "#222222", "#333333", "#888888"])
    expect(html(<ColorPick label="F" colors={Array(12).fill("#000000")} onChange={noop} />)).not.toContain("data-color-add")
    expect(colorRemove(["#1", "#2", "#3"], 2)).toEqual(["#1", "#2"])
  })

  it("Baustein und Kopf übernehmen die Farbe (Speichern wird möglich)", async () => {
    const { ElementForm } = await import("./ElementForm")
    const { HeadForm } = await import("./HeadForm")
    for (const [name, src] of Object.entries(import.meta.glob(["./ElementForm.tsx", "./HeadForm.tsx"], { query: "?raw", import: "default", eager: true }))) {
      const s = String(src)
      expect(s, name).toMatch(name.includes("Element") ? /onChange=\{\(c\) => set\("palette", c\)\}/ : /onChange=\{\(c\) => set\("look", \{ \.\.\.h\.look, palette: c \}\)\}/)
    }
    void ElementForm; void HeadForm
  })
})
