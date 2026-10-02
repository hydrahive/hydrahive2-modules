// Audio-Ansicht des Mediaplayers: Steuerung und Playlist.
// Der Player selbst (Audio-Element + Zustand) lebt in der Projektansicht, damit die
// Musik beim Umschalten auf Video weiterläuft.
import { Pause, Play, Repeat, Repeat1, Shuffle, SkipBack, SkipForward, Volume2 } from "lucide-react"
import { type ReactNode } from "react"
import { useTranslation } from "react-i18next"
import { Equalizer } from "./Equalizer"
import { TrackList } from "./TrackList"
import type { PlayerUI } from "./useAudioPlayer"
import type { LibraryPermissions, Track } from "./types"

const CONTROL_CLASS =
  "grid h-8 w-8 place-items-center rounded-[4px] border border-transparent text-[#8d9ab0] transition-colors " +
  "hover:border-[#46617f] hover:bg-[#172133] hover:text-[#e8eef8] " +
  "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#69d7ff]"

function fmt(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00"
  return `${Math.floor(seconds / 60)}:${Math.floor(seconds % 60).toString().padStart(2, "0")}`
}

function ControlButton({ label, active, onClick, children }: {
  label: string
  active?: boolean
  onClick: () => void
  children: ReactNode
}) {
  return (
    <button
      type="button"
      title={label}
      aria-label={label}
      aria-pressed={active}
      onClick={onClick}
      className={`${CONTROL_CLASS} ${active ? "border-fuchsia-400/35 bg-fuchsia-500/10 text-fuchsia-200" : ""}`}
    >
      {children}
    </button>
  )
}

export function AudioPlayerView({ projectId, tracks, permissions, onRemove, player }: {
  projectId: string
  tracks: Track[]
  permissions: LibraryPermissions
  onRemove: (id: number) => void
  player: PlayerUI
}) {
  const { t } = useTranslation("musicplayer")
  const {
    activeTrack, playing, elapsed, duration, volume, shuffle, repeat,
    select, toggle, prev, next, seek, setVolume, toggleShuffle, cycleRepeat,
  } = player
  const playLabel = playing ? t("mp_pause") : t("mp_play")

  return (
    <div className="space-y-3">
      <div className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-3">
        <p className="mb-2 text-[9px] font-black uppercase tracking-[.15em] text-[#69d7ff]">{t("mp_now_playing")}</p>
        <div className="flex min-w-0 items-center gap-2">
          <Equalizer active={playing} color="#d946ef" />
          <span className="truncate text-xs font-bold text-[#e8eef8]">{activeTrack?.title ?? t("mp_nothing")}</span>
        </div>
        <div className="mt-3 flex items-center gap-2 text-[9px] text-[#8d9ab0]">
          <span>{fmt(elapsed)}</span>
          <input
            aria-label={t("mp_seek")}
            type="range"
            min={0}
            max={duration || 0}
            step={0.1}
            value={elapsed}
            onChange={(e) => seek(Number(e.target.value))}
            className="flex-1 accent-fuchsia-500"
          />
          <span>{fmt(duration)}</span>
        </div>
        <div className="mt-2 flex items-center justify-center gap-1">
          <ControlButton label={t("mp_shuffle")} active={shuffle} onClick={toggleShuffle}>
            <Shuffle size={14} />
          </ControlButton>
          <ControlButton label={t("mp_prev")} onClick={prev}>
            <SkipBack size={14} />
          </ControlButton>
          <button
            type="button"
            title={playLabel}
            aria-label={playLabel}
            onClick={toggle}
            className="grid h-9 w-9 place-items-center rounded-[4px] bg-fuchsia-500 text-white hover:bg-fuchsia-400"
          >
            {playing ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <ControlButton label={t("mp_next")} onClick={next}>
            <SkipForward size={14} />
          </ControlButton>
          <ControlButton
            label={t(repeat === "one" ? "mp_repeat_one" : "mp_repeat")}
            active={repeat !== "off"}
            onClick={cycleRepeat}
          >
            {repeat === "one" ? <Repeat1 size={14} /> : <Repeat size={14} />}
          </ControlButton>
        </div>
        <div className="mt-2 flex items-center gap-2 border-t border-[#2a364b] pt-2 text-[#8d9ab0]">
          <Volume2 size={13} />
          <input
            aria-label={t("mp_volume")}
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={volume}
            onChange={(e) => setVolume(Number(e.target.value))}
            className="flex-1 accent-fuchsia-500"
          />
        </div>
      </div>
      <TrackList
        projectId={projectId}
        kind="audio"
        tracks={tracks}
        activeId={activeTrack?.id}
        permissions={permissions}
        onSelect={(track) => select(track.id)}
        onRemove={onRemove}
      />
    </div>
  )
}
