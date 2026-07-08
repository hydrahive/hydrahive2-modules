import { useEffect, useMemo, useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import { VideoGenerationDialog } from "./VideoGenerationDialog"
import { PromptView } from "./PromptView"
import type { AtelierCharacter, GalleryItem } from "./types"

interface Props {
  projectId: string
  items: GalleryItem[]
  characters: AtelierCharacter[]
  onPromoted: () => void
  onVideoStarted: () => void
  onRepeat: (item: GalleryItem) => void
}

type ViewSize = "small" | "medium" | "large" | "list"
const GRID_MIN: Record<Exclude<ViewSize, "list">, string> = {
  small: "150px",
  medium: "220px",
  large: "340px",
}

/** Galerie der generierten Bilder + "als Referenz übernehmen" + "zu Video". */
export function ImageGalleryPanel({ projectId, items, characters, onPromoted, onVideoStarted, onRepeat }: Props) {
  const { t } = useTranslation("atelier")
  const [zoom, setZoom] = useState<GalleryItem | null>(null)
  const [promoteFor, setPromoteFor] = useState<GalleryItem | null>(null)
  const [videoFor, setVideoFor] = useState<GalleryItem | null>(null)
  const [viewSize, setViewSize] = useState<ViewSize>("medium")

  const zoomIndex = useMemo(() => (zoom ? items.findIndex((it) => it.rel === zoom.rel) : -1), [items, zoom])

  useEffect(() => {
    if (!zoom) return
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setZoom(null)
      if (e.key === "ArrowLeft") stepZoom(-1)
      if (e.key === "ArrowRight") stepZoom(1)
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom, zoomIndex, items])

  function stepZoom(delta: number) {
    if (zoomIndex < 0 || items.length === 0) return
    const next = (zoomIndex + delta + items.length) % items.length
    setZoom(items[next])
  }

  async function promote(charId: string) {
    if (!promoteFor) return
    await atelierApi.promote(projectId, charId, promoteFor.rel)
    setPromoteFor(null)
    onPromoted()
  }

  async function del(it: GalleryItem) {
    if (!confirm(t("delete_image_confirm"))) return
    await atelierApi.deleteImage(projectId, it.rel)
    if (zoom?.rel === it.rel) setZoom(null)
    onPromoted()  // reload
  }

  const gridStyle = viewSize === "list"
    ? undefined
    : { gridTemplateColumns: `repeat(auto-fill, minmax(${GRID_MIN[viewSize]}, 1fr))` }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">{t("gallery")}</h3>
          <p className="text-xs text-slate-500">{items.length} {t("gallery_items")}</p>
        </div>
        <div className="flex gap-1 rounded-lg border border-slate-700 bg-slate-900/70 p-1">
          {(["small", "medium", "large", "list"] as const).map((size) => (
            <button
              key={size}
              onClick={() => setViewSize(size)}
              className={`rounded px-2 py-1 text-[11px] ${viewSize === size ? "bg-emerald-600 text-white" : "text-slate-400 hover:bg-slate-800"}`}
            >
              {t(`gallery_view_${size}`)}
            </button>
          ))}
        </div>
      </div>
      {items.length === 0 && <p className="text-xs text-slate-500">{t("gallery_empty")}</p>}

      <div className={viewSize === "list" ? "flex flex-col gap-2" : "grid gap-2"} style={gridStyle}>
        {items.map((it) => (
          <div
            key={it.name}
            className={viewSize === "list"
              ? "group relative flex gap-3 rounded-lg border border-slate-700 bg-slate-900/40 p-2"
              : "group relative overflow-hidden rounded-lg border border-slate-700 bg-slate-900/40"}
          >
            <img
              src={fileUrl(it.path)}
              alt={it.prompt ?? ""}
              className={viewSize === "list"
                ? "h-24 w-24 shrink-0 rounded object-cover cursor-zoom-in"
                : "w-full aspect-square object-cover cursor-zoom-in"}
              loading="lazy"
              onClick={() => setZoom(it)}
            />
            {viewSize === "list" && (
              <div className="min-w-0 flex-1 text-xs">
                <p className="truncate text-slate-200">{it.name}</p>
                {it.prompt && <PromptView text={it.prompt} clamp={2} />}
                <div className="mt-1 flex flex-wrap gap-1 text-[10px] text-slate-500">
                  {it.model && <span className="rounded bg-slate-800 px-1.5 py-0.5">🤖 {it.model}</span>}
                  {it.seed != null && <span className="rounded bg-slate-800 px-1.5 py-0.5">seed {it.seed}</span>}
                </div>
              </div>
            )}
            <div className={viewSize === "list"
              ? "flex shrink-0 items-start gap-1"
              : "absolute inset-x-0 bottom-0 flex gap-1 bg-black/65 p-1 opacity-0 transition-opacity group-hover:opacity-100"}
            >
              <button
                onClick={() => setZoom(it)}
                className="rounded bg-slate-700/90 px-2 py-1 text-[10px] hover:bg-slate-600"
                title={t("open")}
              >
                🔍
              </button>
              <button
                onClick={() => setPromoteFor(it)}
                className="flex-1 rounded bg-emerald-600 px-2 py-1 text-[10px] hover:bg-emerald-500"
              >
                {t("promote")}
              </button>
              <button
                onClick={() => setVideoFor(it)}
                className="rounded bg-sky-600 px-2 py-1 text-[10px] hover:bg-sky-500"
                title={t("make_video")}
              >
                🎬
              </button>
              <button
                onClick={() => onRepeat(it)}
                className="rounded bg-violet-600 px-2 py-1 text-[10px] hover:bg-violet-500"
                title={t("repeat_image")}
              >
                🔁
              </button>
              <button
                onClick={() => del(it)}
                className="rounded bg-red-600/80 px-2 py-1 text-[10px] hover:bg-red-500"
                title={t("delete")}
              >
                🗑️
              </button>
            </div>
          </div>
        ))}
      </div>

      {zoom && (
        <div className="fixed inset-0 z-50 bg-black/85 p-4" onClick={() => setZoom(null)}>
          <div className="mx-auto flex h-full max-w-7xl flex-col gap-3" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between gap-3 text-xs text-slate-300">
              <span>{zoomIndex + 1} / {items.length} · {zoom.name}</span>
              <button onClick={() => setZoom(null)} className="rounded bg-slate-800 px-3 py-1 hover:bg-slate-700">{t("close")}</button>
            </div>
            <div className="grid min-h-0 flex-1 grid-cols-[minmax(0,1fr)_320px] gap-4 max-lg:grid-cols-1">
              <div className="relative grid min-h-0 place-items-center rounded-lg bg-black/40">
                {items.length > 1 && (
                  <button onClick={() => stepZoom(-1)} className="absolute left-2 top-1/2 rounded-full bg-black/60 px-3 py-2 text-lg hover:bg-slate-700">‹</button>
                )}
                <img src={fileUrl(zoom.path)} alt="" className="max-h-[82vh] max-w-full rounded-lg object-contain" />
                {items.length > 1 && (
                  <button onClick={() => stepZoom(1)} className="absolute right-2 top-1/2 rounded-full bg-black/60 px-3 py-2 text-lg hover:bg-slate-700">›</button>
                )}
              </div>
              <aside className="overflow-auto rounded-lg border border-slate-700 bg-slate-900 p-3 text-xs text-slate-300">
                <h4 className="mb-2 text-sm font-semibold text-slate-100">{t("details")}</h4>
                {zoom.prompt && <PromptView text={zoom.prompt} />}
                <div className="mt-3 flex flex-col gap-1 text-slate-400">
                  {zoom.model && <span>{t("model")}: {zoom.model}</span>}
                  {zoom.seed != null && <span>seed: {zoom.seed}</span>}
                  <span>{t("file")}: {zoom.rel}</span>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button onClick={() => { onRepeat(zoom); setZoom(null) }} className="rounded bg-violet-600 px-3 py-1 text-xs hover:bg-violet-500">🔁 {t("repeat_image")}</button>
                  <button onClick={() => setPromoteFor(zoom)} className="rounded bg-emerald-600 px-3 py-1 text-xs hover:bg-emerald-500">{t("promote")}</button>
                  <button onClick={() => setVideoFor(zoom)} className="rounded bg-sky-600 px-3 py-1 text-xs hover:bg-sky-500">🎬 {t("make_video")}</button>
                  <button onClick={() => del(zoom)} className="rounded bg-red-600/80 px-3 py-1 text-xs hover:bg-red-500">🗑️ {t("delete")}</button>
                </div>
              </aside>
            </div>
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
        <VideoGenerationDialog
          projectId={projectId}
          source={videoFor}
          onClose={() => setVideoFor(null)}
          onStarted={onVideoStarted}
        />
      )}
    </div>
  )
}
