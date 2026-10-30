import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { Film, Trash2, Upload } from "lucide-react"
import { vitrineApi, type VideoFile } from "./api"
import { sizeLabel } from "./rules"
import leerBild from "./assets/leer.webp"

export function VideoList({ videos, onChange }: { videos: VideoFile[]; onChange: () => void }) {
  const { t } = useTranslation("vitrine")
  const input = useRef<HTMLInputElement | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [confirm, setConfirm] = useState<string | null>(null)

  async function onPick(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    e.target.value = ""
    if (!file) return
    setErr(null); setBusy(true)
    try { await vitrineApi.upload(file); onChange() } catch (ex) { setErr(ex instanceof Error ? ex.message : String(ex)) } finally { setBusy(false) }
  }

  async function remove(name: string) {
    setConfirm(null)
    try { await vitrineApi.remove(name); onChange() } catch (ex) { setErr(ex instanceof Error ? ex.message : String(ex)) }
  }

  return (
    <section className="space-y-2">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-bold text-[#e8eef8]">{t("videos")}</h2>
        <button type="button" disabled={busy} onClick={() => input.current?.click()}
          className="ml-auto flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 px-2 py-1 text-xs font-bold text-[#69d7ff] disabled:opacity-50">
          <Upload size={13} />{busy ? t("uploading") : t("upload")}
        </button>
        <input ref={input} type="file" accept="video/mp4,video/webm,video/x-matroska,video/quicktime" className="hidden" onChange={onPick} />
      </div>
      <p className="text-xs text-[#9aa7bc]">{t("videos_hint")}</p>
      {err && <p className="text-xs text-rose-300">{err}</p>}
      {videos.length === 0
        ? <div className="rounded-[4px] border border-dashed border-[rgb(var(--hh-s-rand,42_54_75))]"><div className="flex flex-col items-center gap-2 py-4 text-center"><img src={leerBild} alt="" loading="lazy" draggable={false} className="mx-auto h-20 w-20 select-none object-contain" /><p className="text-xs text-[#9aa7bc]">{t("no_videos")}</p></div></div>
        : (
          <ul className="divide-y divide-[rgb(var(--hh-s-rand,28_38_56))] rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))]">
            {videos.map((v) => (
              <li key={v.name} className="flex items-center gap-3 px-3 py-2 text-sm text-[#c8d2df]">
                <Film size={14} className="shrink-0 text-[#69d7ff]" />
                <span className="truncate">{v.name}</span>
                <span className="ml-auto shrink-0 text-xs text-[#9aa7bc]">{sizeLabel(v.size)}</span>
                {confirm === v.name
                  ? <span className="flex shrink-0 gap-1 text-xs">
                      <button type="button" onClick={() => void remove(v.name)} className="rounded-[4px] bg-rose-500/20 px-2 py-0.5 text-rose-200">{t("delete_yes")}</button>
                      <button type="button" onClick={() => setConfirm(null)} className="px-2 py-0.5 text-[#9aa7bc]">{t("cancel")}</button>
                    </span>
                  : <button type="button" onClick={() => setConfirm(v.name)} title={t("delete")} aria-label={t("delete")} className="shrink-0 rounded p-1 text-[#9aa7bc] hover:text-rose-300"><Trash2 size={14} /></button>}
              </li>
            ))}
          </ul>
        )}
    </section>
  )
}
