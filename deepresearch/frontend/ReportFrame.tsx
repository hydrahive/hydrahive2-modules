import { useEffect, useState } from "react"
import { fetchReportHtml } from "./api"

/** Der Report ist self-contained (data:-Bilder + inline-CSS) → rendert per srcDoc
 *  unter der App-CSP (img-src data:, style-src 'unsafe-inline'). Inline-Skripte
 *  (Export/Scrollspy) sind in-app CSP-geblockt — dafür der „neuer Tab"-Button. */
export function ReportFrame({ runId }: { runId: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    setHtml(null)
    setError(null)
    fetchReportHtml(runId)
      .then((h) => {
        if (alive) setHtml(h)
      })
      .catch((e) => {
        if (alive) setError(String(e))
      })
    return () => {
      alive = false
    }
  }, [runId])

  function openInTab() {
    if (!html) return
    const url = URL.createObjectURL(new Blob([html], { type: "text/html" }))
    window.open(url, "_blank")
    setTimeout(() => URL.revokeObjectURL(url), 60000)
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

  return (
    <div className="flex flex-col h-full min-h-[80vh]">
      <div className="flex justify-end mb-2">
        <button
          onClick={openInTab}
          className="px-3 py-1.5 rounded-lg text-sm bg-white/5 text-zinc-300 hover:bg-white/10 border border-white/10"
        >
          Im neuen Tab öffnen ↗
        </button>
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
