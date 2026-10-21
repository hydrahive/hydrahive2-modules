import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Bluetooth } from "lucide-react"
import { vitrineApi, type BtView } from "./api"
import { BluetoothList } from "./BluetoothList"

/** S7: Karte „Bluetooth“ – alle 2 s aktuell; Koppeln, Entfernen (nur hier, nicht am Kiosk). */
export function BluetoothCard() {
  const { t } = useTranslation("vitrine")
  const [v, setV] = useState<BtView | null>(null)
  const [err, setErr] = useState<string | null>(null)

  const load = useCallback(() => { vitrineApi.bluetooth().then(setV).catch(() => {}) }, [])
  useEffect(() => {
    load()
    const id = window.setInterval(load, 2000)
    return () => window.clearInterval(id)
  }, [load])

  async function run(fn: () => Promise<unknown>) {
    setErr(null)
    try { await fn() } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    load()
  }

  return (
    <section className="space-y-2">
      <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><Bluetooth size={14} className="text-[#69d7ff]" />{t("bt_title")}</h2>
      <p className="text-xs text-[#718097]">{t("bt_hint")}</p>
      {err && <p className="text-xs text-rose-300">{err}</p>}
      {v && <BluetoothList v={v} onScan={() => void run(vitrineApi.btScan)}
        onPair={(a) => void run(() => vitrineApi.btPair(a))}
        onRemove={(a) => { if (window.confirm(t("bt_remove_confirm"))) void run(() => vitrineApi.btRemove(a)) }} />}
    </section>
  )
}
