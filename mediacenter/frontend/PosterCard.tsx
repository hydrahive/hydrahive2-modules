import { Film, Headphones, Music, Radio, Star, Tv } from "lucide-react"
import { useState, type ComponentType } from "react"
import { useTranslation } from "react-i18next"
import type { MediaType, ResultGroup } from "./types"

const FALLBACK_ICONS: Record<MediaType, ComponentType<{ size?: number; className?: string }>> = {
  movie: Film, tv: Tv, book: Headphones, audiobook: Headphones, audioplay: Radio, music: Music,
}

interface Props {
  group: ResultGroup
  onOpen: (group: ResultGroup) => void
}

/**
 * Eine Kachel im Poster-Raster: Cover, Titel, Jahr, Bewertung, Fassungsanzahl.
 *
 * Bücher liefert der Indexer ohne Cover — dort (und bei kaputten Bildern)
 * greift eine Typ-Illustration, damit das Raster nicht löchrig wirkt.
 */
export function PosterCard({ group, onOpen }: Props) {
  const { t } = useTranslation("mediacenter")
  const [broken, setBroken] = useState(false)
  const Icon = FALLBACK_ICONS[group.media_type] ?? Film
  const eligible = group.releases.filter((release) => release.decision === "eligible").length
  const showCover = Boolean(group.cover_url) && !broken

  return <button type="button" onClick={() => onOpen(group)}
    className="group flex flex-col overflow-hidden rounded-[6px] border border-[#28354a] bg-[#101724] text-left transition hover:border-cyan-400/50 focus:border-cyan-400/70 focus:outline-none">
    <div className="relative aspect-[2/3] w-full overflow-hidden bg-[#0c121d]">
      {showCover
        ? <img src={group.cover_url as string} alt="" loading="lazy" referrerPolicy="no-referrer"
            onError={() => setBroken(true)}
            className="h-full w-full object-cover transition group-hover:scale-[1.03]" />
        : <div className="flex h-full w-full items-center justify-center text-[#3c4a61]"><Icon size={44} /></div>}
      {group.rating !== null && <span className="absolute right-1.5 top-1.5 flex items-center gap-1 rounded-full bg-black/75 px-2 py-0.5 text-[10px] font-bold text-amber-300">
        <Star size={10} className="fill-amber-300" />{group.rating.toFixed(1)}
      </span>}
      {eligible > 0 && <span className="absolute bottom-1.5 left-1.5 rounded-full bg-cyan-400/90 px-2 py-0.5 text-[10px] font-bold text-[#06202b]">
        {t("results.versions", { count: eligible })}
      </span>}
    </div>
    <div className="flex min-h-[3.6rem] flex-col gap-0.5 p-2.5">
      <h3 className="line-clamp-2 text-xs font-bold leading-snug text-[#e8eef8]">{group.title}</h3>
      {group.year !== null && <span className="text-[11px] text-[#8d9ab0]">{group.year}</span>}
    </div>
  </button>
}
