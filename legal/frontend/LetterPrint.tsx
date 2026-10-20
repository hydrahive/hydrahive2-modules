import { createPortal } from "react-dom"
import { Printer, X } from "lucide-react"
import type { Letter } from "./api"
import { DIN, deDate, splitBody } from "./letterFormat"

const mm = (v: number) => `${v}mm`

/** Druckansicht DIN 5008 Form B (Maße: letterFormat.DIN). Liegt als eigene Ebene über der App; @media print blendet
 * alles andere aus. „Drucken“ → Browser-Dialog → „Als PDF speichern“ (Till 20.10.: reicht, keine PDF-Bibliothek). */
export function LetterPrint({ letter, onClose }: { letter: Letter; onClose: () => void }) {
  const textWidth = 210 - DIN.marginLeftMm - DIN.marginRightMm
  const css = `
@page { size: A4; margin: 0; }
@media print {
  body > *:not(#legal-print) { display: none !important; }
  #legal-print { position: static !important; background: white !important; overflow: visible !important; }
  #legal-print .no-print { display: none !important; }
  #legal-print .sheet { box-shadow: none !important; margin: 0 !important; }
}
#legal-print .sheet { font-family: Arial, Helvetica, sans-serif; font-size: 11pt; line-height: ${mm(DIN.lineMm)}; color: #000; }
#legal-print .sheet p { margin: 0 0 ${mm(DIN.lineMm)} 0; white-space: pre-wrap; }
#legal-print .ph { background: #fff3a0; }
#legal-print .page-no::after { content: "Seite " counter(page); }`
  const ref = [letter.their_ref && `Ihr Zeichen: ${letter.their_ref}`, letter.our_ref && `Unser Zeichen: ${letter.our_ref}`]
    .filter(Boolean)
  const [senderName, ...senderRest] = (letter.sender || "").split("\n")
  const body = splitBody(letter.body)
  return createPortal(
    <div id="legal-print" className="fixed inset-0 z-[200] overflow-auto bg-[#2b313c]">
      <style>{css}</style>
      <div className="no-print sticky top-0 z-10 flex items-center gap-2 bg-[#0d131d] px-4 py-2 text-sm text-[#e8eef8]">
        <span className="flex-1">Druckansicht – DIN 5008 Form B. Gelb = Platzhalter, vor dem Druck füllen.</span>
        <button type="button" onClick={() => window.print()} className="inline-flex items-center gap-1 rounded-[4px] bg-[#1d4ed8] px-3 py-1 text-white">
          <Printer size={14} />Drucken / als PDF speichern
        </button>
        <button type="button" onClick={onClose} className="rounded-[4px] border border-[#2a364b] p-1"><X size={14} /></button>
      </div>
      <div className="sheet relative mx-auto my-6 bg-white shadow-xl" style={{ width: "210mm", minHeight: "297mm" }}>
        {DIN.foldMm.map((y) => <div key={y} style={{ position: "absolute", left: "5mm", top: mm(y), width: "4mm", borderTop: "0.2mm solid #000" }} />)}
        <div style={{ position: "absolute", left: "5mm", top: mm(DIN.punchMm), width: "6mm", borderTop: "0.2mm solid #000" }} />
        <div style={{ position: "absolute", left: mm(DIN.addressLeftMm), top: mm(DIN.headerMm), width: mm(DIN.addressWidthMm),
                      height: mm(DIN.addressHeightMm), paddingLeft: mm(DIN.addressTextLeftMm - DIN.addressLeftMm), boxSizing: "border-box" }}>
          <div style={{ height: mm(DIN.returnMm), fontSize: "7pt", textDecoration: "underline", overflow: "hidden", whiteSpace: "nowrap" }}>
            {[senderName, ...senderRest].filter(Boolean).join(" · ")}
          </div>
          <div style={{ height: mm(DIN.notesMm), fontSize: "8pt", display: "flex", alignItems: "flex-end" }}>
            {letter.delivery === "einwurf_einschreiben" ? "Einwurf-Einschreiben" : letter.delivery === "einschreiben_rueckschein" ? "Einschreiben Rückschein" : ""}
          </div>
          <div style={{ height: mm(DIN.recipientMm), whiteSpace: "pre-wrap", overflow: "hidden" }}>{letter.recipient}</div>
        </div>
        <div style={{ position: "absolute", left: mm(DIN.infoLeftMm), top: mm(DIN.infoTopMm), width: mm(DIN.infoWidthMm), fontSize: "9pt", whiteSpace: "pre-wrap" }}>
          {letter.sender}
          {"\n\n"}{ref.join("\n")}{ref.length ? "\n" : ""}Datum: {deDate(letter.date)}
        </div>
        <div style={{ paddingTop: mm(DIN.headerMm + DIN.addressHeightMm + 2 * DIN.lineMm), paddingLeft: mm(DIN.marginLeftMm),
                      width: mm(DIN.marginLeftMm + textWidth), paddingBottom: "20mm", boxSizing: "border-box" }}>
          <p style={{ fontWeight: "bold", marginBottom: mm(2 * DIN.lineMm) }}>{letter.subject}</p>
          {body.map((part, i) => (
            <p key={i}>{part.text.split(/(\[[^\]\n]{1,120}\])/g).map((t, j) => (/^\[.*\]$/.test(t) ? <span key={j} className="ph">{t}</span> : t))}</p>
          ))}
          {letter.attachments.length > 0 && (
            <p style={{ marginTop: mm(2 * DIN.lineMm) }}>{letter.attachments.length > 1 ? "Anlagen" : "Anlage"}{"\n"}{letter.attachments.join("\n")}</p>
          )}
        </div>
        <div className="page-no" style={{ position: "absolute", bottom: "10mm", right: mm(DIN.marginRightMm), fontSize: "8pt" }} />
      </div>
    </div>,
    document.body,
  )
}
