import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { boardgamesApi } from "../api"
import type { BoardGameProps, GameMode, LlmModel } from "../types"
import { GLYPHS, fileOf, rankOf } from "./engine_types"
import { useChessGame } from "./useChessGame"

const LIGHT = "#b9c4d0"
const DARK = "#6b7c8f"

/** Schach: Modus-Wahl (Hotseat / vs KI / vs LLM), dann klickbares 8×8-Brett. */
export function ChessGame(_: BoardGameProps) {
  const { t } = useTranslation("boardgames")
  const [mode, setMode] = useState<GameMode | null>(null)
  const [model, setModel] = useState<string>("")
  const [pickModel, setPickModel] = useState(false)

  if (pickModel) {
    return <ModelPicker onPick={(m) => { setModel(m); setMode("llm"); setPickModel(false) }}
      onBack={() => setPickModel(false)} />
  }

  if (!mode) {
    return (
      <div className="flex flex-col items-center gap-4 p-6">
        <h3 className="text-base font-semibold text-zinc-200">{t("bg_choose_mode")}</h3>
        <div className="flex flex-col gap-2 w-56">
          <ModeButton emoji="👥" label={t("bg_mode_hotseat")} onClick={() => setMode("hotseat")} />
          <ModeButton emoji="🤖" label={t("bg_mode_ai")} onClick={() => setMode("ai")} />
          <ModeButton emoji="🧠" label={t("bg_mode_llm")} onClick={() => setPickModel(true)} />
        </div>
      </div>
    )
  }

  return <ChessBoard mode={mode} model={model} onBack={() => { setMode(null); setModel("") }} />
}

function ModeButton({ emoji, label, onClick }: { emoji: string; label: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="px-4 py-3 rounded-lg border border-white/10 bg-white/[4%] text-zinc-200 hover:bg-white/[8%] transition-colors">
      {emoji} {label}
    </button>
  )
}

/** Lädt die Chat-Modelle aus dem Katalog und lässt den Gegner wählen. */
function ModelPicker({ onPick, onBack }: { onPick: (model: string) => void; onBack: () => void }) {
  const { t } = useTranslation("boardgames")
  const [models, setModels] = useState<LlmModel[]>([])
  const [sel, setSel] = useState("")
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState(false)

  useEffect(() => {
    let alive = true
    boardgamesApi.listModels()
      .then((res) => { if (!alive) return; setModels(res.models); setSel(res.default || res.models[0]?.id || "") })
      .catch(() => { if (alive) setErr(true) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [])

  return (
    <div className="flex flex-col items-center gap-4 p-6 w-72">
      <h3 className="text-base font-semibold text-zinc-200">{t("bg_pick_model")}</h3>
      {loading && <p className="text-sm text-zinc-400">{t("bg_loading")}</p>}
      {err && <p className="text-sm text-red-400">{t("bg_models_error")}</p>}
      {!loading && !err && (
        <>
          <select value={sel} onChange={(e) => setSel(e.target.value)}
            className="w-full px-3 py-2 rounded-lg bg-zinc-800 border border-white/10 text-sm text-zinc-200">
            {models.map((m) => (
              <option key={m.id} value={m.id}>{m.label}{m.is_free ? " · free" : ""}</option>
            ))}
          </select>
          <button onClick={() => sel && onPick(sel)} disabled={!sel}
            className="w-full px-4 py-2.5 rounded-lg bg-blue-600 text-sm text-white hover:bg-blue-500 disabled:opacity-40">
            {t("bg_start")}
          </button>
        </>
      )}
      <button onClick={onBack} className="text-xs text-zinc-400 hover:text-zinc-200">← {t("bg_back")}</button>
    </div>
  )
}

function ChessBoard({ mode, model, onBack }: { mode: GameMode; model: string; onBack: () => void }) {
  const { t } = useTranslation("boardgames")
  const g = useChessGame(mode, model)

  let status: string
  if (g.status === "checkmate") status = g.winner === 1 ? t("bg_white_wins") : t("bg_black_wins")
  else if (g.status === "stalemate") status = t("bg_stalemate")
  else if (g.thinking) status = `${mode === "llm" ? "🧠" : "🤖"} ${t("bg_ai_thinking")}`
  else status = g.turn === 1 ? t("bg_white_turn") : t("bg_black_turn")

  return (
    <div className="flex flex-col items-center gap-3 p-4">
      <div className="flex items-center gap-3 w-full max-w-[480px]">
        <span className="text-sm font-medium text-zinc-200">{status}</span>
        <div className="ml-auto flex gap-2">
          <button onClick={g.reset}
            className="px-3 py-1.5 rounded-lg bg-white/[5%] text-xs text-zinc-300 hover:bg-white/[9%]">{t("bg_new_game")}</button>
          <button onClick={onBack}
            className="px-3 py-1.5 rounded-lg bg-white/[5%] text-xs text-zinc-400 hover:bg-white/[9%]">{t("bg_mode")}</button>
        </div>
      </div>

      <div className="grid grid-cols-8 rounded-lg overflow-hidden border border-white/10 shadow-lg select-none"
        style={{ width: "min(480px, 90vw)", height: "min(480px, 90vw)" }}>
        {Array.from({ length: 64 }, (_, sq) => {
          const dark = (fileOf(sq) + rankOf(sq)) % 2 === 1
          const piece = g.board[sq]
          const isSel = g.selected === sq
          const isTarget = g.legalTargets.includes(sq)
          const isLast = g.lastMove && (g.lastMove.from === sq || g.lastMove.to === sq)
          return (
            <button
              key={sq}
              onClick={() => g.onSquare(sq)}
              className="relative flex items-center justify-center"
              style={{
                background: isSel ? "#3b82f6" : isLast ? "#ca8a0455" : dark ? DARK : LIGHT,
                aspectRatio: "1",
              }}
            >
              <span className="text-[min(7vw,34px)] leading-none" style={{ color: piece > 0 ? "#fafafa" : "#18181b" }}>
                {GLYPHS[piece]}
              </span>
              {isTarget && (
                <span className="absolute w-3 h-3 rounded-full"
                  style={{ background: piece !== 0 ? "transparent" : "#22c55eaa", boxShadow: piece !== 0 ? "inset 0 0 0 3px #ef4444aa" : "none", width: piece !== 0 ? "100%" : undefined, height: piece !== 0 ? "100%" : undefined }} />
              )}
            </button>
          )
        })}
      </div>
      {mode === "ai" && <p className="text-[11px] text-zinc-500">{t("bg_ai_hint")}</p>}
      {mode === "llm" && (
        <p className="text-[11px] text-zinc-500">
          🧠 {model}{g.moveSource === "fallback" ? ` · ${t("bg_llm_fallback")}` : ""}
        </p>
      )}
    </div>
  )
}
