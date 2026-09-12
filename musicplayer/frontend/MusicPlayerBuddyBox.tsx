// Kompakter Musicplayer für den dedizierten Buddy-Media-Slot.
import { Pause, Play, Repeat, Repeat1, Shuffle, SkipBack, SkipForward, Trash2, Volume2, Music } from "lucide-react"
import { type ReactNode, useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useAuthStore } from "@/features/auth/useAuthStore"
import { musicApi } from "./api"
import { Equalizer } from "./Equalizer"
import { GeneratedImport } from "./GeneratedImport"
import { MusicPlayerPanel } from "./MusicPlayerPanel"
import { UploadButton } from "./UploadButton"
import { useAudioPlayer } from "./useAudioPlayer"
import type { Track } from "./types"

const ACCENT = "rgb(217 70 239)"
const CONTROL_CLASS = "grid h-8 w-8 place-items-center rounded-[4px] border border-transparent text-[#8d9ab0] transition-colors hover:border-[#46617f] hover:bg-[#172133] hover:text-[#e8eef8] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#69d7ff]"

function fmt(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "0:00"
  const minutes = Math.floor(seconds / 60)
  const rest = Math.floor(seconds % 60)
  return `${minutes}:${rest.toString().padStart(2, "0")}`
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

export function MusicPlayerBuddyBox(_: { onPrompt?: (text: string) => void }) {
  const { t } = useTranslation("musicplayer")
  const isAdmin = useAuthStore((state) => state.role) === "admin"
  const [tracks, setTracks] = useState<Track[]>([])
  const player = useAudioPlayer(tracks)

  const load = useCallback(() => {
    musicApi.list().then(setTracks).catch(() => setTracks([]))
  }, [])
  useEffect(() => { load() }, [load])

  const remove = async (id: number) => {
    await musicApi.remove(id).catch(() => {})
    load()
  }

  return (
    <MusicPlayerPanel title={t("mp_title")} trackCount={tracks.length}>
      <div className="space-y-3">
        <div className="rounded-[4px] border border-[#2a364b] bg-[#0d1420] p-3">
          <p className="mb-2 text-[9px] font-black uppercase tracking-[0.15em] text-[#69d7ff]">
            {t("mp_now_playing")}
          </p>
          <div className="flex min-w-0 items-center gap-2">
            <Equalizer active={player.playing} color={ACCENT} />
            <span className="min-w-0 flex-1 truncate text-xs font-bold text-[#e8eef8]">
              {player.current ? player.current.title : t("mp_nothing")}
            </span>
          </div>

          <div className="mt-3 flex items-center gap-2">
            <span className="w-7 text-[9px] tabular-nums text-[#8d9ab0]">{fmt(player.currentTime)}</span>
            <input
              aria-label={t("mp_seek")}
              type="range"
              min={0}
              max={player.duration || 0}
              step={0.1}
              value={player.currentTime}
              onChange={(event) => player.seek(Number(event.target.value))}
              className="h-1 min-w-0 flex-1 cursor-pointer accent-fuchsia-500"
            />
            <span className="w-7 text-right text-[9px] tabular-nums text-[#8d9ab0]">{fmt(player.duration)}</span>
          </div>

          <div className="mt-3 flex items-center justify-center gap-1.5">
            <ControlButton label={t("mp_shuffle")} active={player.shuffle} onClick={player.toggleShuffle}>
              <Shuffle size={14} />
            </ControlButton>
            <ControlButton label={t("mp_prev")} onClick={player.prev}>
              <SkipBack size={15} />
            </ControlButton>
            <button
              type="button"
              onClick={player.toggle}
              title={player.playing ? t("mp_pause") : t("mp_play")}
              aria-label={player.playing ? t("mp_pause") : t("mp_play")}
              className="grid h-9 w-9 place-items-center rounded-[4px] border border-fuchsia-300/45 bg-fuchsia-500 text-white shadow-[0_0_16px_rgba(217,70,239,.18)] transition-colors hover:bg-fuchsia-400 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#69d7ff]"
            >
              {player.playing ? <Pause size={16} /> : <Play size={16} className="ml-0.5" />}
            </button>
            <ControlButton label={t("mp_next")} onClick={player.next}>
              <SkipForward size={15} />
            </ControlButton>
            <ControlButton
              label={t(player.repeat === "one" ? "mp_repeat_one" : "mp_repeat")}
              active={player.repeat !== "off"}
              onClick={player.cycleRepeat}
            >
              {player.repeat === "one" ? <Repeat1 size={14} /> : <Repeat size={14} />}
            </ControlButton>
          </div>

          <div className="mt-3 flex items-center gap-2 border-t border-[#2a364b] pt-3">
            <Volume2 size={13} className="shrink-0 text-[#8d9ab0]" />
            <input
              aria-label={t("mp_volume")}
              type="range"
              min={0}
              max={1}
              step={0.01}
              value={player.volume}
              onChange={(event) => player.setVolume(Number(event.target.value))}
              className="h-1 min-w-0 flex-1 cursor-pointer accent-fuchsia-500"
            />
            <span className="w-8 text-right text-[9px] tabular-nums text-[#8d9ab0]">
              {Math.round(player.volume * 100)}%
            </span>
          </div>
        </div>

        <div>
          <div className="mb-2 flex items-center justify-between gap-2">
            <p className="text-[9px] font-black uppercase tracking-[0.15em] text-[#69d7ff]">{t("mp_playlist")}</p>
            <span className="text-[9px] tabular-nums text-[#8d9ab0]">{tracks.length}</span>
          </div>
          {tracks.length === 0 ? (
            <p className="rounded-[4px] border border-dashed border-[#2a364b] bg-[#0d1420] px-3 py-4 text-center text-[11px] text-[#8d9ab0]">
              {t("mp_empty")}
            </p>
          ) : (
            <div className="max-h-44 space-y-1 overflow-y-auto pr-1">
              {tracks.map((track, index) => {
                const active = index === player.index
                return (
                  <div
                    key={track.id}
                    className={`flex min-w-0 items-center rounded-[4px] border transition-colors ${active ? "border-fuchsia-400/35 bg-fuchsia-500/10" : "border-transparent bg-[#111827] hover:border-[#2a364b] hover:bg-[#172133]"}`}
                  >
                    <button
                      type="button"
                      onClick={() => player.select(index)}
                      className="flex min-w-0 flex-1 items-center gap-2 px-2 py-2 text-left focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-[#69d7ff]"
                    >
                      <Music size={12} className={active ? "shrink-0 text-fuchsia-300" : "shrink-0 text-[#8d9ab0]"} />
                      <span className={active ? "truncate text-xs font-bold text-fuchsia-100" : "truncate text-xs text-[#c4cedd]"}>
                        {track.title}
                      </span>
                    </button>
                    {isAdmin && (
                      <button
                        type="button"
                        onClick={() => remove(track.id)}
                        aria-label={t("mp_delete", { title: track.title })}
                        title={t("mp_delete", { title: track.title })}
                        className="mr-1 grid h-7 w-7 shrink-0 place-items-center rounded-[4px] text-[#64748b] transition-colors hover:bg-rose-500/10 hover:text-rose-300 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-rose-300"
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {isAdmin && (
          <div className="space-y-2 border-t border-[#2a364b] pt-3">
            <UploadButton onDone={load} />
            <GeneratedImport onImported={load} />
          </div>
        )}

        <audio ref={player.audioRef} preload="metadata" className="hidden" />
      </div>
    </MusicPlayerPanel>
  )
}
