// Schmale Fenster: Der Chat darf der Zeichenfläche nicht den Platz nehmen.
// Im Browser gemessen (12.11.2026, Chat 420 px breit): Fenster 1200 px → 348 px Zeichenfläche,
// 1024 → 172, 900 → 63, 760 → 0.
import { describe, expect, it } from "vitest"
import { BOARD_MIN, DOCK_MIN, dockLayout } from "./dock"
import { SIDE_PANEL, SIDE_PANEL_WIDTH } from "./styles"

describe("Chat neben dem Board: Platz für die Zeichenfläche", () => {
  it("steht neben dem Board in der gewünschten Breite, wenn der Platz reicht", () => {
    expect(dockLayout(420, 1244)).toEqual({ over: false, width: 420 })
  })

  it("gibt nach, damit Palette und Zeichenfläche ihr Mindestmaß behalten", () => {
    expect(dockLayout(600, 944)).toEqual({ over: false, width: 944 - BOARD_MIN })
    expect(dockLayout(420, BOARD_MIN + DOCK_MIN)).toEqual({ over: false, width: DOCK_MIN })
  })

  it("liegt über dem Board, sobald daneben kein Platz für beide ist, und nimmt dann die ganze Breite", () => {
    expect(dockLayout(420, BOARD_MIN + DOCK_MIN - 1)).toEqual({ over: true, width: BOARD_MIN + DOCK_MIN - 1 })
    expect(dockLayout(420, 520)).toEqual({ over: true, width: 520 })
  })

  it("nimmt vor der ersten Messung die gewünschte Breite neben dem Board", () => {
    expect(dockLayout(512, null)).toEqual({ over: false, width: 512 })
  })

  it("gibt für die rechte Spalte weiter nach, aber nie unter sein Mindestmaß", () => {
    expect(dockLayout(600, 1244, SIDE_PANEL_WIDTH)).toEqual({ over: false, width: 1244 - BOARD_MIN - SIDE_PANEL_WIDTH })
    expect(dockLayout(420, 944, SIDE_PANEL_WIDTH)).toEqual({ over: false, width: DOCK_MIN })
  })

  it("springt nicht über das Board, nur weil ein Baustein gewählt wird", () => {
    expect(dockLayout(420, BOARD_MIN + DOCK_MIN, SIDE_PANEL_WIDTH).over).toBe(false)
    expect(dockLayout(420, BOARD_MIN + DOCK_MIN - 1, SIDE_PANEL_WIDTH).over).toBe(true)
  })

  it("rechnet mit den Breiten, die Palette und rechte Spalte wirklich haben", () => {
    expect(SIDE_PANEL).toContain(`w-${SIDE_PANEL_WIDTH / 4} `)
    expect(BOARD_MIN).toBeGreaterThanOrEqual(176 + 300)  // Palette w-44 = 176 px, dazu mindestens 300 px Fläche
  })
})
