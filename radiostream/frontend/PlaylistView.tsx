import { ChevronDown, ChevronUp, X } from "lucide-react"
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { fmtDuration } from "./logic"
import { DRAG_TYPE, moveIndex, type Playlist, type PlaylistItem } from "./programLogic"
import { BOX, BTN_DANGER, BTN_ICON, BTN_MAIN, INPUT } from "./ui"

interface Props {
  pl: Playlist; items: PlaylistItem[]; canModerate: boolean; busy: boolean
  onChange: (v: Partial<Pick<Playlist, "name" | "order_mode" | "at_end">>) => void
  onMove: (from: number, to: number) => void; onRemove: (pos: number) => void; onDelete: () => void; onPlayNow: () => void
  onDropTracks?: (trackIds: string[]) => void
}

/** Eine Playlist: Abspielart, Titel umsortieren (Ziehen am Rechner, Pfeile überall), entfernen, löschen, jetzt spielen. */
export function PlaylistView({ pl, items, canModerate, busy, onChange, onMove, onRemove, onDelete, onPlayNow, onDropTracks }: Props) {
  const { t } = useTranslation("radiostream")
  const [drag, setDrag] = useState<number | null>(null)
  const drop = (e: React.DragEvent, to: number | null) => {
    e.preventDefault()
    const ids = e.dataTransfer.getData(DRAG_TYPE)
    if (ids && onDropTracks) onDropTracks(ids.split(","))
    else if (drag !== null && to !== null && drag !== to) onMove(drag, to)
    setDrag(null)
  }
  return (
    <section className={BOX} data-dropzone={pl.id} onDragOver={(e) => canModerate && e.preventDefault()} onDrop={(e) => canModerate && drop(e, null)}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-base font-semibold text-[#e8eef8] break-words">{pl.name} <span className="text-sm font-normal text-[#9aa7bc]">{t("playlist.count", { count: items.length })}</span></h3>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={BTN_MAIN} disabled={busy || !canModerate || items.length === 0} onClick={onPlayNow}>{t("playlist.play_now")}</button>
          {canModerate && <button type="button" className={BTN_DANGER} disabled={busy} onClick={onDelete}>{t("playlist.delete")}</button>}
        </div>
      </div>
      {canModerate && (
        <div className="grid gap-2 sm:grid-cols-2">
          <select className={INPUT} value={pl.order_mode} disabled={busy} aria-label="order" onChange={(e) => onChange({ order_mode: e.target.value as Playlist["order_mode"] })}>
            <option value="ordered">{t("playlist.ordered")}</option><option value="shuffle">{t("playlist.shuffle")}</option></select>
          <select className={INPUT} value={pl.at_end} disabled={busy} aria-label="at_end" onChange={(e) => onChange({ at_end: e.target.value as Playlist["at_end"] })}>
            <option value="repeat">{t("playlist.repeat")}</option><option value="back">{t("playlist.back")}</option></select>
        </div>)}
      {items.length === 0 ? <p className="rounded border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))] p-4 text-sm text-[#c8d2df]">{t("playlist.empty")}</p> : (
        <ol className="divide-y divide-[rgb(var(--hh-s-rand,42_54_75))]">
          {items.map((it, i) => (
            <li key={`${it.pos}-${it.track_id}`} draggable={canModerate} onDragStart={() => setDrag(i)} onDragOver={(e) => canModerate && e.preventDefault()}
              onDrop={(e) => { e.stopPropagation(); if (canModerate) drop(e, i) }}
              className={`flex items-center gap-2 py-1.5 text-sm ${it.available ? "text-[#e8eef8]" : "text-[#9aa7bc] line-through"}`}>
              <span className="w-6 shrink-0 text-right tabular-nums text-xs text-[#9aa7bc]">{i + 1}</span>
              <span className="min-w-0 flex-1 break-words">{[it.artist, it.title].filter(Boolean).join(" – ")}
                {!it.available && <span className="ml-2 text-xs no-underline">({t("playlist.missing")})</span>}</span>
              <span className="hidden w-12 text-right tabular-nums text-xs text-[#9aa7bc] sm:inline">{fmtDuration(it.duration_s)}</span>
              {canModerate && <>
                <button type="button" className={BTN_ICON} title={t("playlist.up")} aria-label={`playlist.up ${i}`} disabled={busy || moveIndex(items.length, i, -1) === null} onClick={() => onMove(i, i - 1)}><ChevronUp size={14} /></button>
                <button type="button" className={BTN_ICON} title={t("playlist.down")} aria-label={`playlist.down ${i}`} disabled={busy || moveIndex(items.length, i, 1) === null} onClick={() => onMove(i, i + 1)}><ChevronDown size={14} /></button>
                <button type="button" className={BTN_ICON} title={t("playlist.remove")} aria-label={`playlist.remove ${i}`} disabled={busy} onClick={() => onRemove(i)}><X size={14} /></button>
              </>}
            </li>))}
        </ol>)}
      {canModerate && <p className="hidden text-xs text-[#9aa7bc] lg:block">{t("playlist.drop")}</p>}
    </section>
  )
}
