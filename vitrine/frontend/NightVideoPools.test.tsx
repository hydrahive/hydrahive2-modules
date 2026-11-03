import { renderToStaticMarkup } from "react-dom/server"
import { describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({ useTranslation: () => ({ t: (k: string) => k }) }))

const { NightVideoPools, toggleNightVideo } = await import("./NightVideoPools")

const pools = {
  spring: ["fruehling.mp4"],
  summer: [],
  autumn: [],
  winter: ["winter.mp4"],
}
const videos = [
  { name: "fruehling.mp4", size: 1, modified: 1 },
  { name: "winter.mp4", size: 1, modified: 1 },
]

describe("Nachtvideo-Pools", () => {
  it("zeigt alle vier Jahreszeiten und hochgeladene Videos", () => {
    const html = renderToStaticMarkup(<NightVideoPools pools={pools} videos={videos} onChange={() => undefined} />)
    for (const season of ["spring", "summer", "autumn", "winter"]) {
      expect(html).toContain(`season.${season}`)
    }
    expect(html).toContain("fruehling.mp4")
    expect(html).toContain("winter.mp4")
    expect(html.match(/checked=""/g)).toHaveLength(2)
  })

  it("ordnet ein Video nur im gewählten Saison-Pool zu", () => {
    const next = toggleNightVideo(pools, "summer", "winter.mp4")
    expect(next.summer).toEqual(["winter.mp4"])
    expect(next.winter).toEqual(["winter.mp4"])
    expect(pools.summer).toEqual([])
  })
})
