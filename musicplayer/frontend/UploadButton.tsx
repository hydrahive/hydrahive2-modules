// Admin-Upload: versteckter File-Input + Button. Meldet Erfolg via onDone.
import { Upload } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"

export function UploadButton({ projectId, onDone }: { projectId: string; onDone: () => void }) {
  const { t } = useTranslation("musicplayer")
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const onPick = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ""  // gleiche Datei erneut wählbar
    if (!file) return
    setErr(null)
    setBusy(true)
    try {
      await musicApi.upload(projectId, file, "")
      onDone()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : t("mp_upload_error"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-dashed border-[#2a364b] bg-[#111827] px-2 py-2 text-xs font-bold text-[#c8f2ff] transition-colors hover:border-[#69d7ff]/70 hover:bg-[#172133] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-[#69d7ff]"
      >
        <Upload size={13} />
        {busy ? t("mp_uploading") : t("mp_upload")}
      </button>
      <input
        ref={inputRef}
        type="file"
        accept="audio/mpeg,.mp3"
        className="hidden"
        onChange={onPick}
      />
      {err && <p className="mt-1 text-[10px] text-rose-300">{err}</p>}
    </div>
  )
}
