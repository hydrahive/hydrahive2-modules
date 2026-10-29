// Task 0dda5420: Die großen Atelier-Bereiche zeigen im Leer-Zustand das eigene Hydra-Bild des Moduls.
import { readFileSync } from "node:fs"
import { join } from "node:path"
import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it } from "vitest"
import { AtelierEmpty } from "./AtelierEmpty"

describe("AtelierEmpty", () => {
  it("Bild als Deko + Text", () => {
    const html = renderToStaticMarkup(<AtelierEmpty text="Noch keine Bilder." />)
    expect(html).toMatch(/<img[^>]*src="[^"]*leer[^"]*\.webp"[^>]*alt=""/)
    expect(html).toContain("Noch keine Bilder.")
  })
  it.each([
    ["ImageGalleryPanel.tsx", "gallery_empty"], ["ClipLibraryPanel.tsx", "video_empty"], ["FilmComposerPanel.tsx", "film_empty"],
    ["DirectorPanel.tsx", "scenes_empty"], ["AtelierCutPanel.tsx", "cut_empty"], ["AudioLibrary.tsx", "audio_library_empty"],
  ])("%s zeigt %s über AtelierEmpty", (file, key) => {
    const src = readFileSync(join(__dirname, file), "utf8")
    expect(src).toContain(`<AtelierEmpty text={t("${key}")} />`)
  })
  it("das Bild liegt im Modul", () => {
    expect(readFileSync(join(__dirname, "assets", "leer.webp")).length).toBeGreaterThan(1000)
  })
})
