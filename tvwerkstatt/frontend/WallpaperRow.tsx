import { useTranslation } from "react-i18next"
import type { TvwWallpaper } from "./api"
import { useAuthImage } from "./useAuthImage"

/** Vorschaubilder der Hintergründe einer Tageszeit, mit Entfernen. */
export function WallpaperRow({ walls, path, onDelete }: {
  walls: TvwWallpaper[]; path: (id: string) => string; onDelete: (id: string) => void
}) {
  const { t } = useTranslation("tvwerkstatt")
  if (walls.length === 0) return <p className="text-xs text-[#9aa7bc]">{t("desk.no_image")}</p>
  return (
    <div className="grid grid-cols-3 gap-1.5">
      {walls.map((w) => <Thumb key={w.wallpaper_id} w={w} src={path(w.wallpaper_id)} onDelete={onDelete} />)}
    </div>
  )
}

function Thumb({ w, src, onDelete }: { w: TvwWallpaper; src: string; onDelete: (id: string) => void }) {
  const { t } = useTranslation("tvwerkstatt")
  const img = useAuthImage(src)
  return (
    <div className="group relative aspect-video overflow-hidden rounded border border-[rgb(var(--hh-s-rand,52_66_92))]
      bg-[rgb(var(--hh-s-innen,36_48_71))]" title={w.title}>
      {img && <img src={img} alt={w.title} className="h-full w-full object-cover" />}
      <button type="button" aria-label={t("desk.remove_image")} onClick={() => onDelete(w.wallpaper_id)}
        className="absolute right-0.5 top-0.5 rounded bg-black/70 px-1 text-xs text-red-300 opacity-0 group-hover:opacity-100
          focus:opacity-100">✕</button>
    </div>
  )
}
