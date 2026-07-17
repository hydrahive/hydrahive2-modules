import { useState, type FormEvent } from "react"
import { Home, KeyRound } from "lucide-react"
import { haushaltsbuchApi, errorMessage, isConflict } from "./api"
import type { Household } from "./types"
import { Button, ErrorState, Field, Input, Select, panel } from "./ui"

export function HouseholdSetup({ onReady }: { onReady: (household: Household) => void }) {
  const [mode, setMode] = useState<"create" | "join">("create")
  const [name, setName] = useState("Unser Haushalt")
  const [currency, setCurrency] = useState("EUR")
  const [timezone, setTimezone] = useState(Intl.DateTimeFormat().resolvedOptions().timeZone || "Europe/Berlin")
  const [defaults, setDefaults] = useState(true)
  const [code, setCode] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()

  async function submit(event: FormEvent) {
    event.preventDefault(); setBusy(true); setError(undefined)
    try {
      if (mode === "create") await haushaltsbuchApi.createHousehold({ name: name.trim(), base_currency: currency, timezone, create_default_categories: defaults })
      else await haushaltsbuchApi.acceptInvite(code.trim())
      onReady(await haushaltsbuchApi.household())
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }

  return <div className="mx-auto grid max-w-4xl gap-4 py-8 lg:grid-cols-[1fr_1.35fr]">
    <section className={`${panel} p-6`}><Home className="text-cyan-300" size={28} /><h1 className="mt-4 text-xl font-black text-[#e8eef8]">Gemeinsam den Überblick behalten</h1><p className="mt-2 text-sm leading-6 text-[#8d9ab0]">Lege einen Haushalt an oder tritt mit einem Einladungscode bei. Finanzdaten bleiben lokal in HydraHive und werden mit allen Mitgliedern geteilt.</p><ul className="mt-5 space-y-2 text-xs text-[#b5c1d2]"><li>✓ Beträge werden exakt in Minor Units gespeichert.</li><li>✓ Änderungen sind revisionsgeschützt und auditierbar.</li><li>✓ Keine Bank- oder Cloud-Anbindung in V1.</li></ul></section>
    <form onSubmit={submit} className={`${panel} p-6`}>
      <div className="mb-5 flex rounded-[4px] border border-[#2a364b] bg-[#0b111c] p-1">
        <button type="button" onClick={() => setMode("create")} className={`flex-1 rounded px-3 py-2 text-xs font-bold ${mode === "create" ? "bg-[#1c2940] text-cyan-200" : "text-[#8d9ab0]"}`}>Haushalt anlegen</button>
        <button type="button" onClick={() => setMode("join")} className={`flex-1 rounded px-3 py-2 text-xs font-bold ${mode === "join" ? "bg-[#1c2940] text-cyan-200" : "text-[#8d9ab0]"}`}>Einladung annehmen</button>
      </div>
      {error !== undefined && <div className="mb-4"><ErrorState error={errorMessage(error)} conflict={isConflict(error)} /></div>}
      {mode === "create" ? <div className="grid gap-4">
        <Field label="Haushaltsname"><Input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></Field>
        <div className="grid gap-4 sm:grid-cols-2"><Field label="Basiswährung"><Select value={currency} onChange={(e) => setCurrency(e.target.value)}><option>EUR</option><option>USD</option><option>CHF</option><option>GBP</option></Select></Field><Field label="Zeitzone"><Input required value={timezone} onChange={(e) => setTimezone(e.target.value)} /></Field></div>
        <label className="flex items-start gap-3 rounded-[4px] border border-[#2a364b] p-3 text-sm text-[#b5c1d2]"><input type="checkbox" checked={defaults} onChange={(e) => setDefaults(e.target.checked)} className="mt-0.5" /><span><strong className="block text-[#e8eef8]">Standardkategorien anlegen</strong><span className="text-xs text-[#718097]">Gehalt, Wohnen, Lebensmittel und weitere Startkategorien.</span></span></label>
      </div> : <div className="grid gap-4"><KeyRound className="text-cyan-300" /><Field label="Einladungscode" hint="Der Code wird vom Eigentümer nur einmal angezeigt."><Input required minLength={20} autoComplete="off" value={code} onChange={(e) => setCode(e.target.value)} placeholder="Code einfügen" /></Field></div>}
      <div className="mt-6 flex justify-end"><Button type="submit" tone="primary" disabled={busy}>{busy ? "Wird eingerichtet …" : mode === "create" ? "Haushalt anlegen" : "Beitreten"}</Button></div>
    </form>
  </div>
}
