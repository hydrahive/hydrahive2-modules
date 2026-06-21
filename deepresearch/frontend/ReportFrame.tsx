import { useEffect, useState } from "react"
import { fetchReportHtml } from "./api"

/** Der Report ist self-contained (data:-Bilder + inline-CSS) → rendert per srcDoc
 *  unter der App-CSP (img-src data:, style-src 'unsafe-inline'). Inline-Skripte sind
 *  in-app CSP-geblockt, daher laufen Export/Druck über React-Buttons (Blob). */
export function ReportFrame({ runId }: { runId: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setHtml(null)
    setError(null)
    fetchReportHtml(runId)
      .then((h) => alive && setHtml(h))
      .catch((e) => alive && setError(String(e)))
    return () => {
      alive = false
    }
  }, [runId])

  function blobUrl(): string {
    return URL.createObjectURL(new Blob([html ?? ""], { type: "text/html" }))
  }

  function openTab() {
    const url = blobUrl()
    window.open(url, "_blank")
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  }

  function printPdf() {
    const url = blobUrl()
    const w = window.open(url, "_blank")
    if (w) w.addEventListener("load", () => { w.focus(); w.print() })
    setTimeout(() => URL.revokeObjectURL(url), 60000)
  }

  function downloadHtml() {
    const url = blobUrl()
    const a = document.createElement("a")
    a.href = url
    a.download = "deep-research-report.html"
    a.click()
    setTimeout(() => URL.revokeObjectURL(url), 30000)
  }

  if (error) {
    return (
      <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
        Bericht konnte nicht geladen werden: {error}
      </div>
    )
  }
  if (!html) {
    return <div className="text-zinc-500 text-sm p-4">Lade Bericht …</div>
  }

  const btn = "px-3 py-1.5 rounded-lg text-sm bg-white/5 text-zinc-300 hover:bg-white/10 border border-white/10"
  return (
    <div className="flex flex-col h-full min-h-[80vh]">
      <div className="flex justify-end gap-2 mb-2">
        <button onClick={printPdf} className={btn}>Als PDF</button>
        <button onClick={downloadHtml} className={btn}>HTML laden</button>
        <button onClick={openTab} className={btn}>Im neuen Tab öffnen ↗</button>
      </div>
      <iframe
        srcDoc={html}
        title="Deep Research Report"
        sandbox="allow-same-origin allow-popups allow-downloads"
        className="flex-1 w-full rounded-xl border border-white/10 bg-[#fbf9f4]"
      />
    </div>
  )
}
