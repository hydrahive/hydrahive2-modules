import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { audioUrl, fmtDuration, tonstudioApi } from "./api"
import { errText } from "./errors"
import type { LibraryItem } from "./types"

interface Props {
  projectId: string
  items: LibraryItem[]
  onChanged: () => void
}

const ORIGIN_ICON: Record<LibraryItem["origin"], string> = { generated: "✨", upload: "⬆️", project: "📁" }

/** Bibliothek: eigene Clips (erzeugt/hochgeladen) und Audio aus dem Projekt, mit Player. */
export function Library({ projectId, items, onChanged }: Props) {
  const { t } = useTranslation("tonstudio")
  const fileRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  async function upload(file: File | undefined) {
    if (!file) return
    setBusy(true)
    setError("")
    try {
      await tonstudioApi.upload(projectId, file)
      onChanged()
    } catch (e) {
      setError(errText(e))
    } finally {
      setBusy(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  async function remove(rel: string) {
    if (!confirm(t("clip_delete_confirm"))) return
    try {
      await tonstudioApi.deleteClip(projectId, rel)
      onChanged()
    } catch (e) {
      setError(errText(e))
    }
  }

  return (
    <section className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        <h3 className="flex-1 text-sm font-semibold text-slate-200">🎧 {t("library")}</h3>
        <input ref={fileRef} type="file" accept="audio/*,.mp3,.wav,.flac,.ogg,.m4a" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
        <button onClick={() => fileRef.current?.click()} disabled={busy} className="rounded border border-slate-600 px-2 py-1 text-xs text-slate-300 hover:bg-slate-700 disabled:opacity-40">
          {busy ? t("uploading") : `⬆️ ${t("upload")}`}
        </button>
      </div>
      {error && <p className="text-xs text-red-400">{error}</p>}
      {items.length === 0 && <p className="text-xs text-slate-500">{t("library_empty")}</p>}
      <ul className="flex flex-col gap-2">
        {items.map((it) => (
          <li key={it.source_rel} className="group flex flex-col gap-1 rounded border border-slate-700 bg-slate-800/50 p-2">
            <div className="flex items-center gap-2">
              <span title={t(`origin_${it.origin}`)}>{ORIGIN_ICON[it.origin]}</span>
              <span className="flex-1 truncate text-xs text-slate-200" title={it.prompt || it.source_rel}>
                {it.prompt || it.name}
              </span>
              <span className="text-[11px] text-slate-500">{fmtDuration(it.duration)}</span>
              {it.origin !== "project" && (
                <button onClick={() => remove(it.source_rel)} title={t("clip_delete")} className="text-xs text-slate-500 opacity-0 hover:text-red-400 group-hover:opacity-100">
                  🗑️
                </button>
              )}
            </div>
            {it.model && <span className="text-[11px] text-slate-500">{it.model}</span>}
            <audio src={audioUrl(projectId, it.source_rel)} controls preload="none" className="h-8 w-full" />
          </li>
        ))}
      </ul>
    </section>
  )
}
