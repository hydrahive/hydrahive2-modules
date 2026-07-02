import type { Clip } from "./types"

interface Player {
  playhead: number
  stepFrame: (dir: number) => void
  jumpPrevKeyframe: () => void
  jumpNextKeyframe: () => void
}
interface Edl {
  snapOn: boolean
  toggleSnap: () => void
  toggleMode: (id: string) => void
  undo: () => void
  redo: () => void
  isOnKeyframe: (t: number) => boolean
}
interface Preview {
  isPreviewing: boolean
  playClip: (c: Clip) => void
  playTimeline: (cs: Clip[]) => void
  stop: () => void
}

interface Props {
  player: Player
  edl: Edl
  preview: Preview
  inPoint: number | null
  selected: Clip | undefined
  clips: Clip[]
  selectedClipId: string | null
  onMarkIn: () => void
  onMarkOut: () => void
  onSplit: () => void
  onDelete: () => void
}

const btn = "px-2 py-1 rounded border border-white/10 hover:bg-white/5 disabled:opacity-40"

export function EditorToolbar(p: Props) {
  const { player, edl, preview, inPoint, selected, clips } = p
  const onKf = edl.isOnKeyframe(player.playhead)

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs text-zinc-400">
      {/* Snap-Toggle */}
      <button onClick={edl.toggleSnap}
        className={`${btn} ${edl.snapOn ? "bg-emerald-500/15 border-emerald-500/40 text-emerald-200" : ""}`}
        title="Keyframe-Magnet: Schnitte rasten auf Keyframes ein → verlustfrei kopierbar">
        🧲 Snap {edl.snapOn ? "an" : "aus"}
      </button>
      <span className={`text-[10px] ${onKf ? "text-emerald-400" : "text-zinc-600"}`}>
        {onKf ? "● auf Keyframe" : "○ zwischen Keyframes"}
      </span>

      <span className="w-px h-4 bg-white/10" />

      {/* Schnitt */}
      <button onClick={p.onMarkIn} className={btn}>In (I)</button>
      <button onClick={p.onMarkOut} disabled={inPoint === null} className={btn}>Out (O)</button>
      <button onClick={p.onSplit} className={btn}>Split (S)</button>
      <button onClick={p.onDelete} disabled={!p.selectedClipId} className={btn}>Löschen</button>
      {inPoint !== null && <span className="text-amber-300">In @ {inPoint.toFixed(2)}s</span>}

      <span className="w-px h-4 bg-white/10" />

      {/* Undo/Redo */}
      <button onClick={edl.undo} className={btn} title="Rückgängig (Strg+Z)">↩︎</button>
      <button onClick={edl.redo} className={btn} title="Wiederholen (Strg+Shift+Z)">↪︎</button>

      <span className="w-px h-4 bg-white/10" />

      {/* Player-Präzision */}
      <button onClick={() => player.jumpPrevKeyframe()} className={btn} title="Vorheriger Keyframe ([)">⇤kf</button>
      <button onClick={() => player.stepFrame(-1)} className={btn} title="1 Bild zurück (←)">◀|</button>
      <button onClick={() => player.stepFrame(1)} className={btn} title="1 Bild vor (→)">|▶</button>
      <button onClick={() => player.jumpNextKeyframe()} className={btn} title="Nächster Keyframe (])">kf⇥</button>

      <span className="w-px h-4 bg-white/10" />

      {/* Vorschau ohne Rendern */}
      {preview.isPreviewing ? (
        <button onClick={preview.stop} className={`${btn} bg-pink-500/15 border-pink-500/40 text-pink-200`}>■ Stop</button>
      ) : (
        <>
          <button onClick={() => selected && preview.playClip(selected)} disabled={!selected} className={btn}
            title="Ausgewählten Clip abspielen">▶ Clip</button>
          <button onClick={() => preview.playTimeline(clips)} disabled={clips.length === 0} className={btn}
            title="Ganzen Schnitt abspielen (ohne Rendern)">▶▶ Schnitt</button>
        </>
      )}

      {selected && (
        <button onClick={() => edl.toggleMode(selected.id)} className={btn}>
          {selected.mode === "copy" ? "⚡ Kopieren" : "⟳ Neu kodieren"}
        </button>
      )}

      <span className="flex-1" />
      <span>{player.playhead.toFixed(2)}s · {clips.length} Clip(s)</span>
    </div>
  )
}
