import { useEffect, useState } from "react"
import { Clock3, Save } from "lucide-react"
import { useTranslation } from "react-i18next"
import { ticketsApi, type SlaProfile } from "./api"

export function SlaProfileSettings() {
  const { t } = useTranslation("tickets")
  const [profile, setProfile] = useState<SlaProfile | null>(null)
  const [open, setOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  useEffect(() => { void ticketsApi.slaProfiles().then((items) => setProfile(items.find((item) => item.id === "default") ?? null)).catch(() => setProfile(null)) }, [])
  if (!profile) return null
  const current = profile
  async function save() {
    setBusy(true)
    try {
      const hours = {
        urgent_response_hours: current.urgent_response_hours,
        urgent_resolution_hours: current.urgent_resolution_hours,
        high_response_hours: current.high_response_hours,
        high_resolution_hours: current.high_resolution_hours,
        normal_response_hours: current.normal_response_hours,
        normal_resolution_hours: current.normal_resolution_hours,
        low_response_hours: current.low_response_hours,
        low_resolution_hours: current.low_resolution_hours,
      }
      setProfile(await ticketsApi.updateSlaProfile(current.id, hours))
    } finally { setBusy(false) }
  }
  const field = (key: keyof SlaProfile, label: string) => <label className="text-[10px] text-[#8d9ab0]">{label}<input type="number" min={1} value={Number(current[key])} onChange={(event) => setProfile({ ...current, [key]: Number(event.target.value) })} className="mt-1 block w-full rounded-[5px] border border-[#253247] bg-[#0d1420] px-2 py-1.5 text-xs text-[#c8d2df]" /></label>
  return <section className="shrink-0 border-t border-[#1f2a3b] bg-[#0c131e] p-3"><button onClick={() => setOpen((value) => !value)} className="flex w-full items-center gap-2 text-left text-xs font-semibold text-[#a9b5c6] hover:text-[#e8eef8]"><Clock3 size={14} className="text-[#69d7ff]" />{t("slaProfiles")}</button>{open && <div className="mt-3 space-y-3"><p className="text-[10px] leading-relaxed text-[#607188]">{t("slaProfilesHint")}</p><div className="grid grid-cols-2 gap-2">{field("urgent_response_hours", t("priority.urgent"))}{field("urgent_resolution_hours", t("resolution"))}{field("high_response_hours", t("priority.high"))}{field("high_resolution_hours", t("resolution"))}{field("normal_response_hours", t("priority.normal"))}{field("normal_resolution_hours", t("resolution"))}{field("low_response_hours", t("priority.low"))}{field("low_resolution_hours", t("resolution"))}</div><button disabled={busy} onClick={() => void save()} className="inline-flex items-center gap-1.5 rounded-[5px] border border-[#2b4058] px-2.5 py-1.5 text-[10px] text-[#a8dff2] hover:border-[#69d7ff]/60 disabled:opacity-40"><Save size={12} />{t("save")}</button></div>}</section>
}
