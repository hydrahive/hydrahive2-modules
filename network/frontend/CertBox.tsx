import { useState } from "react"
import { useTranslation } from "react-i18next"
import { confirmFingerprint, fetchFingerprint, testUdm, type Settings } from "./api"
import { errorKey } from "./logic"
import { BOX, BTN, BTN_MAIN, H2, MUTED } from "./ui"

/** Zertifikat der Dream Machine: Fingerabdruck holen, mit dem Gerät vergleichen, bestätigen; danach testen. */
export function CertBox({ confirmed, onChange }: { confirmed: boolean; onChange: (s: Settings) => void }) {
  const { t } = useTranslation("network")
  const [fp, setFp] = useState<{ fingerprint: string; pretty: string } | null>(null)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const run = (fn: () => Promise<void>) => { setBusy(true); setMsg(null); fn().catch((e) => setMsg({ ok: false, text: t(errorKey(e)) })).finally(() => setBusy(false)) }
  return (
    <section className={BOX}>
      <h3 className={H2}>{t("settings.cert")}</h3>
      <p className={MUTED}>{t("settings.cert_hint")}</p>
      <p className={`text-sm ${confirmed ? "text-emerald-300" : "text-amber-300"}`}>{t(confirmed ? "settings.cert_ok" : "settings.cert_missing")}</p>
      {fp && <code className="block break-all rounded bg-[rgb(var(--hh-s-box,21_28_43))] p-2 text-xs text-[#e8eef8]">{fp.pretty}</code>}
      <div className="flex flex-wrap gap-2">
        <button type="button" className={BTN} disabled={busy} onClick={() => run(() => fetchFingerprint().then(setFp))}>{t("settings.cert_fetch")}</button>
        {fp && <button type="button" className={BTN_MAIN} disabled={busy}
          onClick={() => run(() => confirmFingerprint(fp.fingerprint).then((s) => { onChange(s); setFp(null) }))}>{t("settings.cert_confirm")}</button>}
        {confirmed && <button type="button" className={BTN} disabled={busy}
          onClick={() => run(() => testUdm().then((r) => setMsg({ ok: true, text: t("settings.test_ok", { v: r.version ?? "?" }) })))}>{t("settings.test")}</button>}
      </div>
      {msg && <p role="status" className={`text-sm ${msg.ok ? "text-emerald-300" : "text-rose-300"}`}>{msg.text}</p>}
    </section>
  )
}
