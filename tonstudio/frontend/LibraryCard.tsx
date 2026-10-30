import { useTranslation } from "react-i18next"
import { fmtDuration } from "./api"
import { displayName } from "./libraryView"
import type { LibraryItem } from "./types"

interface Props {
  item: LibraryItem
  playing: boolean
  progress: number
  onToggle: () => void
  onSeek: (fraction: number) => void
  onDelete?: () => void
  onRename: () => void
}

const ORIGIN_ICON: Record<LibraryItem["origin"], string> = { generated: "✨", upload: "⬆️", project: "📁" }

/** Kompakte Kachel: Play-Knopf, Name (aus Prompt/Titel statt UUID), Dauer, Modell, schmaler Fortschrittsbalken. */
export function LibraryCard({ item, playing, progress, onToggle, onSeek, onDelete, onRename }: Props) {
  const { t } = useTranslation("tonstudio")
  const name = displayName(item, (date) => t("song_from", { date }))
  const copies = item.copies?.length ?? 0
  const sub = [fmtDuration(item.duration), item.model?.split("/").pop(), item.created_at?.slice(0, 10)].filter(Boolean).join(" · ")
  return (
    <li className={`group flex flex-col gap-1 rounded-[4px] border px-2 py-1.5 ${playing ? "border-[#69d7ff]/55 bg-[#1c2940]" : "border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))]"}`}>
      <div className="flex items-center gap-2">
        <button onClick={onToggle} aria-label={playing ? t("pause") : t("play")}
          className="grid h-7 w-7 shrink-0 place-items-center rounded-full border border-[#69d7ff]/40 bg-[#69d7ff]/10 text-xs text-[#69d7ff] hover:bg-[#69d7ff]/20">
          {playing ? "❚❚" : "▶"}
        </button>
        <div className="min-w-0 flex-1">
          <p className={`truncate text-xs font-semibold ${item.named === false ? "italic text-[#b8c3d4]" : "text-[#e8eef8]"}`} title={item.prompt || item.source_rel}>
            <span className="mr-1" title={t(`origin_${item.origin}`)}>{ORIGIN_ICON[item.origin]}</span>{name}
          </p>
          <p className="truncate text-[10px] text-[#9aa7bc]" title={item.source_rel}>{sub}</p>
        </div>
        {copies > 0 && (
          <span className="shrink-0 rounded border border-[rgb(var(--hh-s-rand,42_54_75))] px-1 text-[10px] text-[#9aa7bc]" title={item.copies!.join("\n")}>
            {t("copies", { count: copies })}
          </span>
        )}
        <button onClick={onRename} title={t("rename")} className="text-xs text-[#9aa7bc] opacity-0 hover:text-[#e8eef8] group-hover:opacity-100">✏️</button>
        {onDelete && (
          <button onClick={onDelete} title={t("clip_delete")} className="text-xs text-[#9aa7bc] opacity-0 hover:text-red-400 group-hover:opacity-100">🗑️</button>
        )}
      </div>
      <div role="slider" aria-label={t("position")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(progress * 100)} tabIndex={-1}
        onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); onSeek((e.clientX - r.left) / r.width) }}
        className="h-1 w-full cursor-pointer rounded bg-[rgb(var(--hh-s-rand,42_54_75))]">
        <div className="h-1 rounded bg-[#69d7ff]" style={{ width: `${Math.min(100, progress * 100)}%` }} />
      </div>
    </li>
  )
}
