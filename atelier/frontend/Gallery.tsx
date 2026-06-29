import { useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import { VideoDialog } from "./VideoDialog"
import type { AtelierCharacter, GalleryItem } from "./types"

interface Props {
  projectId: string
  items: GalleryItem[]
  characters: AtelierCharacter[]
  onPromoted: () => void
  onVideoStarted: () => void
}

/** Rechte Spalte: Galerie der generierten Bilder + "als Referenz übernehmen" + "zu Video". */
export function Gallery({ projectId, items, characters, onPromoted, onVideoStarted }: Props) {
  const { t } = useTranslation("atelier")
  const [zoom, setZoom] = useState<GalleryItem | null>(null)
  const [promoteFor, setPromoteFor] = useState<GalleryItem | null>(null)
  const [videoFor, setVideoFor] = useState<GalleryItem | null>(null)

  async function promote(charId: string) {
    if (!promoteFor) return
    await atelierApi.promote(projectId, charId, promoteFor.rel)
    setPromoteFor(null)
    onPromoted()
  }

  async function del(it: GalleryItem) {
    if (!confirm(t("delete_image_confirm"))) return
    await atelierApi.deleteImage(projectId, it.rel)
    onPromoted()  // reload
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-200">{t("gallery")}</h3>
      {items.length === 0 && <p className="text-xs text-slate-500">{t("gallery_empty")}</p>}

      <div className="grid grid-cols-2 gap-2">
        {items.map((it) => (
          <div key={it.name} className="group relative rounded overflow-hidden border border-slate-700">
            <img
              src={fileUrl(it.path)}
              alt={it.prompt ?? ""}
              className="w-full aspect-square object-cover cursor-zoom-in"
              onClick={() => setZoom(it)}
            />
            <div className="absolute inset-x-0 bottom-0 p-1 bg-black/60 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
              <button
                onClick={() => setPromoteFor(it)}
                className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-600 hover:bg-emerald-500 flex-1"
              >
                {t("promote")}
              </button>
              <button
                onClick={() => setVideoFor(it)}
                className="text-[10px] px-1.5 py-0.5 rounded bg-sky-600 hover:bg-sky-500"
                title={t("make_video")}
              >
                🎬
              </button>
              <button
                onClick={() => del(it)}
                className="text-[10px] px-1.5 py-0.5 rounded bg-red-600/80 hover:bg-red-500"
                title={t("delete")}
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>

      {zoom && (
        <div className="fixed inset-0 z-50 bg-black/80 grid place-items-center p-6" onClick={() => setZoom(null)}>
          <div className="max-w-3xl flex flex-col gap-2" onClick={(e) => e.stopPropagation()}>
            <img src={fileUrl(zoom.path)} alt="" className="max-h-[70vh] rounded-lg" />
            {zoom.prompt && <p className="text-xs text-slate-300 bg-slate-800 rounded p-2">{zoom.prompt}</p>}
            <div className="flex gap-3 text-xs text-slate-400">
              {zoom.model && <span>{t("model")}: {zoom.model}</span>}
              {zoom.seed != null && <span>seed: {zoom.seed}</span>}
            </div>
            <button onClick={() => setZoom(null)} className="text-xs px-3 py-1 rounded bg-slate-700 self-end">
              {t("close")}
            </button>
          </div>
        </div>
      )}

      {promoteFor && (
        <div className="fixed inset-0 z-50 bg-black/70 grid place-items-center p-6" onClick={() => setPromoteFor(null)}>
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-4 flex flex-col gap-2 max-w-xs" onClick={(e) => e.stopPropagation()}>
            <h4 className="text-sm font-semibold text-slate-200">{t("promote_to")}</h4>
            {characters.length === 0 && <p className="text-xs text-slate-500">{t("no_characters")}</p>}
            {characters.map((c) => (
              <button
                key={c.id}
                onClick={() => promote(c.id)}
                className="text-xs px-3 py-1.5 rounded bg-slate-700 hover:bg-emerald-600 text-left"
              >
                {c.name || t("untitled")}
              </button>
            ))}
            <button onClick={() => setPromoteFor(null)} className="text-xs text-slate-400 mt-1">
              {t("cancel")}
            </button>
          </div>
        </div>
      )}

      {videoFor && (
        <VideoDialog
          projectId={projectId}
          source={videoFor}
          onClose={() => setVideoFor(null)}
          onStarted={onVideoStarted}
        />
      )}
    </div>
  )
}
