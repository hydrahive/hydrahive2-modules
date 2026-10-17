import { Music, User } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fileUrl } from "@/shared/files"
import type { LibraryItem } from "./api"
import { previewMode } from "./libraryView"

/** Das eigentliche Medium in der Vorschau: Video, Bild, Ton oder Figur. */
export function MediaView({ item, bind }: { item: LibraryItem | null; bind: (el: HTMLMediaElement | null) => void }) {
  const { t } = useTranslation("studio")
  const mode = previewMode(item)
  const frame = "flex aspect-video max-h-full w-full items-center justify-center overflow-hidden rounded-[4px] border border-[#223048] bg-black"
  if (!item || mode === "none") {
    return <div className={`${frame} text-xs text-[#68758a]`} data-studio-preview="none">{t("preview_empty")}</div>
  }
  if (mode === "video") {
    return (
      <div className={frame}>
        <video key={item.id} ref={bind} src={fileUrl(item.abs)} className="h-full w-full object-contain" preload="metadata"
          playsInline data-studio-preview="video" />
      </div>
    )
  }
  if (mode === "image") {
    return <div className={frame}><img src={fileUrl(item.abs)} alt={item.name} className="h-full w-full object-contain" data-studio-preview="image" /></div>
  }
  if (mode === "element") {
    return (
      <div className={`${frame} flex-col gap-2`} data-studio-preview="element">
        {item.thumb_abs ? <img src={fileUrl(item.thumb_abs)} alt={item.name} className="max-h-[80%] object-contain" />
          : <User size={42} className="text-[#46617f]" />}
        <span className="text-sm font-bold text-[#e8eef8]">{item.name}</span>
      </div>
    )
  }
  return (
    <div className={`${frame} flex-col gap-3 bg-gradient-to-br from-[#1c2940] to-[#080b11]`}>
      <Music size={40} className="text-[#69d7ff]" />
      <span className="max-w-[80%] truncate text-sm text-[#e8eef8]">{item.name}</span>
      <audio key={item.id} ref={bind} src={fileUrl(item.abs)} preload="metadata" data-studio-preview="audio" />
    </div>
  )
}
