import { useEffect, useState } from "react"
import { fetchReportHtml } from "./api"

/** Lädt den Report über eine Blob-URL ins iframe (eigener Dokument-Kontext) statt
 *  srcDoc — so greift NICHT die strenge App-CSP, die inline-Styles/Skripte killt. */
export function ReportFrame({ runId }: { runId: string }) {
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    let objectUrl: string | null = null
    setUrl(null)
    setError(null)
    fetchReportHtml(runId)
      .then((html) => {
        if (!alive) return
        objectUrl = URL.createObjectURL(new Blob([html], { type: "text/html" }))
        setUrl(objectUrl)
      })
      .catch((e) => {
        if (alive) setError(String(e))
      })
    return () => {
      alive = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [runId])

  if (error) {
    return (
      <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
        Bericht konnte nicht geladen werden: {error}
      </div>
    )
  }
  if (!url) {
    return <div className="text-zinc-500 text-sm p-4">Lade Bericht …</div>
  }

  return (
    <div className="flex flex-col h-full min-h-[80vh]">
      <div className="flex justify-end mb-2">
        <button
          onClick={() => window.open(url, "_blank")}
          className="px-3 py-1.5 rounded-lg text-sm bg-white/5 text-zinc-300 hover:bg-white/10 border border-white/10"
        >
          Im neuen Tab öffnen ↗
        </button>
      </div>
      <iframe
        src={url}
        title="Deep Research Report"
        className="flex-1 w-full rounded-xl border border-white/10 bg-[#fbf9f4]"
      />
    </div>
  )
}
