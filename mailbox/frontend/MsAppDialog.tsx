import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { X } from "lucide-react"
import { mailApi } from "./api"

const FIELD = "w-full rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-2 py-1.5 font-mono text-sm text-[#e8eef8]"
const BTN = "rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff] disabled:opacity-40"

/** Admin: die Microsoft-App von HydraHive eintragen (einmal global). Danach melden sich alle Nutzer darüber an. */
export function MsAppDialog({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("mailbox")
  const [cid, setCid] = useState("")
  const [tenant, setTenant] = useState("common")
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    mailApi.msApp().then((a) => { setCid(a.client_id); setTenant(a.tenant) }).catch(() => setMsg({ ok: false, text: t("app.loadFailed") }))
  }, [t])

  async function save(andCheck: boolean) {
    setBusy(true); setMsg(null)
    try {
      const a = await mailApi.msSaveApp(cid.trim(), tenant.trim())
      setCid(a.client_id); setTenant(a.tenant)
      if (!andCheck || !a.client_id) { setMsg({ ok: true, text: t("app.saved") }); return }
      const r = await mailApi.msCheckApp()
      setMsg(r.ok ? { ok: true, text: t("app.checkOk") } : { ok: false, text: `${t("app.checkFail")} ${r.error ?? ""}: ${r.message ?? ""}` })
    } catch (e) {
      setMsg({ ok: false, text: e instanceof Error ? e.message : String(e) })
    } finally { setBusy(false) }
  }

  return (
    <div role="dialog" aria-modal="true" aria-label={t("app.title")} data-mbx-ms-app="1"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="max-h-full w-full max-w-lg space-y-3 overflow-y-auto rounded-[6px] border border-[#2a364b] bg-[#0b1220] p-4 text-xs text-[#c8d2df]">
        <header className="flex items-center gap-2">
          <h2 className="flex-1 text-sm font-bold text-[#e8eef8]">{t("app.title")}</h2>
          <button type="button" onClick={onClose} aria-label={t("compose.close")} className="rounded p-1 text-[#8d9ab0] hover:bg-[#1c2638]"><X size={14} /></button>
        </header>
        <p>{t("app.intro")}</p>
        <ol className="list-decimal space-y-1 pl-5 text-[#8d9ab0]">
          <li>{t("app.step1")} <a href="https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade" target="_blank"
            rel="noopener noreferrer" className="text-[#69d7ff] hover:underline">entra.microsoft.com</a></li>
          <li>{t("app.step2")}</li>
          <li>{t("app.step3")}</li>
          <li>{t("app.step4")}</li>
        </ol>
        <label className="block space-y-1 text-[#8d9ab0]">{t("app.clientId")}
          <input className={FIELD} value={cid} onChange={(e) => setCid(e.target.value)} placeholder="00000000-0000-0000-0000-000000000000"
            spellCheck={false} data-mbx-ms-cid="1" /></label>
        <label className="block space-y-1 text-[#8d9ab0]">{t("app.tenant")}
          <input className={FIELD} value={tenant} onChange={(e) => setTenant(e.target.value)} spellCheck={false} /></label>
        <p className="text-[11px] text-[#718097]">{t("app.tenantHint")}</p>
        {msg && <p className={msg.ok ? "text-emerald-300" : "break-words text-rose-300"} data-mbx-ms-app-msg={msg.ok ? "ok" : "err"}>{msg.text}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-sm text-[#c8d2df] hover:bg-[#1c2638]">{t("settings.cancel")}</button>
          <button type="button" onClick={() => void save(false)} disabled={busy} className={BTN}>{t("settings.save")}</button>
          <button type="button" onClick={() => void save(true)} disabled={busy || !cid.trim()} data-mbx-ms-check="1" className={BTN}>{t("app.saveCheck")}</button>
        </div>
      </div>
    </div>
  )
}
