import type { AudioClip } from "./types"

interface Props {
  clip: AudioClip
  onGain: (db: number) => void
  onFade: (fade: { fadeIn?: number; fadeOut?: number }) => void
  onSplit: () => void
  onRemove: () => void
  onClose?: () => void
}

const btn = "px-2 py-1 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] disabled:opacity-40"

function shortName(rel: string): string {
  const name = rel.split("/").pop() || rel
  return name.length > 32 ? "…" + name.slice(-31) : name
}

/** Kompaktes Inspector-Panel für einen ausgewählten Audio-Clip —
 *  Gain, Fades, Split/Löschen. Schmale Card unter der Timeline. */
export function AudioClipInspector(p: Props) {
  const { clip } = p
  const duration = (clip.src_end - clip.src_start).toFixed(2)

  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] px-3 py-2 text-xs text-[#c8d2df]">
      {/* Titel + Dauer */}
      <div className="min-w-0 flex-shrink-0">
        <p className="text-[#e8eef8] truncate max-w-[220px]" title={clip.source_rel}>
          {shortName(clip.source_rel)}
        </p>
        <p className="text-[10px] text-[#9aa7bc]">{duration}s</p>
      </div>

      {/* Gain */}
      <label className="flex items-center gap-2">
        <span className="text-[11px] text-[#9aa7bc]">Gain</span>
        <input
          type="range" min={-30} max={12} step={0.5} value={clip.gain_db}
          onChange={(e) => p.onGain(Number(e.target.value))}
          className="w-32 accent-emerald-500"
        />
        <span className="w-12 tabular-nums text-emerald-200">
          {clip.gain_db.toFixed(1)} dB
        </span>
      </label>

      {/* Fade-In */}
      <label className="flex items-center gap-1.5">
        <span className="text-[11px] text-[#9aa7bc]">Fade-In</span>
        <input
          type="number" min={0} step={0.1} value={clip.fade_in}
          onChange={(e) => p.onFade({ fadeIn: Math.max(0, Number(e.target.value)) })}
          className="w-16 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-black/30 px-1.5 py-0.5 text-[#e8eef8]"
        />
        <span className="text-[11px] text-[#9aa7bc]">s</span>
      </label>

      {/* Fade-Out */}
      <label className="flex items-center gap-1.5">
        <span className="text-[11px] text-[#9aa7bc]">Fade-Out</span>
        <input
          type="number" min={0} step={0.1} value={clip.fade_out}
          onChange={(e) => p.onFade({ fadeOut: Math.max(0, Number(e.target.value)) })}
          className="w-16 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-black/30 px-1.5 py-0.5 text-[#e8eef8]"
        />
        <span className="text-[11px] text-[#9aa7bc]">s</span>
      </label>

      {/* Aktionen */}
      <div className="ml-auto flex items-center gap-2">
        <button onClick={p.onSplit} className={btn}>Split am Playhead</button>
        <button onClick={p.onRemove}
          className={`${btn} border-red-500/30 text-red-300 hover:bg-red-500/10`}>
          Löschen
        </button>
        {p.onClose && (
          <button onClick={p.onClose} className="text-[#9aa7bc] hover:text-[#e8eef8]">✕</button>
        )}
      </div>
    </div>
  )
}
