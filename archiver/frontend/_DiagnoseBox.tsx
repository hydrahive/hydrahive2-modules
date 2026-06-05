import { useState } from "react"
import { Activity, AlertTriangle, Loader2 } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { archiverApi, type Drive, type SmartResult } from "./api"

interface Props {
  drive: Drive | null
}

export function DiagnoseBox({ drive }: Props) {
  const [smartResult, setSmartResult] = useState<SmartResult | null>(null)
  const [smartLoading, setSmartLoading] = useState(false)
  const [dmesgLines, setDmesgLines] = useState<string[] | null>(null)
  const [dmesgLoading, setDmesgLoading] = useState(false)

  const deviceName = drive ? drive.device.replace("/dev/", "") : null

  async function handleSmart() {
    if (!deviceName) return
    setSmartLoading(true)
    setSmartResult(null)
    try {
      const r = await archiverApi.smart(deviceName)
      setSmartResult(r)
    } catch (e) {
      setSmartResult({ health: "UNKNOWN", raw: String(e), available: false })
    } finally {
      setSmartLoading(false)
    }
  }

  async function handleDmesg() {
    if (!deviceName) return
    setDmesgLoading(true)
    setDmesgLines(null)
    try {
      const { lines } = await archiverApi.dmesg(deviceName)
      setDmesgLines(lines)
    } catch (e) {
      setDmesgLines([`Fehler: ${String(e)}`])
    } finally {
      setDmesgLoading(false)
    }
  }

  const healthColor =
    smartResult?.health === "PASSED" ? "text-emerald-400"
    : smartResult?.health === "FAILED" ? "text-rose-400"
    : "text-zinc-400"

  return (
    <CollapsibleBox
      boxId="archiver.diagnose"
      title="Diagnose"
      icon={<Activity size={14} />}
      color="59,130,246"
      defaultCollapsed
    >
      <div className="p-4 space-y-4">
        {!drive ? (
          <p className="text-xs text-zinc-600">Kein Laufwerk ausgewählt.</p>
        ) : (
          <>
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSmart}
                  disabled={smartLoading}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-500/10 border border-blue-500/20 text-blue-300 hover:bg-blue-500/20 disabled:opacity-40 transition-colors text-xs"
                >
                  {smartLoading ? <Loader2 size={11} className="animate-spin" /> : <Activity size={11} />}
                  SMART prüfen
                </button>
                {smartResult && (
                  <span className={`text-xs font-semibold ${healthColor}`}>
                    {smartResult.health}
                    {!smartResult.available && " (nicht verfügbar)"}
                  </span>
                )}
              </div>
              {smartResult?.raw && (
                <pre className="bg-black/30 rounded-lg p-2 text-[10px] font-mono text-zinc-400 h-36 overflow-y-auto whitespace-pre-wrap break-all">
                  {smartResult.raw}
                </pre>
              )}
            </div>

            <div className="space-y-2">
              <button
                onClick={handleDmesg}
                disabled={dmesgLoading}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-300 hover:bg-amber-500/20 disabled:opacity-40 transition-colors text-xs"
              >
                {dmesgLoading ? <Loader2 size={11} className="animate-spin" /> : <AlertTriangle size={11} />}
                Fehlerlog (dmesg)
              </button>
              {dmesgLines !== null && (
                <pre className="bg-black/30 rounded-lg p-2 text-[10px] font-mono h-36 overflow-y-auto whitespace-pre-wrap break-all">
                  {dmesgLines.length === 0
                    ? <span className="text-zinc-600">Keine Treffer im dmesg-Log.</span>
                    : dmesgLines.map((l, i) => (
                        <div key={i} className={l.toLowerCase().includes("error") ? "text-rose-400" : "text-zinc-400"}>
                          {l}
                        </div>
                      ))
                  }
                </pre>
              )}
            </div>
          </>
        )}
      </div>
    </CollapsibleBox>
  )
}
