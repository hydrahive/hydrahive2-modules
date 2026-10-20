import { useState } from "react"
import { Check, Copy, ExternalLink } from "lucide-react"
import type { NormDetail } from "./api"
import { normLines, shortDate } from "./legalFormat"

/** Wortlaut einer Norm mit Stand und amtlichem Link. Absätze und Listenpunkte wie im Gesetz. */
export function NormView({ norm }: { norm: NormDetail }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try {
      await navigator.clipboard.writeText(norm.citation)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1500)
    } catch { /* Zwischenablage gesperrt – egal */ }
  }
  return (
    <article className="space-y-3">
      <header className="flex flex-wrap items-start justify-between gap-2">
        <div>
          <h2 className="text-lg font-bold text-[#e8eef8]">{norm.citation}</h2>
          {norm.title && <p className="text-sm text-[#d7deea]">{norm.title}</p>}
          {!norm.title && norm.gliederung && <p className="text-xs text-[#8d9ab0]">{norm.gliederung}</p>}
          <p className="mt-1 text-xs text-[#8d9ab0]">{norm.law_title}</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void copy()}
            className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-xs text-[#d7deea] hover:bg-[#172133]">
            {copied ? <Check size={13} /> : <Copy size={13} />}{copied ? "Kopiert" : "Zitat kopieren"}
          </button>
          <a href={norm.url} target="_blank" rel="noreferrer noopener"
            className="inline-flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-xs text-[#69d7ff] hover:bg-[#172133]">
            <ExternalLink size={13} />Amtliche Fassung
          </a>
        </div>
      </header>
      <div className="space-y-2 text-sm leading-6 text-[#e8eef8]">
        {normLines(norm.text).map((l, i) => (
          <p key={i} className={l.kind === "item" ? "pl-6" : ""}>{l.text}</p>
        ))}
      </div>
      <footer className="border-t border-[#2a364b] pt-2 text-[11px] leading-4 text-[#68758a]">
        {norm.stand && <p>Stand: {norm.stand}</p>}
        <p>Abgerufen am {shortDate(norm.fetched_at)} von gesetze-im-internet.de{norm.valid_to ? ` · ersetzt am ${shortDate(norm.valid_to)}` : ""}</p>
      </footer>
    </article>
  )
}
