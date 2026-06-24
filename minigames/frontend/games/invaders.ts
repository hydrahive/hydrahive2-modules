// Space Invaders — Spieler unten (←/→ bewegen, Space schießt). Alien-Formation
// rückt seitlich vor, springt bei Randkontakt eine Reihe tiefer & dreht. Treffer
// = +10. Game-Over wenn Alien-Schuss trifft oder Aliens die Bodenlinie erreichen.
// Kapselt rAF + Keyboard; stop() räumt alles ab. Canvas 480×480.
import type { GameInstance, GameModule, GameMountOpts } from "../types"

const W = 480
const H = 480
const COLS = 8
const ROWS = 4
const A_W = 26       // Alien-Breite
const A_H = 18
const A_GAP = 22
const A_TOP = 50
const PLAYER_W = 36
const PLAYER_Y = H - 28
const FLOOR = H - 40  // erreichen Aliens das → Game Over

type Shot = { x: number; y: number; vy: number }

function mount(canvas: HTMLCanvasElement, opts: GameMountOpts): GameInstance {
  const ctx = canvas.getContext("2d")!
  let px = W / 2
  let aliens: { x: number; y: number; alive: boolean }[] = []
  let aDir = 1            // Formation-Richtung (1 rechts, -1 links)
  let aStep = 0.5        // horizontale Geschwindigkeit (steigt je weniger Aliens)
  let shots: Shot[] = []  // Spieler-Schüsse (vy<0)
  let bombs: Shot[] = []  // Alien-Schüsse (vy>0)
  let score = 0
  let alive = true
  let raf = 0
  const keys = new Set<string>()
  let fireCd = 0
  let bombCd = 60

  function reset() {
    px = W / 2
    aliens = []
    for (let r = 0; r < ROWS; r++)
      for (let c = 0; c < COLS; c++)
        aliens.push({ x: 40 + c * (A_W + A_GAP), y: A_TOP + r * (A_H + A_GAP), alive: true })
    aDir = 1; aStep = 0.5; shots = []; bombs = []; score = 0; alive = true
    fireCd = 0; bombCd = 60
    opts.onScore(0)
  }

  function livingAliens() { return aliens.filter((a) => a.alive) }

  function stepAliens() {
    const living = livingAliens()
    if (living.length === 0) { reset(); return }      // Welle geschafft → neue
    aStep = 0.5 + (ROWS * COLS - living.length) * 0.08 // schneller je weniger
    let hitEdge = false
    for (const a of living) {
      a.x += aDir * aStep
      if (a.x < 8 || a.x + A_W > W - 8) hitEdge = true
    }
    if (hitEdge) {
      aDir *= -1
      for (const a of living) a.y += 14
      if (living.some((a) => a.y + A_H >= FLOOR)) { alive = false; opts.onGameOver(score) }
    }
  }

  function update() {
    if (keys.has("ArrowLeft") || keys.has("a")) px = Math.max(PLAYER_W / 2, px - 5)
    if (keys.has("ArrowRight") || keys.has("d")) px = Math.min(W - PLAYER_W / 2, px + 5)
    if (fireCd > 0) fireCd--
    if ((keys.has(" ") || keys.has("ArrowUp")) && fireCd === 0) {
      shots.push({ x: px, y: PLAYER_Y - 10, vy: -7 }); fireCd = 18
    }

    stepAliens()

    // Alien-Bombe: zufälliger lebender Alien feuert
    if (--bombCd <= 0) {
      const living = livingAliens()
      if (living.length) {
        const a = living[(Math.random() * living.length) | 0]
        bombs.push({ x: a.x + A_W / 2, y: a.y + A_H, vy: 4 })
      }
      bombCd = 50 + (Math.random() * 60 | 0)
    }

    // Spieler-Schüsse bewegen + Treffer
    shots.forEach((s) => (s.y += s.vy))
    shots = shots.filter((s) => {
      if (s.y < 0) return false
      for (const a of aliens) {
        if (a.alive && s.x > a.x && s.x < a.x + A_W && s.y > a.y && s.y < a.y + A_H) {
          a.alive = false; score += 10; opts.onScore(score); return false
        }
      }
      return true
    })

    // Bomben bewegen + Spieler-Treffer
    bombs.forEach((b) => (b.y += b.vy))
    bombs = bombs.filter((b) => {
      if (b.y > H) return false
      if (b.y > PLAYER_Y - 8 && Math.abs(b.x - px) < PLAYER_W / 2) {
        alive = false; opts.onGameOver(score); return false
      }
      return true
    })
  }

  function draw() {
    ctx.fillStyle = "#0a0a0b"; ctx.fillRect(0, 0, W, H)
    // Aliens
    ctx.fillStyle = "#a78bfa"
    for (const a of aliens) if (a.alive) ctx.fillRect(a.x, a.y, A_W, A_H)
    // Spieler
    ctx.fillStyle = "#34d399"
    ctx.fillRect(px - PLAYER_W / 2, PLAYER_Y, PLAYER_W, 10)
    ctx.fillRect(px - 3, PLAYER_Y - 8, 6, 8)
    // Schüsse
    ctx.fillStyle = "#6ee7b7"
    for (const s of shots) ctx.fillRect(s.x - 1, s.y, 3, 10)
    ctx.fillStyle = "#f43f5e"
    for (const b of bombs) ctx.fillRect(b.x - 1, b.y, 3, 10)
  }

  function loop() {
    raf = requestAnimationFrame(loop)
    if (alive) update()
    draw()
  }

  function onKey(e: KeyboardEvent) {
    if ([" ", "ArrowLeft", "ArrowRight", "ArrowUp"].includes(e.key)) e.preventDefault()
    if ((e.key === " " || e.key === "Enter") && !alive) { reset(); return }
    keys.add(e.key)
  }
  function onKeyUp(e: KeyboardEvent) { keys.delete(e.key) }

  return {
    start() {
      reset()
      window.addEventListener("keydown", onKey)
      window.addEventListener("keyup", onKeyUp)
      raf = requestAnimationFrame(loop)
    },
    stop() {
      cancelAnimationFrame(raf)
      window.removeEventListener("keydown", onKey)
      window.removeEventListener("keyup", onKeyUp)
    },
  }
}

export const invaders: GameModule = {
  meta: { id: "invaders", titleKey: "mg_game_invaders", icon: "Rocket", accent: "167 139 250" },
  mount,
}
