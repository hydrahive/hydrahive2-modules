import { Pause, Play } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Track } from "./api"
import { fmtDuration } from "./logic"

/** Eine Zeile der Titelliste. Breit: Tabelle; schmal (Handy): zweizeilig in der ersten Zelle. */
export function TrackRow({ t: tr, playing, onPlay }: { t: Track; playing: boolean; onPlay: (id: string) => void }) {
  const { t } = useTranslation("radiostream")
  return (
    <tr className="border-b border-white/5 hover:bg-white/[3%]" data-track={tr.track_id}>
      <td className="w-10 py-1.5 pl-2">
        <button type="button" onClick={() => onPlay(tr.track_id)} aria-label={playing ? "stop" : "play"} title={playing ? t("stop") : t("play")}
          className="rounded-full p-1.5 text-zinc-300 hover:bg-white/10 hover:text-white">
          {playing ? <Pause size={14} /> : <Play size={14} />}
        </button>
      </td>
      <td className="py-1.5 pr-3">
        <div className="truncate text-sm text-zinc-100">{tr.title}</div>
        <div className="truncate text-xs text-zinc-400 md:hidden">{tr.artist}{tr.album ? ` · ${tr.album}` : ""}{tr.year ? ` · ${tr.year}` : ""}</div>
      </td>
      <td className="hidden max-w-[220px] truncate py-1.5 pr-3 text-sm text-zinc-300 md:table-cell">{tr.artist}</td>
      <td className="hidden max-w-[220px] truncate py-1.5 pr-3 text-sm text-zinc-400 lg:table-cell">{tr.album}</td>
      <td className="hidden py-1.5 pr-3 text-sm text-zinc-400 md:table-cell">{tr.year ?? ""}</td>
      <td className="py-1.5 pr-3 text-right text-sm tabular-nums text-zinc-400">{fmtDuration(tr.duration_s)}</td>
      <td className="hidden py-1.5 pr-2 text-xs text-zinc-500 sm:table-cell">{tr.format.toUpperCase()}</td>
    </tr>
  )
}
