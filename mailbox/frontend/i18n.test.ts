import { describe, expect, it } from "vitest"
import { i18n } from "./i18n"

function keys(o: unknown, p = ""): string[] {
  if (typeof o !== "object" || o === null) return [p]
  return Object.entries(o).flatMap(([k, v]) => keys(v, p ? `${p}.${k}` : k))
}

describe("i18n", () => {
  it("de und en haben genau dieselben Schlüssel", () => {
    expect(keys(i18n.en).sort()).toEqual(keys(i18n.de).sort())
  })
  it("Platzhalter gleich in beiden Sprachen", () => {
    const at = (root: unknown, k: string) =>
      String(k.split(".").reduce<unknown>((o, x) => (o as Record<string, unknown>)[x], root))
    const de = Object.fromEntries(keys(i18n.de).map((k) => [k, at(i18n.de, k)]))
    const en = Object.fromEntries(keys(i18n.en).map((k) => [k, at(i18n.en, k)]))
    for (const k of Object.keys(de)) {
      const ph = (s: string) => (s.match(/\{\{\w+\}\}/g) ?? []).sort()
      expect(ph(en[k]), k).toEqual(ph(de[k]))
    }
  })
})
