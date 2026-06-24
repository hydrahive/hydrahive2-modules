// Frogger — Frosch (Pfeile/WASD) von unten nach oben: erst Straße (Autos =
// tödlich bei Kollision), dann Fluss (nur auf Baumstämmen überleben, Wasser =
// ertrinken), oben die Zielzone. +10 je Aufwärtsfeld, +50 je erreichtes Ziel.
// Raster 13×13 (Zelle 480/13≈36,9). Kapselt rAF + Keyboard; stop() räumt auf.
import type { GameInstance, GameModule, GameMountOpts } from "../types"

const SIZE = 480
const ROWS = 13
const CELL = SIZE / ROWS
// Zeilen (0 = oben): 0 Ziel, 1-5 Fluss, 6 Mittelinsel, 7-11 Straße, 12 Start
const RIVER = [1, 2, 3, 4, 5]
const ROAD = [7, 8, 9, 10, 11]

type Lane = { row: number; speed: number; len: number; gap: number; offset: number }

function makeLanes(): Lane[] {
  // speed in px/frame; len/gap in Zellen; offset Startversatz
  const cfg: [number, number, number, number][] = [
    [1, 1.4, 2, 4], [2, -1.0, 3, 5], [3, 1.8, 2, 3], [4, -1.3, 2, 4], [5, 1.1, 3, 5], // Fluss-Logs
    [7, -1.6, 1, 4], [8, 1.2, 1, 3], [9, -2.0, 1, 5], [10, 1.5, 2, 4], [11, -1.1, 1, 3], // Autos
  ]
  return cfg.map(([row, speed, len, gap], i) => ({
    row, speed, len, gap, offset: (i * 90) % SIZE,
  }))
}

function mount(canvas: HTMLCanvasElement, opts: GameMountOpts): GameInstance {
  const ctx = canvas.getContext("2d")!
  let fx = 6, fy = 12       // Frosch-Zelle
  let maxRowReached = 12
  let score = 0
  let alive = true
  let raf = 0
  let lanes = makeLanes()
  let carry = 0             // horizontale Mitnahme auf Logs (px)

  function reset() {
    fx = 6; fy = 12; maxRowReached = 12; score = 0; alive = true
    lanes = makeLanes(); carry = 0
    opts.onScore(0)
  }

  // Belegte Segmente einer Lane als [startPx, endPx]-Liste (mit Wrap)
  function segments(l: Lane, t: number): [number, number][] {
    const period = (l.len + l.gap) * CELL
    const base = ((l.offset + t * l.speed) % period + period) % period
    const out: [number, number][] = []
    for (let x = base - period; x < SIZE + period; x += period)
      out.push([x, x + l.len * CELL])
    return out
  }

  let frame = 0
  function update() {
    frame++
    const froggerX = fx * CELL + CELL / 2

    // Fluss: auf Log mitschwimmen, sonst ertrinken
    if (RIVER.includes(fy)) {
      const lane = lanes.find((l) => l.row === fy)!
      const onLog = segments(lane, frame).some(([a, b]) => froggerX >= a && froggerX <= b)
      if (onLog) {
        carry += lane.speed
        while (carry >= CELL) { fx++; carry -= CELL }
        while (carry <= -CELL) { fx--; carry += CELL }
        if (fx < 0 || fx >= ROWS) { alive = false; opts.onGameOver(score); return }
      } else {
        alive = false; opts.onGameOver(score); return   // ertrunken
      }
    } else {
      carry = 0
    }

    // Straße: Auto-Kollision
    if (ROAD.includes(fy)) {
      const lane = lanes.find((l) => l.row === fy)!
      const hit = segments(lane, frame).some(([a, b]) => froggerX + 8 > a && froggerX - 8 < b)
      if (hit) { alive = false; opts.onGameOver(score); return }
    }

    // Ziel erreicht (oberste Zeile)
    if (fy === 0) {
      score += 50; opts.onScore(score)
      fx = 6; fy = 12; maxRowReached = 12; carry = 0
    }
  }

  function draw() {
    // Hintergrund-Zonen
    ctx.fillStyle = "#1e293b"; ctx.fillRect(0, 0, SIZE, SIZE)         // Start/Insel
    ctx.fillStyle = "#0c4a6e"; ctx.fillRect(0, CELL, SIZE, 5 * CELL)  // Fluss
    ctx.fillStyle = "#3f3f46"; ctx.fillRect(0, 7 * CELL, SIZE, 5 * CELL) // Straße
    ctx.fillStyle = "#166534"; ctx.fillRect(0, 0, SIZE, CELL)          // Ziel
    ctx.fillStyle = "#166534"; ctx.fillRect(0, 6 * CELL, SIZE, CELL)   // Mittelinsel

    for (const l of lanes) {
      const y = l.row * CELL
      ctx.fillStyle = RIVER.includes(l.row) ? "#a16207" : "#dc2626"   // Log braun / Auto rot
      for (const [a, b] of segments(l, frame)) {
        ctx.fillRect(a, y + 4, b - a, CELL - 8)
      }
    }

    // Frosch
    ctx.fillStyle = alive ? "#4ade80" : "#71717a"
    ctx.fillRect(fx * CELL + 5, fy * CELL + 5, CELL - 10, CELL - 10)
  }

  function loop() {
    raf = requestAnimationFrame(loop)
    if (alive) update()
    draw()
  }

  function move(dx: number, dy: number) {
    fx = Math.max(0, Math.min(ROWS - 1, fx + dx))
    fy = Math.max(0, Math.min(ROWS - 1, fy + dy))
    if (fy < maxRowReached) { maxRowReached = fy; score += 10; opts.onScore(score) }
  }

  function onKey(e: KeyboardEvent) {
    const k = e.key
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", " "].includes(k)) e.preventDefault()
    if (!alive) {
      if (k === " " || k === "Enter") reset()
      return
    }
    if (k === "ArrowUp" || k === "w") move(0, -1)
    else if (k === "ArrowDown" || k === "s") move(0, 1)
    else if (k === "ArrowLeft" || k === "a") move(-1, 0)
    else if (k === "ArrowRight" || k === "d") move(1, 0)
  }

  return {
    start() { reset(); window.addEventListener("keydown", onKey); raf = requestAnimationFrame(loop) },
    stop() { cancelAnimationFrame(raf); window.removeEventListener("keydown", onKey) },
  }
}

export const frogger: GameModule = {
  meta: { id: "frogger", titleKey: "mg_game_frogger", icon: "Squirrel", accent: "74 222 128" },
  mount,
}
