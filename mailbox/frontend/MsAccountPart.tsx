import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { mailApi } from "./api"
import { MsSignInView } from "./MsSignInView"
import { errorCode } from "./msFlow"
import { useMsSignIn } from "./useMsSignIn"

interface Props {
  address: string
  label: string
  /** null = wird noch geprüft; false = Admin hat die Microsoft-App noch nicht eingetragen */
  ready: boolean | null
  onSaved: () => void
}

/** Teil des Konto-Dialogs für Microsoft-Konten: anmelden, danach legt Mailbox das Konto selbst an (kein Passwort). */
export function MsAccountPart({ address, label, ready, onSaved }: Props) {
  const { t } = useTranslation("mailbox")
  const s = useMsSignIn()
  const [err, setErr] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const used = useRef<string | null>(null)

  useEffect(() => {
    const f = s.flow
    if (s.state !== "done" || !f || used.current === f.flow_id) return
    used.current = f.flow_id                       // ein Vorgang ergibt genau ein Konto
    setSaving(true); setErr(null)
    mailApi.msCreate(f.flow_id, address, label)
      .then(() => onSaved())
      .catch((e) => setErr(errorCode(e) === "exists" ? t("ms.err.exists") : e instanceof Error ? e.message : String(e)))
      .finally(() => setSaving(false))
  }, [s.state, s.flow, address, label, onSaved, t])

  if (ready === false) return <p className="text-xs text-amber-200" data-mbx-ms-off="1">{t("ms.err.notConfigured")}</p>
  if (!address.includes("@")) return <p className="text-xs text-[#9aa7bc]">{t("ms.needAddress")}</p>
  return (
    <div className="space-y-2">
      <p className="text-[11px] text-[#9aa7bc]">{t("ms.explain")}</p>
      <MsSignInView state={s.state} flow={s.flow} errKey={s.errKey} detail={s.detail} onStart={() => void s.start()} />
      {saving && <p className="text-xs text-[#9aa7bc]">{t("ms.saving")}</p>}
      {err && <p className="text-xs text-rose-300" data-mbx-error="1">{err}</p>}
    </div>
  )
}
