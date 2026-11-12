import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"
import { describe, expect, it, vi } from "vitest"

// Der Modul-Index des Kerns importiert dieses Modul; ohne diese Mocks entsteht im Test ein Import-Kreis.
vi.mock("@/shared/api-client", () => ({ api: {} }))
vi.mock("@/shared/CollapsibleBox", () => ({ CollapsibleBox: () => null }))
import { i18n } from "./index"
import { de } from "./texts.de"
import { en } from "./texts.en"

function dateien(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name)
    if (statSync(path).isDirectory()) return dateien(path)
    return /\.tsx?$/.test(name) && !/\.test\.tsx?$/.test(name) && !/^(texts\.(de|en)|i18nMock)\.ts$/.test(name) ? [path] : []
  })
}

const QUELLEN = dateien(__dirname).map((path) => ({ name: path.slice(__dirname.length + 1), text: readFileSync(path, "utf8") }))
const ALLES = QUELLEN.map((quelle) => quelle.text).join("\n")

describe("Texte des Tasks-Moduls", () => {
  it("deutsch und englisch haben dieselben Schlüssel", () => {
    expect(Object.keys(en).sort()).toEqual(Object.keys(de).sort())
  })

  it("kein Text ist leer", () => {
    for (const [lang, texts] of [["de", de], ["en", en]] as const) {
      const leer = Object.entries(texts).filter(([, value]) => !value.trim()).map(([key]) => `${lang}:${key}`)
      expect(leer).toEqual([])
    }
  })

  it("Platzhalter stimmen in beiden Sprachen überein", () => {
    const holes = (text: string) => [...text.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort()
    const abweichend = Object.keys(de).filter((key) =>
      holes(de[key as keyof typeof de]).join() !== holes(en[key as keyof typeof en]).join())
    expect(abweichend).toEqual([])
  })

  it("kein Platzhalter heißt count (löst in i18next die Mehrzahl-Suche aus)", () => {
    expect(Object.entries(de).filter(([, value]) => value.includes("{{count}}")).map(([key]) => key)).toEqual([])
  })

  it("jeder Status und jede Priorität hat in beiden Sprachen eine Beschriftung", () => {
    for (const key of ["status_open", "status_in_progress", "status_done", "status_cancelled",
      "priority_high", "priority_medium", "priority_low"]) {
      expect(de).toHaveProperty(key)
      expect(en).toHaveProperty(key)
    }
  })

  it("englische Texte sind übersetzt, nicht kopiert", () => {
    const gleich = Object.keys(de).filter((key) => de[key as keyof typeof de] === en[key as keyof typeof en])
    expect(gleich).toEqual([])
  })

  it("jeder Schlüssel wird im Modul benutzt", () => {
    const dynamisch = (key: string) => /^(status|priority)_/.test(key)
    const unbenutzt = Object.keys(de).filter((key) =>
      key !== "title" && !dynamisch(key) && !ALLES.includes(`"${key}"`))
    expect(unbenutzt).toEqual([])
    expect(ALLES).toMatch(/`status_\$\{/)
    expect(ALLES).toMatch(/`priority_\$\{/)
  })

  it("in den Bausteinen steht kein fester deutscher Text mehr", () => {
    const werte = Object.values(de).map((value) => value.replace(/\{\{\w+\}\}/g, "").trim()).filter((value) => value.length >= 5)
    const funde = QUELLEN.flatMap(({ name, text }) =>
      werte.filter((value) => text.includes(`"${value}"`) || text.includes(`>${value}<`)).map((value) => `${name}: ${value}`))
    expect(funde).toEqual([])
    const umlaute = QUELLEN.flatMap(({ name, text }) =>
      text.split("\n").filter((line) => !/^\s*(\/\/|\*|\/\*)/.test(line) && !line.includes("{/*") && /[äöüÄÖÜß]/.test(line.replace(/\/\/.*$/, "")))
        .map((line) => `${name}: ${line.trim().slice(0, 80)}`))
    expect(umlaute).toEqual([])
  })
})

describe("Anmeldung im Kern", () => {
  it("liefert die Texte im Namensraum tasks, der Modulname bleibt", () => {
    expect(i18n.de.tasks).toBe(de)
    expect(i18n.en.tasks).toBe(en)
    expect(i18n.de.tasks.title).toBe("Aufgaben")
    expect(i18n.en.tasks.title).toBe("Tasks")
  })
})
