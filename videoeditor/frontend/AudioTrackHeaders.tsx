import { useState } from "react"
import type { AudioTrack, OriginalAudio } from "./types"
import { AUDIO_ROW_H } from "./_audioDraw"

interface Ops {
  renameTrack: (trackId: string, name: string) => void
  removeTrack: (trackId: string) => void
  setTrackFlag: (trackId: string, flags: { mute?: boolean; solo?: boolean }) => void
  setTrackGain: (trackId: string, db: number) => void
  addTrack: () => void
  setOriginalAudio: (patch: { mute?: boolean; gain_db?: number }) => void
}

interface Props {
  originalAudio: OriginalAudio
  tracks: AudioTrack[]
  ops: Ops
  hasVideoAudio: boolean
}

export const HEADER_W = 140

const iconBtn = "px-1.5 py-0.5 text-[10px] rounded border transition-colors"
const rowStyle = { height: AUDIO_ROW_H } as const

function GainSlider({ value, onChange }: { value: number; onChange: (db: number) => void }) {
  return (
    <label className="flex items-center gap-1">
      <input type="range" min={-30} max={12} step={0.5} value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-14 accent-emerald-500" />
      <span className="w-9 tabular-nums text-[9px] text-emerald-200">{value.toFixed(0)}dB</span>
    </label>
  )
}

/** Header-Spalte links neben dem Audio-Canvas. Erste Zeile = O-Ton,
 *  darunter je Track eine Zeile (gleiche AUDIO_ROW_H wie Canvas). */
export function AudioTrackHeaders({ originalAudio, tracks, ops, hasVideoAudio }: Props) {
  const [editing, setEditing] = useState<string | null>(null)

  return (
    <div className="flex-shrink-0 select-none" style={{ width: HEADER_W }}>
      {/* O-Ton-Zeile */}
      <div className="flex flex-col justify-center gap-1 px-2 border-b border-white/10"
        style={rowStyle}>
        <div className="flex items-center gap-1">
          <span className="text-[11px] text-zinc-300 truncate flex-1">Original-Ton</span>
          <button
            onClick={() => ops.setOriginalAudio({ mute: !originalAudio.mute })}
            disabled={!hasVideoAudio}
            title={hasVideoAudio ? "Original-Ton stumm" : "Video ohne Ton"}
            className={`${iconBtn} ${originalAudio.mute ? "border-red-500/40 text-red-300 bg-red-500/10" : "border-white/10 text-zinc-400"} disabled:opacity-30`}>
            M
          </button>
        </div>
        <GainSlider value={originalAudio.gain_db} onChange={(db) => ops.setOriginalAudio({ gain_db: db })} />
      </div>

      {/* Track-Zeilen */}
      {tracks.map((t) => (
        <div key={t.id} className="flex flex-col justify-center gap-1 px-2 border-b border-white/10" style={rowStyle}>
          <div className="flex items-center gap-1">
            {editing === t.id ? (
              <input autoFocus defaultValue={t.name}
                onBlur={(e) => { ops.renameTrack(t.id, e.target.value.trim() || t.name); setEditing(null) }}
                onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur() }}
                className="min-w-0 flex-1 rounded border border-white/10 bg-black/40 px-1 py-0.5 text-[11px] text-zinc-100" />
            ) : (
              <span className="text-[11px] text-zinc-300 truncate flex-1 cursor-text"
                title={t.name} onDoubleClick={() => setEditing(t.id)}>{t.name}</span>
            )}
            <button onClick={() => ops.removeTrack(t.id)} title="Spur löschen"
              className={`${iconBtn} border-white/10 text-zinc-500 hover:text-red-300 hover:border-red-500/40`}>✕</button>
          </div>
          <div className="flex items-center gap-1">
            <button onClick={() => ops.setTrackFlag(t.id, { mute: !t.mute })} title="Mute"
              className={`${iconBtn} ${t.mute ? "border-red-500/40 text-red-300 bg-red-500/10" : "border-white/10 text-zinc-400"}`}>M</button>
            <button onClick={() => ops.setTrackFlag(t.id, { solo: !t.solo })} title="Solo"
              className={`${iconBtn} ${t.solo ? "border-amber-500/40 text-amber-300 bg-amber-500/10" : "border-white/10 text-zinc-400"}`}>S</button>
            <GainSlider value={t.gain_db} onChange={(db) => ops.setTrackGain(t.id, db)} />
          </div>
        </div>
      ))}

      {/* Spur hinzufügen */}
      <button onClick={ops.addTrack}
        className="w-full px-2 py-1.5 text-[11px] text-cyan-200 border-b border-white/10 hover:bg-white/5 text-left">
        + Audiospur
      </button>
    </div>
  )
}
