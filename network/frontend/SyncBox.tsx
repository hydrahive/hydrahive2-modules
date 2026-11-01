import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { importSnapshot, syncNow } from "./api"
import { errorKey } from "./logic"
import { BOX, BTN, MUTED } from "./ui"

/** Sofort abrufen und eine frühere Sicherung der Dream Machine übernehmen. */
export function SyncBox() {
  const { t } = useTranslation("network")
  const file = useRef<HTMLInputElement>(null)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const run = (fn: () => Promise<string>) => {
    setBusy(true); setMsg(null)
    fn().then((text) => setMsg({ ok: true, text })).catch((e) => setMsg({ ok: false, text: t(errorKey(e)) })).finally(() => setBusy(false))
  }
  const onFile = (f: File | undefined) => {
    if (f) run(() => importSnapshot(f).then((r) => t("settings.import_ok", r)))
    if (file.current) file.current.value = ""
  }
  return (
    <section className={BOX}>
      <div className="flex flex-wrap gap-2">
        <button type="button" className={BTN} disabled={busy} onClick={() => run(() => syncNow().then((r) => t("settings.sync_ok", r)))}>{t("settings.sync")}</button>
        <button type="button" className={BTN} disabled={busy} onClick={() => file.current?.click()}>{t("settings.import")}</button>
        <input ref={file} type="file" accept=".json,.gz,application/json,application/gzip" className="hidden" onChange={(e) => onFile(e.target.files?.[0])} />
      </div>
      <h3 className="sr-only">{t("settings.import")}</h3>
      <p className={MUTED}>{t("settings.import_hint")}</p>
      {msg && <p role="status" className={`text-sm ${msg.ok ? "text-emerald-300" : "text-rose-300"}`}>{msg.text}</p>}
    </section>
  )
}
