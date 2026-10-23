import { useEffect, useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import { mailApi, type Account } from "./api"
import { MsSignInView } from "./MsSignInView"
import { useMsSignIn } from "./useMsSignIn"

/** In den Kontoeinstellungen eines Microsoft-Kontos: neu anmelden (z. B. nach „Anmeldung abgelaufen“). Archiv bleibt. */
export function MsReauth({ account, onDone }: { account: Account; onDone: () => void }) {
  const { t } = useTranslation("mailbox")
  const s = useMsSignIn()
  const [err, setErr] = useState<string | null>(null)
  const used = useRef<string | null>(null)

  useEffect(() => {
    const f = s.flow
    if (s.state !== "done" || !f || used.current === f.flow_id) return
    used.current = f.flow_id
    mailApi.msReauth(account.id, f.flow_id).then(() => onDone()).catch((e) => setErr(e instanceof Error ? e.message : String(e)))
  }, [s.state, s.flow, account.id, onDone])

  return (
    <section className="space-y-2 border-t border-[#2a364b] pt-3" data-mbx-ms-reauth="1">
      <h3 className="text-xs font-semibold text-[#e8eef8]">{t("ms.reauthTitle")}</h3>
      {account.status === "auth_failed" && <p className="text-xs text-rose-300">{t("ms.expiredAccount")}</p>}
      <MsSignInView state={s.state} flow={s.flow} errKey={s.errKey} detail={s.detail} onStart={() => void s.start()} />
      {err && <p className="text-xs text-rose-300">{err}</p>}
    </section>
  )
}
