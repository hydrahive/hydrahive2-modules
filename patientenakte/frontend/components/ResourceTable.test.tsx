// Task 0dda5420: Die Akte bringt ihr eigenes Leer-Bild (bunte Hydra) mit statt des alten Kernbilds.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))
import { ResourceTable } from "./ResourceTable"

describe("ResourceTable leer", () => {
  it("zeigt das eigene Leer-Bild des Moduls, nicht das alte Kernbild", () => {
    const html = renderToStaticMarkup(<ResourceTable rows={[]} columns={[]} />)
    expect(html).not.toContain("/illustrations/empty-akte.png")
    expect(html).toMatch(/<img[^>]*src="[^"]*leer[^"]*\.webp"/)
    expect(html).toContain("akte.no_entries")
  })
  it("das Bild liegt im Modul", () => {
    expect(readFileSync(join(__dirname, "..", "assets", "leer.webp")).length).toBeGreaterThan(1000)
  })
})
