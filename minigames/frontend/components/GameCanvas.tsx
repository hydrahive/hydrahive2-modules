import { useEffect, useRef } from "react"
import type { GameInstance, GameModule } from "../types"

interface Props {
  game: GameModule
  size?: number
  onScore: (score: number) => void
  onGameOver: (finalScore: number) => void
}

/** Mountet ein GameModule auf ein Canvas und baut es beim Unmount sauber ab. */
export function GameCanvas({ game, size = 480, onScore, onGameOver }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  // Callbacks in Refs halten → Spiel wird nicht bei jedem Render neu gemountet.
  const scoreRef = useRef(onScore)
  const overRef = useRef(onGameOver)
  scoreRef.current = onScore
  overRef.current = onGameOver

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    let inst: GameInstance | null = game.mount(canvas, {
      onScore: (s) => scoreRef.current(s),
      onGameOver: (s) => overRef.current(s),
    })
    inst.start()
    return () => {
      inst?.stop()
      inst = null
    }
  }, [game])

  return (
    <canvas
      ref={canvasRef}
      width={size}
      height={size}
      className="rounded-lg border border-white/[8%] bg-zinc-950 max-w-full touch-none"
      style={{ imageRendering: "pixelated" }}
    />
  )
}
