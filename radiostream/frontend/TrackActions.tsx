import { MoreHorizontal } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Playlist } from "./programLogic"
import { BTN_ICON } from "./ui"

interface Props {
  trackId: string; playlists: Pick<Playlist, "id" | "name" | "count">[]; open: boolean; onToggle: () => void
  onQueue: (trackId: string, front: boolean) => void; onAdd: (playlistId: string, trackId: string) => void
}

/** Knopf „Mehr“ an der Titelzeile: Als Nächstes, ans Ende der Warteschlange, zu einer Playlist. Für Handy und Rechner. */
export function TrackActions({ trackId, playlists, open, onToggle, onQueue, onAdd }: Props) {
  const { t } = useTranslation("radiostream")
  const item = "block w-full px-3 py-1.5 text-left text-sm text-[#e8eef8] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"
  return (
    <div className="relative">
      <button type="button" className={BTN_ICON} aria-label="track.actions" title={t("track.actions")} aria-expanded={open}
        onClick={onToggle}><MoreHorizontal size={14} /></button>
      {open && (
        <div role="menu" className="absolute right-0 z-20 mt-1 w-56 overflow-hidden rounded border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43))] shadow-lg">
          <button type="button" role="menuitem" className={item} onClick={() => onQueue(trackId, true)}>{t("track.next")}</button>
          <button type="button" role="menuitem" className={item} onClick={() => onQueue(trackId, false)}>{t("track.queue_end")}</button>
          {playlists.length > 0 && <>
            <p className="border-t border-[rgb(var(--hh-s-rand,42_54_75))] px-3 pt-2 text-xs uppercase tracking-wide text-[#9aa7bc]">{t("track.add_to")}</p>
            {playlists.map((p) => <button key={p.id} type="button" role="menuitem" className={item} onClick={() => onAdd(p.id, trackId)}>+ {p.name}</button>)}
          </>}
        </div>)}
    </div>
  )
}
