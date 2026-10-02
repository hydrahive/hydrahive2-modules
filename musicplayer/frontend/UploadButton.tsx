import { Upload } from "lucide-react"
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { musicApi } from "./api"
import { MEDIA_ACCEPT } from "./mediaUtils"
import type { MediaKind } from "./types"

export function UploadButton({ projectId, kind, onDone }: { projectId: string; kind: MediaKind; onDone: () => void }) {
  const { t } = useTranslation("musicplayer"); const inputRef = useRef<HTMLInputElement | null>(null)
  const [busy, setBusy] = useState(false); const [err, setErr] = useState<string | null>(null)
  const onPick = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; event.target.value = ""; if (!file) return
    setErr(null); setBusy(true)
    try { await musicApi.upload(projectId, file, ""); onDone() } catch (ex) { setErr(ex instanceof Error ? ex.message : t("mp_upload_error")) } finally { setBusy(false) }
  }
  return <div><button type="button" onClick={() => inputRef.current?.click()} disabled={busy} className="flex w-full items-center justify-center gap-1.5 rounded-[4px] border border-dashed border-[#2a364b] bg-[#111827] px-2 py-2 text-xs font-bold text-[#c8f2ff] transition-colors hover:border-[#69d7ff]/70 hover:bg-[#172133] disabled:opacity-50"><Upload size={13} />{busy ? t("mp_uploading") : t("mp_upload", { kind: t(`mp_${kind}`) })}</button><input ref={inputRef} type="file" accept={MEDIA_ACCEPT[kind]} className="hidden" onChange={onPick} />{err && <p className="mt-1 text-[10px] text-rose-300">{err}</p>}</div>
}
