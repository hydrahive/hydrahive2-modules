// Buddy-Box: kompakter MP3-Player + Track-Liste. Upload/Delete nur für Admin.
import { Music, Pause, Play, SkipBack, SkipForward, Trash2, Volume2 } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { musicApi } from "./api"
import { Equalizer } from "./Equalizer"
import { UploadButton } from "./UploadButton"
import { useAudioPlayer } from "./useAudioPlayer"
import type { Track } from "./types"

const ACCENT = "217 70 239"  // fuchsia-500

function fmt(s: number): string {
  if (!Number.isFinite(s) || s < 0) return "0:00"
  const m = Math.floor(s / 60)
  const sec = Math.floor(s % 60)
  return `${m}:${sec.toString().padStart(2, "0")}`
}

export function MusicPlayerBuddyBox(_: { onPrompt?: (text: string) => void }) {
  const { t } = useTranslation("musicplayer")
  const isAdmin = useAuthStore((s) => s.role) === "admin"
  const [tracks, setTracks] = useState<Track[]>([])
  const p = useAudioPlayer(tracks)

  const load = useCallback(() => {
    musicApi.list().then(setTracks).catch(() => setTracks([]))
  }, [])
  useEffect(() => { load() }, [load])

  const del = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation()
    await musicApi.remove(id).catch(() => {})
    load()
  }

  const accent = `rgb(${ACCENT})`

  return (
    <CollapsibleBox
      boxId="buddy-musicplayer"
      icon={<Music size={14} style={{ color: accent }} />}
      title={t("mp_title")}
      color={ACCENT}
      defaultCollapsed={false}
      className="w-60"
      headerRight={<span className="text-[10px] text-zinc-600">{tracks.length}</span>}
    >
      <div className="p-2 space-y-2">
        {/* Now-Playing + Transport */}
        <div className="rounded-lg bg-white/[3%] border border-white/[6%] p-2 space-y-2">
          <div className="flex items-center gap-2">
            <Equalizer active={p.playing} color={accent} />
            <span className="text-xs text-zinc-200 truncate flex-1">
              {p.current ? p.current.title : t("mp_nothing")}
            </span>
          </div>

          {/* Seek-Bar */}
          <div className="flex items-center gap-1.5">
            <span className="text-[9px] text-zinc-500 tabular-nums w-7">{fmt(p.currentTime)}</span>
            <input
              type="range" min={0} max={p.duration || 0} step={0.1} value={p.currentTime}
              onChange={(e) => p.seek(Number(e.target.value))}
              className="flex-1 h-1 accent-fuchsia-500 cursor-pointer"
              style={{ accentColor: accent }}
            />
            <span className="text-[9px] text-zinc-500 tabular-nums w-7">{fmt(p.duration)}</span>
          </div>

          {/* Buttons */}
          <div className="flex items-center justify-center gap-3">
            <button onClick={p.prev} className="text-zinc-400 hover:text-fuchsia-200" title={t("mp_prev")}>
              <SkipBack size={16} />
            </button>
            <button onClick={p.toggle}
              className="w-8 h-8 rounded-full flex items-center justify-center text-white"
              style={{ background: accent }} title={p.playing ? t("mp_pause") : t("mp_play")}>
              {p.playing ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
            </button>
            <button onClick={p.next} className="text-zinc-400 hover:text-fuchsia-200" title={t("mp_next")}>
              <SkipForward size={16} />
            </button>
          </div>

          {/* Volume */}
          <div className="flex items-center gap-1.5">
            <Volume2 size={12} className="text-zinc-500" />
            <input
              type="range" min={0} max={1} step={0.01} value={p.volume}
              onChange={(e) => p.setVolume(Number(e.target.value))}
              className="flex-1 h-1 cursor-pointer" style={{ accentColor: accent }}
            />
          </div>
        </div>

        {/* Track-Liste */}
        {tracks.length === 0 ? (
          <p className="text-[11px] text-zinc-500 text-center py-1">{t("mp_empty")}</p>
        ) : (
          <div className="space-y-0.5 max-h-44 overflow-y-auto">
            {tracks.map((tr, i) => (
              <button key={tr.id} onClick={() => p.select(i)}
                className={`w-full group flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors ${
                  i === p.index ? "bg-fuchsia-500/[12%] text-fuchsia-100" : "hover:bg-white/[4%] text-zinc-300"
                }`}>
                <Music size={12} className="shrink-0" style={{ color: i === p.index ? accent : undefined }} />
                <span className="text-xs truncate flex-1">{tr.title}</span>
                {isAdmin && (
                  <Trash2 size={12} onClick={(e) => del(tr.id, e)}
                    className="shrink-0 text-zinc-600 opacity-0 group-hover:opacity-100 hover:text-red-400" />
                )}
              </button>
            ))}
          </div>
        )}

        {isAdmin && <UploadButton onDone={load} />}

        {/* Das eine versteckte Audio-Element */}
        <audio ref={p.audioRef} preload="metadata" className="hidden" />
      </div>
    </CollapsibleBox>
  )
}
