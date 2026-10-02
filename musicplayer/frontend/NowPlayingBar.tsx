// Schmale Musik-Leiste in der Video-Ansicht: laufendes Lied, Pause/Weiter,
// Klick auf den Titel wechselt zurück zu Audio.
import { Pause, Play } from "lucide-react"
import { useTranslation } from "react-i18next"
import { Equalizer } from "./Equalizer"
import type { Track } from "./types"

export function NowPlayingBar({ track, playing, onToggle, onOpen }: {
  track: Track | null
  playing: boolean
  onToggle: () => void
  onOpen: () => void
}) {
  const { t } = useTranslation("musicplayer")
  if (!track) return null
  const label = playing ? t("mp_pause") : t("mp_play")
  return (
    <div className="flex min-w-0 items-center gap-2 rounded-[4px] border border-fuchsia-400/25 bg-fuchsia-500/5 px-2 py-1.5">
      <Equalizer active={playing} color="#d946ef" />
      <button
        type="button"
        onClick={onOpen}
        title={t("mp_back_to_audio")}
        className="min-w-0 flex-1 truncate text-left text-xs text-[#c4cedd] hover:text-[#e8eef8]"
      >
        {track.title}
      </button>
      <button
        type="button"
        onClick={onToggle}
        title={label}
        aria-label={label}
        className="grid h-7 w-7 shrink-0 place-items-center rounded-[4px] bg-fuchsia-500/80 text-white hover:bg-fuchsia-400"
      >
        {playing ? <Pause size={13} /> : <Play size={13} />}
      </button>
    </div>
  )
}
