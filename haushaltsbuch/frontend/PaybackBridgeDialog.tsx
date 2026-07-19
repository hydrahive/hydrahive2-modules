import { useEffect, useRef, useState } from "react"
import { CheckCircle2, Clipboard, Download, ShieldAlert } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage } from "./api"
import { loyaltyApi } from "./loyaltyApi"
import type { LoyaltyConnection, PaybackBridgeStartResult } from "./loyaltyTypes"
import { Button, ErrorState } from "./ui"

function downloadBase64Zip(filename: string, base64: string) {
  const binary = atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index)
  const blobUrl = URL.createObjectURL(new Blob([bytes], { type: "application/zip" }))
  const link = document.createElement("a")
  link.href = blobUrl
  link.download = filename.replace(/[^A-Za-z0-9._-]/g, "_") || "hydrahive-payback-bridge.zip"
  link.click()
  URL.revokeObjectURL(blobUrl)
}

function remainingLabel(expiresAt: string, now: number) {
  const seconds = Math.max(0, Math.ceil((new Date(expiresAt).getTime() - now) / 1000))
  const minutes = Math.floor(seconds / 60)
  return `${minutes}:${String(seconds % 60).padStart(2, "0")} Min.`
}

export function PaybackBridgeDialog({ onClose, onConsumed }: {
  onClose: () => void
  onConsumed: (connection?: LoyaltyConnection) => void
}) {
  const [accepted, setAccepted] = useState(false)
  const [flow, setFlow] = useState<PaybackBridgeStartResult>()
  const [status, setStatus] = useState<"pending" | "consumed" | "expired">("pending")
  const [busy, setBusy] = useState(false)
  const [copied, setCopied] = useState(false)
  const [packageInfo, setPackageInfo] = useState<{ filename: string; sha256: string }>()
  const [error, setError] = useState<unknown>()
  const [now, setNow] = useState(Date.now())
  const consumedDelivered = useRef(false)

  useEffect(() => {
    if (!flow || status !== "pending") return
    const tick = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(tick)
  }, [flow, status])

  useEffect(() => {
    if (!flow || status !== "pending") return
    let active = true
    async function poll() {
      try {
        const result = await loyaltyApi.paybackBridgeStatus(flow!.flow_id)
        if (!active) return
        setStatus(result.status)
        setError(undefined)
        if (result.status === "consumed" && !consumedDelivered.current) {
          consumedDelivered.current = true
          onConsumed(result.connection)
        }
      } catch (cause) {
        if (active) setError(cause)
      }
    }
    void poll()
    const timer = window.setInterval(() => void poll(), 2000)
    return () => { active = false; window.clearInterval(timer) }
  }, [flow, onConsumed, status])

  async function downloadExtension() {
    setBusy(true); setError(undefined)
    try {
      const extension = await loyaltyApi.paybackExtensionPackage()
      downloadBase64Zip(extension.filename, extension.base64)
      setPackageInfo({ filename: extension.filename, sha256: extension.sha256 })
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }

  async function start() {
    if (!accepted) return
    setBusy(true); setError(undefined); setCopied(false); consumedDelivered.current = false
    try {
      const result = await loyaltyApi.startPaybackBridge()
      setFlow(result); setStatus("pending"); setNow(Date.now())
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }

  async function copyCode() {
    if (!flow) return
    try {
      await navigator.clipboard.writeText(flow.pairing_code)
      setCopied(true); setError(undefined)
    } catch (cause) { setError(cause) }
  }

  const expiredLocally = flow ? new Date(flow.expires_at).getTime() <= now : false
  const effectiveStatus = status === "pending" && expiredLocally ? "expired" : status
  const origin = window.location.origin

  return <AdminDialog
    title="PAYBACK per Browser importieren"
    eyebrow="Haushaltsbuch · Manuelle read-only Bridge"
    icon={<ShieldAlert size={16} />}
    maxWidthClass="max-w-3xl"
    onClose={busy ? undefined : onClose}
    footer={<>
      <Button onClick={onClose} disabled={busy}>{effectiveStatus === "consumed" ? "Schließen" : "Abbrechen"}</Button>
      {!flow && <Button tone="primary" disabled={!accepted || busy} onClick={start}>{busy ? "Wird vorbereitet …" : "Einmalcode erzeugen"}</Button>}
      {flow && effectiveStatus === "expired" && <Button tone="primary" disabled={busy} onClick={start}>{busy ? "Wird erneuert …" : "Neuen Einmalcode erzeugen"}</Button>}
    </>}
  >
    <div className="grid gap-4">
      <div className="rounded border border-amber-400/35 bg-amber-400/10 p-3 text-xs text-amber-100">
        <strong>Experimentell, manuell und ausschließlich lesend.</strong>
        <p className="mt-1">Die Erweiterung liest nur die Daten, die du in deinem angemeldeten PAYBACK-Webkonto öffnest. Passwort, Cookies und PAYBACK-Sitzung bleiben im Browser. HydraHive aktiviert keine Coupons und löst keine Punkte ein.</p>
      </div>
      {error !== undefined && <ErrorState error={errorMessage(error)} />}

      <label className="flex cursor-pointer items-start gap-3 rounded border border-[#33425a] p-3 text-xs text-[#b5c1d2]">
        <input type="checkbox" className="mt-0.5" checked={accepted} disabled={Boolean(flow)} onChange={(event) => setAccepted(event.target.checked)} />
        <span><strong>Ich akzeptiere das experimentelle Risiko ausdrücklich.</strong><br /><span className="text-[#8d9ab0]">PAYBACK unterstützt diese Browser-Bridge nicht offiziell; sichtbare Seitenstrukturen können sich ändern.</span></span>
      </label>

      <ol className="grid gap-4 text-sm text-[#d4deeb]">
        <li>
          <strong>1. Erweiterung herunterladen und entpacken.</strong>
          <p className="mt-1 text-xs text-[#8d9ab0]">Das ZIP wird authentifiziert von dieser HydraHive-Installation geladen. Entpacke es in einen dauerhaft verfügbaren Ordner.</p>
          <Button className="mt-2" disabled={!accepted || busy} onClick={downloadExtension}><Download size={13} className="mr-1 inline" />{busy ? "ZIP wird geladen …" : "Extension-ZIP laden"}</Button>
          {packageInfo && <p className="mt-2 break-all text-[11px] text-emerald-200">Geladen: {packageInfo.filename}<br />SHA-256: <code>{packageInfo.sha256}</code></p>}
        </li>
        <li>
          <strong>2. Als entpackte Chromium-Erweiterung installieren.</strong>
          <p className="mt-1 text-xs text-[#8d9ab0]">Öffne <code>chrome://extensions</code>, aktiviere den Entwicklermodus, wähle „Entpackte Erweiterung laden“ und den entpackten Ordner.</p>
        </li>
        <li>
          <strong>3. Einmalcode in der Erweiterung verwenden.</strong>
          {!flow ? <p className="mt-1 text-xs text-[#8d9ab0]">Installiere die Erweiterung zuerst. Erzeuge danach den nur zehn Minuten gültigen Code.</p> : <div className="mt-2 grid gap-2 rounded border border-cyan-400/25 bg-cyan-400/5 p-3">
            <div className="flex flex-wrap items-center gap-2">
              <code className="min-w-0 flex-1 break-all rounded bg-[#080d15] px-3 py-2 text-xs text-cyan-100">{flow.pairing_code}</code>
              <Button onClick={copyCode}><Clipboard size={13} className="mr-1 inline" />{copied ? "Kopiert" : "Code kopieren"}</Button>
            </div>
            <p className="text-xs text-[#9eacc0]">HydraHive-Origin: <code>{origin}</code><br />Importpfad: <code>{flow.import_path}</code></p>
            <p className={`text-xs font-bold ${effectiveStatus === "expired" ? "text-rose-200" : "text-amber-200"}`}>{effectiveStatus === "expired" ? "Der Einmalcode ist abgelaufen." : `Gültig bis ${new Date(flow.expires_at).toLocaleTimeString("de-DE")} Uhr · noch ${remainingLabel(flow.expires_at, now)}`}</p>
          </div>}
        </li>
        <li>
          <strong>4. PAYBACK-Seiten erfassen und Import bestätigen.</strong>
          <p className="mt-1 text-xs text-[#8d9ab0]">Öffne in PAYBACK nacheinander Übersicht, Punktekonto und Coupons. Prüfe die Vorschau der Erweiterung und bestätige dort bewusst den Versand.</p>
        </li>
      </ol>

      {flow && effectiveStatus === "pending" && <div className="rounded border border-cyan-400/25 bg-cyan-400/5 p-3 text-xs text-cyan-100"><span className="mr-2 inline-block h-2 w-2 animate-pulse rounded-full bg-cyan-300" />Warte auf den einmaligen Browser-Import … Der Status wird automatisch geprüft.</div>}
      {effectiveStatus === "consumed" && <div className="flex items-start gap-2 rounded border border-emerald-400/30 bg-emerald-400/10 p-3 text-sm text-emerald-100"><CheckCircle2 size={18} className="mt-0.5 shrink-0" /><div><strong>Import abgeschlossen.</strong><p className="mt-1 text-xs opacity-85">Verbindung und PAYBACK-Daten wurden aktualisiert. Der Einmalcode ist verbraucht und kann nicht erneut verwendet werden.</p></div></div>}
    </div>
  </AdminDialog>
}
