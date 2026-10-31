import { Pause, Play } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { ReactNode } from "react"
import type { Track } from "./api"
import { fmtDuration } from "./logic"
import { DRAG_TYPE } from "./programLogic"

/** Eine Zeile der Titelliste. Breit: Tabelle; schmal (Handy): zweizeilig in der ersten Zelle. */
export function TrackRow({ t: tr, playing, onPlay, actions }: { t: Track; playing: boolean; onPlay: (id: string) => void; actions?: ReactNode }) {
  const { t } = useTranslation("radiostream")
  return (
    <tr className="border-b border-[rgb(var(--hh-s-rand,42_54_75))] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]" data-track={tr.track_id}
      draggable={!!actions} onDragStart={(e) => e.dataTransfer.setData(DRAG_TYPE, tr.track_id)}>
      <td className="w-10 py-1.5 pl-2">
        <button type="button" onClick={() => onPlay(tr.track_id)} aria-label={playing ? "stop" : "play"} title={playing ? t("stop") : t("play")}
          className="rounded-full p-1.5 text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] hover:text-white">
          {playing ? <Pause size={14} /> : <Play size={14} />}
        </button>
      </td>
      <td className="py-1.5 pr-3">
        <div className="truncate text-sm text-[#e8eef8]">{tr.title}</div>
        <div className="truncate text-xs text-[#c8d2df] md:hidden">{tr.artist}{tr.album ? ` · ${tr.album}` : ""}{tr.year ? ` · ${tr.year}` : ""}</div>
      </td>
      <td className="hidden max-w-[220px] truncate py-1.5 pr-3 text-sm text-[#c8d2df] md:table-cell">{tr.artist}</td>
      <td className="hidden max-w-[220px] truncate py-1.5 pr-3 text-sm text-[#c8d2df] lg:table-cell">{tr.album}</td>
      <td className="hidden py-1.5 pr-3 text-sm text-[#c8d2df] md:table-cell">{tr.year ?? ""}</td>
      <td className="py-1.5 pr-3 text-right text-sm tabular-nums text-[#c8d2df]">{fmtDuration(tr.duration_s)}</td>
      <td className="hidden py-1.5 pr-2 text-xs text-[#9aa7bc] sm:table-cell">{tr.format.toUpperCase()}</td>
      {actions !== undefined && <td className="w-10 py-1.5 pr-2">{actions}</td>}
    </tr>
  )
}
