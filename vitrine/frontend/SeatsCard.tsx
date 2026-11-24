import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Info, Loader2, MonitorSmartphone } from "lucide-react"
import { vitrineApi, type SeatAction, type SeatId, type SeatsView } from "./api"
import { choiceErrors, complete, initialChoice, seatRows } from "./seats"
import { SeatsSwitch } from "./SeatsSwitch"

const box = "space-y-3 rounded-[6px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] p-4"
const field = "rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] px-2 py-1 text-sm text-[#e8eef8]"

interface ViewProps {
  v: SeatsView
  choice: Record<string, SeatId | null>
  saving: boolean
  msg: string | null
  onPick: (id: string, s: SeatId | null) => void
  onSave: () => void
  confirming?: SeatAction | null
  onAsk?: (a: SeatAction) => void
  onConfirm?: () => void
  onCancel?: () => void
}

/** Reine Anzeige (testbar ohne Browser). */
export function SeatsPanel({ v, choice, saving, msg, onPick, onSave, confirming = null, onAsk = () => {}, onConfirm = () => {},
  onCancel = () => {} }: ViewProps) {
  const { t } = useTranslation("vitrine")
  const errs = choiceErrors(v, choice)
  return (
    <section className={`${box} max-w-3xl`} data-part="seats">
      <h2 className="flex items-center gap-2 text-sm font-bold text-[#e8eef8]"><MonitorSmartphone size={15} className="text-[#69d7ff]" />{t("seats_title")}</h2>
      {v.monitor_detected && (
        <p className="rounded-[4px] border border-[#69d7ff]/40 bg-[#69d7ff]/10 p-2 text-sm text-[#cfefff]" data-hint="monitor">{t("seats_monitor_hint")}</p>
      )}
      <p className="text-xs text-[#9aa7bc]">{t("seats_intro")}</p>
      {!v.feasible && (
        <div className="space-y-1 rounded-[4px] border border-amber-400/40 bg-amber-400/10 p-2 text-sm text-amber-100" data-part="not-feasible">
          <p>{t("seats_not_feasible")}</p>
          <ul className="list-disc pl-5 text-xs">{v.reasons.map((r) => <li key={r}>{t(`seats_reason_${r}`)}</li>)}</ul>
        </div>
      )}
      {v.feasible && (
        <>
          {v.inputs_unclear && <p className="text-xs text-amber-200" data-hint="inputs">{t("seats_inputs_unclear")}</p>}
          <table className="w-full text-sm">
            <thead><tr className="text-left text-[11px] uppercase tracking-wider text-[#9aa7bc]">
              <th className="py-1 font-semibold">{t("seats_device")}</th><th className="py-1 font-semibold">{t("seats_place")}</th>
            </tr></thead>
            <tbody>
              {seatRows(v).map((r) => (
                <tr key={r.id} className="border-t border-[rgb(var(--hh-s-rand,42_54_75))]" data-device={r.id}>
                  <td className="py-1.5 pr-2 text-[#e8eef8]">
                    <span className="mr-1 text-[10px] text-[#9aa7bc]">{t(`seats_kind_${r.kind}`)}</span>{r.label}
                    {r.detail && <span className="block text-[11px] text-[#9aa7bc]">{r.detail}</span>}
                  </td>
                  <td className="py-1.5">
                    <select className={field} value={choice[r.id] ?? ""} aria-label={r.label}
                      onChange={(e) => onPick(r.id, (e.target.value || null) as SeatId | null)}>
                      <option value="">{t("seats_choose")}</option>
                      <option value="seat0">{t("seats_seat0")}</option>
                      <option value="seat1">{t("seats_seat1")}</option>
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {errs.length > 0 && <ul className="list-disc pl-5 text-xs text-amber-200">{errs.map((e) => <li key={e}>{t(e)}</li>)}</ul>}
          <div className="flex items-center gap-3">
            <button type="button" onClick={onSave} disabled={saving || errs.length > 0} data-action="save"
              className="flex items-center gap-2 rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff] disabled:opacity-40">
              {saving && <Loader2 size={13} className="animate-spin" />}{t("seats_apply")}
            </button>
            {msg && <span className="text-xs text-[#9aa7bc]">{msg}</span>}
          </div>
        </>
      )}
      {(v.feasible || v.applied || v.running) && (
        <SeatsSwitch v={v} confirming={confirming} onAsk={onAsk} onConfirm={onConfirm} onCancel={onCancel} />
      )}
      <p className="flex items-start gap-1.5 text-xs text-[#9aa7bc]" data-hint="switch"><Info size={13} className="mt-0.5 shrink-0" />{t("seats_switch_hint")}</p>
    </section>
  )
}

/** Karte „Zweiter Arbeitsplatz“: Vorschlag ansehen, ändern, „Übernehmen“ (M1); ein-/ausschalten (M2). */
export function SeatsCard() {
  const { t } = useTranslation("vitrine")
  const [v, setV] = useState<SeatsView | null>(null)
  const [choice, setChoice] = useState<Record<string, SeatId | null>>({})
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState<string | null>(null)
  const [confirming, setConfirming] = useState<SeatAction | null>(null)
  const load = useCallback(async (keepChoice = false) => {
    try { const x = await vitrineApi.seats(); setV(x); if (!keepChoice) setChoice(initialChoice(x)) }
    catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
  }, [])
  useEffect(() => { void load() }, [load])
  // Während eines Laufs alle 3 s nachfragen – nur solange running
  const running = v?.running ?? null
  useEffect(() => {
    if (!running) return
    const id = window.setInterval(() => { void load(true) }, 3000)
    return () => window.clearInterval(id)
  }, [running, load])

  async function switchSeats() {
    const a = confirming
    setConfirming(null)
    if (!a) return
    setMsg(null)
    try { await vitrineApi.seatsSwitch(a) } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
    await load(true)
  }

  async function save() {
    if (!v) return
    setSaving(true); setMsg(null)
    try { await vitrineApi.saveSeats(complete(choice)); setMsg(t("seats_saved")); await load() }
    catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
    finally { setSaving(false) }
  }

  if (!v) return <p className="text-sm text-[#9aa7bc]">{msg ?? t("seats_loading")}</p>
  return <SeatsPanel v={v} choice={choice} saving={saving} msg={msg}
    onPick={(id, s) => setChoice((c) => ({ ...c, [id]: s }))} onSave={() => void save()}
    confirming={confirming} onAsk={setConfirming} onConfirm={() => void switchSeats()} onCancel={() => setConfirming(null)} />
}
