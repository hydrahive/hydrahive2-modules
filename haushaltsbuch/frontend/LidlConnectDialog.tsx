import { useState, type FormEvent } from "react"
import { ExternalLink, ShieldAlert } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage } from "./api"
import { loyaltyApi } from "./loyaltyApi"
import type { LidlAuthStartResult, LoyaltyConnection } from "./loyaltyTypes"
import { Button, ErrorState, Field, Input, Textarea } from "./ui"

function safeAuthorizationUrl(value: string): string | undefined {
  try {
    const url = new URL(value)
    if (url.origin !== "https://accounts.lidl.com") return undefined
    if (url.pathname !== "/connect/authorize" || url.username || url.password || url.hash) return undefined
    return value
  } catch {
    return undefined
  }
}

function validCallbackUrl(value: string): boolean {
  try {
    const url = new URL(value.trim())
    if (url.protocol !== "com.lidlplus.app:" || url.hostname !== "callback") return false
    if (!["", "/"].includes(url.pathname) || url.username || url.password || url.port || url.hash) return false
    const keys = [...url.searchParams.keys()]
    if (keys.some((key) => !["code", "state", "session_state", "iss"].includes(key))) return false
    if (url.searchParams.getAll("code").length !== 1 || !url.searchParams.get("code")) return false
    if (url.searchParams.getAll("state").length !== 1 || !url.searchParams.get("state")) return false
    const issuer = url.searchParams.getAll("iss")
    return issuer.length === 0 || (issuer.length === 1 && issuer[0] === "https://accounts.lidl.com")
  } catch {
    return false
  }
}

export function LidlConnectDialog({ onClose, onConnected }: {
  onClose: () => void
  onConnected: (connection: LoyaltyConnection) => void
}) {
  const [accepted, setAccepted] = useState(false)
  const [flow, setFlow] = useState<LidlAuthStartResult>()
  const [callbackUrl, setCallbackUrl] = useState("")
  const [alias, setAlias] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const authorizationUrl = flow && safeAuthorizationUrl(flow.authorization_url)
  const callbackComplete = validCallbackUrl(callbackUrl)

  async function start() {
    if (!accepted) return
    setBusy(true); setError(undefined)
    try {
      const result = await loyaltyApi.startLidlAuth()
      if (!safeAuthorizationUrl(result.authorization_url)) {
        throw new Error("Das Backend hat keine zulässige Lidl-Anmelde-URL geliefert.")
      }
      setFlow(result); setCallbackUrl("")
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }

  async function complete(event: FormEvent) {
    event.preventDefault()
    if (!flow || !callbackComplete) return
    setBusy(true); setError(undefined)
    try {
      const connection = await loyaltyApi.completeLidlAuth({
        flow_token: flow.flow_token,
        callback_url: callbackUrl.trim(),
        ...(alias.trim() ? { alias: alias.trim() } : {}),
        visibility: "owner",
      })
      onConnected(connection)
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }

  return <AdminDialog
    title="Lidl Plus experimentell verbinden"
    eyebrow="Haushaltsbuch · Inoffizieller Testconnector"
    icon={<ShieldAlert size={16} />}
    maxWidthClass="max-w-2xl"
    onClose={busy ? undefined : onClose}
    footer={<><Button onClick={onClose} disabled={busy}>Abbrechen</Button>{!flow
      ? <Button tone="primary" disabled={!accepted || busy} onClick={start}>{busy ? "Wird gestartet …" : "Sicheren Browserflow starten"}</Button>
      : <Button tone="primary" type="submit" form="lidl-connect-form" disabled={!callbackComplete || busy}>{busy ? "Wird verbunden …" : "Verbindung abschließen"}</Button>}</>}
  >
    <form id="lidl-connect-form" onSubmit={complete} className="grid gap-4">
      <div className="rounded border border-amber-400/35 bg-amber-400/10 p-3 text-xs text-amber-100">
        <strong>Experimentell, inoffiziell und ausschließlich read-only.</strong>
        <p className="mt-1">Die nicht öffentliche Lidl-Schnittstelle kann sich ändern oder den Zugriff blockieren. HydraHive aktiviert keine Coupons und verändert weder Lidl-Profil noch Einkäufe.</p>
      </div>
      <div className="rounded border border-cyan-400/25 bg-cyan-400/5 p-3 text-xs text-cyan-100">
        Passwort und MFA-Code gibst du nur direkt bei Lidl ein. Trage hier niemals Passwort, MFA-Code oder Refresh-Token ein.
      </div>
      {error !== undefined && <ErrorState error={errorMessage(error)} />}
      {!flow ? <label className="flex cursor-pointer items-start gap-3 rounded border border-[#33425a] p-3 text-xs text-[#b5c1d2]">
        <input type="checkbox" className="mt-0.5" checked={accepted} onChange={(event) => setAccepted(event.target.checked)} />
        <span><strong>Ich akzeptiere das experimentelle Risiko ausdrücklich.</strong><br /><span className="text-[#8d9ab0]">Mir ist bewusst, dass dies keine offizielle Lidl-Integration ist und ohne Stabilitäts- oder Zulässigkeitszusage bereitgestellt wird.</span></span>
      </label> : <>
        <ol className="grid gap-3 text-sm text-[#d4deeb]">
          <li><strong>1. Lidl-Anmeldung öffnen.</strong><p className="mt-1 text-xs text-[#8d9ab0]">Der Link stammt aus diesem gestarteten Backend-Flow und öffnet sich erst durch deinen Klick in einem neuen Tab.</p>{authorizationUrl && <a href={authorizationUrl} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex items-center gap-1 rounded border border-cyan-400/40 bg-cyan-400/15 px-3 py-2 text-xs font-bold text-cyan-200"><ExternalLink size={13} />Direkt bei Lidl anmelden</a>}</li>
          <li><strong>2. Vollständige Callback-URL kopieren.</strong><p className="mt-1 text-xs text-[#8d9ab0]">Nach dem Redirect kann der Browser die Seite eventuell nicht öffnen. Kopiere dann aus seiner Adresszeile die komplette Adresse ab <code>com.lidlplus.app://callback?...</code> — einschließlich aller Parameter.</p></li>
          <li><strong>3. Verbindung abschließen.</strong><p className="mt-1 text-xs text-[#8d9ab0]">Der Flow läuft um {new Date(flow.expires_at).toLocaleTimeString("de-DE")} Uhr ab und ist nur einmal nutzbar.</p></li>
        </ol>
        <Field label="Komplette Callback-URL" hint="Nur die Adresse aus der Browser-Adresszeile; keine Zugangsdaten."><Textarea required rows={4} spellCheck={false} autoComplete="off" value={callbackUrl} onChange={(event) => setCallbackUrl(event.target.value)} placeholder="com.lidlplus.app://callback/?code=…&state=…" /></Field>
        {callbackUrl.trim() && !callbackComplete && <p className="text-xs text-amber-200">Die Callback-Adresse ist noch nicht vollständig oder hat nicht das erwartete Lidl-Format. Sie muss mit <code>com.lidlplus.app://callback</code> beginnen und <code>code</code> sowie <code>state</code> enthalten.</p>}
        <Field label="Alias (optional)"><Input maxLength={120} value={alias} onChange={(event) => setAlias(event.target.value)} placeholder="z. B. Mein Lidl Plus" /></Field>
        <p className="text-xs text-[#718097]">Die neue Verbindung ist nur für dich sichtbar. Synchronisiert werden ausschließlich digitale Belege und deren read-only Details.</p>
      </>}
    </form>
  </AdminDialog>
}
