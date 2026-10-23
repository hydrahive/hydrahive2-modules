import { useState } from "react"
import { useTranslation } from "react-i18next"
import { X } from "lucide-react"
import { mailApi, type Account } from "./api"
import { MsReauth } from "./MsReauth"

const FIELD = "w-full rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-2 py-1 text-sm text-[#e8eef8]"

/** Absendername und Signatur je Konto (Spec §6). Die Signatur hängt der Server beim Senden an (nach „-- “). */
export function AccountSettings({ account, onClose, onSaved }: { account: Account; onClose: () => void; onSaved: () => void }) {
  const { t } = useTranslation("mailbox")
  const [name, setName] = useState(account.sender_name)
  const [sig, setSig] = useState(account.signature)
  const [err, setErr] = useState(false)
  const [busy, setBusy] = useState(false)

  async function save() {
    setBusy(true)
    setErr(false)
    try {
      await mailApi.updateAccount(account.id, { sender_name: name.trim(), signature: sig })
      onSaved()
    } catch {
      setErr(true)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-label={t("settings.title")} data-mbx-settings="1"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div className="w-full max-w-lg space-y-3 rounded-[6px] border border-[#2a364b] bg-[#0b1220] p-4">
        <header className="flex items-center gap-2">
          <h2 className="flex-1 text-sm font-bold text-[#e8eef8]">{t("settings.title")} · {account.address}</h2>
          <button type="button" onClick={onClose} aria-label={t("compose.close")} className="rounded p-1 text-[#8d9ab0] hover:bg-[#1c2638]">
            <X size={14} /></button>
        </header>
        <label className="block space-y-1 text-xs text-[#8d9ab0]">{t("settings.senderName")}
          <input value={name} onChange={(e) => setName(e.target.value)} maxLength={200} className={FIELD} data-mbx-sender-name="1" />
        </label>
        <label className="block space-y-1 text-xs text-[#8d9ab0]">{t("settings.signature")}
          <textarea value={sig} onChange={(e) => setSig(e.target.value)} maxLength={5000} rows={5}
            className={`${FIELD} resize-y font-sans`} data-mbx-signature="1" />
        </label>
        <p className="text-[11px] text-[#718097]">{t("settings.signatureHint")}</p>
        {err && <p role="alert" className="text-xs text-rose-300">{t("settings.failed")}</p>}
        {account.auth === "oauth_microsoft" && <MsReauth account={account} onDone={onSaved} />}
        <footer className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] border border-[#2a364b] px-3 py-1 text-sm text-[#c8d2df]">
            {t("settings.cancel")}</button>
          <button type="button" onClick={() => void save()} disabled={busy} data-mbx-settings-save="1"
            className="rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1 text-sm font-semibold text-[#69d7ff] disabled:opacity-50">
            {t("settings.save")}</button>
        </footer>
      </div>
    </div>
  )
}
