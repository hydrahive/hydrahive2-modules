import { Bell, BellRing, Plus, Trash2 } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { cryptoApi } from "../api"
import { AlertForm } from "../components/AlertForm"
import type { Alert, AlertEvent } from "../types"
import { EmptyHint } from "../components/EmptyHint"

const C = "105 215 255"

function kindLabel(t: (k: string) => string, a: Alert): string {
  const target = a.kind.startsWith("portfolio") ? t("al_portfolio") : (a.symbol || a.coin_id)
  return `${target} · ${t(`al_kind_${a.kind}`)} ${a.threshold}`
}

export function AlertsView() {
  const { t } = useTranslation("cryptoboard")
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [events, setEvents] = useState<AlertEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [adding, setAdding] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [a, ev] = await Promise.all([cryptoApi.alerts(), cryptoApi.alertEvents(50)])
      setAlerts(a)
      setEvents(ev.events)
      if (ev.unseen > 0) await cryptoApi.markAlertsSeen()
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function toggle(a: Alert) {
    await cryptoApi.toggleAlert(a.id, a.active === 0)
    await load()
  }

  async function del(id: number) {
    await cryptoApi.deleteAlert(id)
    await load()
  }

  if (loading && alerts.length === 0 && events.length === 0) {
    return <p className="p-8 text-center text-sm text-[#9aa7bc]">{t("loading")}</p>
  }

  return (
    <div className="p-5 space-y-4 max-w-4xl mx-auto">
      {adding ? (
        <div className="rounded-xl border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-4">
          <h3 className="text-sm font-semibold text-[#e8eef8] mb-3">{t("al_new_title")}</h3>
          <AlertForm onSaved={() => { setAdding(false); void load() }} onCancel={() => setAdding(false)} />
        </div>
      ) : (
        <button onClick={() => setAdding(true)}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[rgb(var(--hh-s-innen,17_24_39))] text-sm text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] transition-colors">
          <Plus size={15} /> {t("al_new_title")}
        </button>
      )}

      {/* Aktive Regeln */}
      <CollapsibleBox boxId="cryptoboard-alert-rules" color={C} icon={<Bell size={14} />} title={t("al_rules")}>
        <div className="box-b">
          {alerts.length === 0 ? (
            <EmptyHint text={t("al_empty")} />
          ) : (
            <ul className="divide-y divide-[rgb(var(--hh-s-rand,42_54_75))]">
              {alerts.map((a) => (
                <li key={a.id} className="flex items-center gap-3 py-2.5 group">
                  <button onClick={() => toggle(a)} aria-label="toggle"
                    className={`shrink-0 ${a.active ? "text-emerald-400" : "text-[#9aa7bc]"}`}>
                    {a.active ? <BellRing size={16} /> : <Bell size={16} />}
                  </button>
                  <span className={`text-sm ${a.active ? "text-[#e8eef8]" : "text-[#9aa7bc]"}`}>{kindLabel(t, a)}</span>
                  <button onClick={() => del(a.id)} aria-label="delete"
                    className="ml-auto p-1 text-[#9aa7bc] hover:text-rose-400 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CollapsibleBox>

      {/* Ausgelöste Benachrichtigungen */}
      <CollapsibleBox boxId="cryptoboard-alert-events" color={C} icon={<BellRing size={14} />} title={t("al_history")}>
        <div className="box-b">
          {events.length === 0 ? (
            <p className="py-5 text-center text-sm text-[#9aa7bc]">{t("al_history_empty")}</p>
          ) : (
            <ul className="divide-y divide-[rgb(var(--hh-s-rand,42_54_75))]">
              {events.map((e) => (
                <li key={e.id} className="flex items-center gap-3 py-2.5">
                  <BellRing size={14} className="text-amber-400 shrink-0" />
                  <span className="text-sm text-[#e8eef8]">{e.message}</span>
                  <span className="ml-auto text-[10px] text-[#9aa7bc] tabular-nums whitespace-nowrap">{e.created_at.slice(0, 16).replace("T", " ")}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </CollapsibleBox>
    </div>
  )
}
