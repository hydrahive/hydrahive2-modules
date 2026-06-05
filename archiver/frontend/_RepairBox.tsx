import { useRef, useState } from "react"
import { Wrench, Loader2, CheckCircle, XCircle } from "lucide-react"
import { CollapsibleBox } from "@/shared/CollapsibleBox"
import { archiverApi, type Drive, type RepairUpdate } from "./api"

interface Props {
  drive: Drive | null
}

type RepairStatus = "idle" | "running" | "done" | "failed"

export function RepairBox({ drive }: Props) {
  const [status, setStatus] = useState<RepairStatus>("idle")
  const [lines, setLines] = useState<string[]>([])
  const logRef = useRef<HTMLPreElement>(null)
  const stopRef = useRef<(() => void) | null>(null)

  const deviceName = drive ? drive.device.replace("/dev/", "") : null

  async function startRepair(tool: "ntfsfix" | "fsck") {
    if (!deviceName) return
    setStatus("running")
    setLines([])

    try {
      await archiverApi.startRepair(deviceName, tool)
    } catch (e) {
      setLines([`Fehler beim Start: ${String(e)}`])
      setStatus("failed")
      return
    }

    stopRef.current = archiverApi.streamRepair(
      deviceName,
      (data: RepairUpdate) => {
        setLines(data.lines)
        if (data.status === "done") setStatus("done")
        else if (data.status === "failed" || data.status === "not_found") setStatus("failed")
        // Auto-scroll
        if (logRef.current) {
          logRef.current.scrollTop = logRef.current.scrollHeight
        }
      },
      () => { /* onDone already handled via status */ },
    )
  }

  function handleStop() {
    stopRef.current?.()
    setStatus("idle")
  }

  const ntfsVisible = drive && (drive.fstype === "ntfs" || drive.fstype === "ntfs3")
  const fsckVisible = drive && (drive.fstype?.startsWith("ext") || drive.fstype === "")

  const statusIcon =
    status === "running" ? <Loader2 size={13} className="text-violet-400 animate-spin" />
    : status === "done" ? <CheckCircle size={13} className="text-emerald-400" />
    : status === "failed" ? <XCircle size={13} className="text-rose-400" />
    : null

  return (
    <CollapsibleBox
      boxId="archiver.repair"
      title="Reparatur"
      icon={<Wrench size={14} />}
      color="239,68,68"
      defaultCollapsed
    >
      <div className="p-4 space-y-3">
        {!drive ? (
          <p className="text-xs text-zinc-600">Kein Laufwerk ausgewählt.</p>
        ) : (
          <>
            <p className="text-xs text-zinc-500">
              Laufwerk wird vor der Reparatur automatisch ausgehängt.
            </p>
            <div className="flex items-center gap-2 flex-wrap">
              {ntfsVisible && (
                <button
                  onClick={() => startRepair("ntfsfix")}
                  disabled={status === "running"}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-500/10 border border-orange-500/20 text-orange-300 hover:bg-orange-500/20 disabled:opacity-40 transition-colors text-xs"
                >
                  <Wrench size={11} />
                  ntfsfix
                </button>
              )}
              {fsckVisible && (
                <button
                  onClick={() => startRepair("fsck")}
                  disabled={status === "running"}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 hover:bg-rose-500/20 disabled:opacity-40 transition-colors text-xs"
                >
                  <Wrench size={11} />
                  fsck reparieren (ext2/3/4)
                </button>
              )}
              {status === "running" && (
                <button
                  onClick={handleStop}
                  className="px-2 py-1 rounded text-[11px] text-zinc-400 hover:text-zinc-200 transition-colors"
                >
                  Abbrechen
                </button>
              )}
              {statusIcon && (
                <span className="flex items-center gap-1 text-xs text-zinc-400">
                  {statusIcon}
                  {status === "done" ? "Fertig" : status === "failed" ? "Fehler" : "Läuft…"}
                </span>
              )}
            </div>
            {lines.length > 0 && (
              <pre
                ref={logRef}
                className="bg-black/30 rounded-lg p-2 text-[10px] font-mono text-zinc-400 h-40 overflow-y-auto whitespace-pre-wrap break-all"
              >
                {lines.map((l, i) => (
                  <div key={i} className={l.toLowerCase().includes("error") || l.toLowerCase().includes("fehler") ? "text-rose-400" : ""}>
                    {l}
                  </div>
                ))}
              </pre>
            )}
          </>
        )}
      </div>
    </CollapsibleBox>
  )
}
