// Snake — klassisch. Raster 24×24, Schlange wächst beim Fressen, kein 180°-Turn.
// Score = gefressene Häppchen × 10. Game-Over bei Wand-/Selbstkollision.
// Kapselt requestAnimationFrame + Keyboard-Listener; stop() räumt alles ab.
import type { GameInstance, GameModule, GameMountOpts } from "../types"

const GRID = 24
const STEP_MS = 110 // Tick-Intervall (Tempo)
const BG = "#0a0a0b"
const SNAKE = "#34d399"
const HEAD = "#6ee7b7"
const FOOD = "#f43f5e"

type Pt = { x: number; y: number }
type Dir = { x: number; y: number }

const DIRS: Record<string, Dir> = {
  ArrowUp: { x: 0, y: -1 }, ArrowDown: { x: 0, y: 1 },
  ArrowLeft: { x: -1, y: 0 }, ArrowRight: { x: 1, y: 0 },
  w: { x: 0, y: -1 }, s: { x: 0, y: 1 }, a: { x: -1, y: 0 }, d: { x: 1, y: 0 },
}

function mount(canvas: HTMLCanvasElement, opts: GameMountOpts): GameInstance {
  const ctx = canvas.getContext("2d")!
  let snake: Pt[] = []
  let dir: Dir = { x: 1, y: 0 }
  let pending: Dir = dir
  let food: Pt = { x: 0, y: 0 }
  let score = 0
  let alive = true
  let acc = 0
  let last = 0
  let raf = 0

  function randFood() {
    do {
      food = { x: (Math.random() * GRID) | 0, y: (Math.random() * GRID) | 0 }
    } while (snake.some((s) => s.x === food.x && s.y === food.y))
  }

  function reset() {
    snake = [{ x: 8, y: 12 }, { x: 7, y: 12 }, { x: 6, y: 12 }]
    dir = { x: 1, y: 0 }
    pending = dir
    score = 0
    alive = true
    acc = 0
    randFood()
    opts.onScore(0)
  }

  function step() {
    // 180°-Turn verhindern
    if (pending.x !== -dir.x || pending.y !== -dir.y) dir = pending
    const head = { x: snake[0].x + dir.x, y: snake[0].y + dir.y }

    const hitWall = head.x < 0 || head.y < 0 || head.x >= GRID || head.y >= GRID
    const hitSelf = snake.some((s) => s.x === head.x && s.y === head.y)
    if (hitWall || hitSelf) {
      alive = false
      opts.onGameOver(score)
      return
    }

    snake.unshift(head)
    if (head.x === food.x && head.y === food.y) {
      score += 10
      opts.onScore(score)
      randFood()
    } else {
      snake.pop()
    }
  }

  function draw() {
    const cell = canvas.width / GRID
    ctx.fillStyle = BG
    ctx.fillRect(0, 0, canvas.width, canvas.height)
    // Food
    ctx.fillStyle = FOOD
    ctx.fillRect(food.x * cell + 1, food.y * cell + 1, cell - 2, cell - 2)
    // Snake
    snake.forEach((s, i) => {
      ctx.fillStyle = i === 0 ? HEAD : SNAKE
      ctx.fillRect(s.x * cell + 1, s.y * cell + 1, cell - 2, cell - 2)
    })
  }

  function loop(t: number) {
    raf = requestAnimationFrame(loop)
    if (!last) last = t
    acc += t - last
    last = t
    if (alive && acc >= STEP_MS) {
      acc = 0
      step()
    }
    draw()
  }

  function onKey(e: KeyboardEvent) {
    const d = DIRS[e.key]
    if (d) {
      pending = d
      e.preventDefault()
    } else if ((e.key === " " || e.key === "Enter") && !alive) {
      reset()
    }
  }

  return {
    start() {
      reset()
      window.addEventListener("keydown", onKey)
      last = 0
      raf = requestAnimationFrame(loop)
    },
    stop() {
      cancelAnimationFrame(raf)
      window.removeEventListener("keydown", onKey)
    },
  }
}

export const snake: GameModule = {
  meta: { id: "snake", titleKey: "mg_game_snake", icon: "Worm", accent: "52 211 153" },
  mount,
}
