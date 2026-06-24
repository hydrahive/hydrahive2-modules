// Admin-Upload: versteckter File-Input + Button. Meldet Erfolg via onDone.
import { Upload } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"

export function UploadButton({ onDone }: { onDone: () => void }) {
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
      await musicApi.upload(file, "")
      onDone()
    } catch (ex) {
      setErr(ex instanceof Error ? ex.message : t("mp_upload_error"))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="pt-1">
      <button
        onClick={() => inputRef.current?.click()}
        disabled={busy}
        className="w-full flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-lg border border-dashed border-fuchsia-400/30 text-fuchsia-200/90 hover:bg-fuchsia-400/[6%] text-xs disabled:opacity-50 transition-colors"
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
      {err && <p className="mt-1 text-[10px] text-red-400">{err}</p>}
    </div>
  )
}
