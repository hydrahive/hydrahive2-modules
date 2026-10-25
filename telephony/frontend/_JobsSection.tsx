import { Loader2 } from "lucide-react"
import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { DialPanel } from "./DialPanel"
import { telephonyApi } from "./api"
import type { Connection } from "./types"

/** Reiter „Telefonaufträge“: lädt die Verbindung und zeigt „Anrufen“ (Etappe 3a). */
export function JobsSection({ onSetup }: { onSetup: () => void }) {
  const { t } = useTranslation("voip")
  const [conn, setConn] = useState<Connection | null>(null)
  useEffect(() => { void telephonyApi.connection().then(setConn).catch(() => setConn({ configured: false, status: "not_configured" })) }, [])
  if (!conn) return <div role="status" className="flex min-h-40 items-center justify-center text-zinc-500"><Loader2 size={17} className="animate-spin" /></div>
  if (!conn.configured) {
    return (
      <section className="rounded-xl border border-zinc-800 bg-zinc-900/40 p-5 text-sm text-zinc-300" data-voip-jobs-setup="1">
        <p>{t("dial.needs_connection")}</p>
        <button type="button" onClick={onSetup} className="mt-3 rounded-lg border border-zinc-700 px-3 py-2 text-zinc-200 hover:bg-zinc-800">
          {t("setup_action")}
        </button>
      </section>
    )
  }
  return <DialPanel conn={conn} />
}
