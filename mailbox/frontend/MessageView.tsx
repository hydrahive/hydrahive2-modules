import { useState } from "react"
import { Download, FileText, ImageOff, Paperclip } from "lucide-react"
import { mailApi, type MailDetail } from "./api"
import { fullDate, senderName, size } from "./mailFormat"

/** Lesebereich. HTML nur im sandbox-iframe ohne allow-scripts (Server bereinigt zusätzlich + CSP).
 *  Externe Bilder erst nach Klick („Bilder laden“). Texte nur als Text – nie dangerouslySetInnerHTML.
 *  Aufrufer setzt key={mail.id}: neue Mail = frischer Zustand (Text/HTML-Umschalter). */
export function MessageView({ mail, onImages, images }: { mail: MailDetail; images: boolean; onImages: () => void }) {
  const [showText, setShowText] = useState(!mail.has_html)
  const files = mail.attachments.filter((a) => !a.inline)
  return (
    <article className="flex h-full min-h-0 flex-col gap-2">
      <header className="space-y-1 border-b border-[rgb(var(--hh-s-rand,42_54_75))] pb-2">
        <h2 className="text-lg font-bold text-[#e8eef8]">{mail.subject || "(ohne Betreff)"}</h2>
        <p className="text-sm text-[#d7deea]"><span className="font-semibold">{senderName(mail.from_addr)}</span>
          <span className="ml-2 text-xs text-[#9aa7bc]">{mail.from_addr}</span></p>
        <p className="text-xs text-[#9aa7bc]">an {mail.to_addr || "–"}{mail.cc_addr ? ` · cc ${mail.cc_addr}` : ""}</p>
        <p className="text-xs text-[#9aa7bc]">{fullDate(mail.date)} · {mail.account} · {mail.folder}</p>
        {mail.deleted_on_server === 1 && (
          <p className="text-xs text-amber-200" data-mbx-archived="1">Auf dem Server gelöscht – nur noch im Archiv.</p>
        )}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          {mail.has_html && (
            <button type="button" onClick={() => setShowText(!showText)} data-mbx-toggle="1"
              className="rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-0.5 text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,28_38_56))]">
              {showText ? "HTML-Ansicht" : "Nur Text"}</button>
          )}
          {mail.has_html && !showText && !images && (
            <button type="button" onClick={onImages} data-mbx-images="1"
              className="inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] px-2 py-0.5 text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,28_38_56))]">
              <ImageOff size={12} />Bilder laden</button>
          )}
          <a href={mailApi.emlUrl(mail.id)} className="inline-flex items-center gap-1 text-[#69d7ff] hover:underline">
            <Download size={12} />.eml</a>
        </div>
      </header>
      {files.length > 0 && (
        <ul className="flex flex-wrap gap-2" aria-label="Anhänge">
          {files.map((a) => (
            <li key={a.index}>
              <a href={mailApi.attachmentUrl(mail.id, a.index)} data-mbx-attachment={a.index}
                className="inline-flex items-center gap-1 rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-1 text-xs text-[#d7deea] hover:bg-[rgb(var(--hh-s-hebung,28_38_56))]">
                <Paperclip size={12} />{a.name}<span className="text-[#9aa7bc]">{size(a.size)}</span></a>
            </li>
          ))}
        </ul>
      )}
      <div className="min-h-0 flex-1 overflow-hidden rounded-[4px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-white">
        {showText ? (
          <pre className="h-full overflow-auto whitespace-pre-wrap bg-[rgb(var(--hh-s-tief,13_19_31))] p-3 font-sans text-sm text-[#d7deea]">
            {mail.text || <span className="inline-flex items-center gap-1 text-[#9aa7bc]"><FileText size={14} />Kein Text</span>}
          </pre>
        ) : (
          <iframe title="Mailinhalt" src={mailApi.htmlUrl(mail.id, images)} sandbox="allow-popups allow-popups-to-escape-sandbox"
            referrerPolicy="no-referrer" className="h-full w-full border-0" />
        )}
      </div>
    </article>
  )
}
