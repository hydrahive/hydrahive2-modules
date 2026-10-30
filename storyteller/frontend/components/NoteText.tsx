// T1d: Text eines Hinweises/einer Notiz als Markdown (Recherche-Notizen kommen mit Überschriften, Fett, Listen).
// Sicher: kein rohes HTML (react-markdown-Standard), Links nur http(s) in neuem Tab, Bilder werden nicht geladen.
import ReactMarkdown, { type Components } from "react-markdown"
import remarkGfm from "remark-gfm"
import { safeUrl } from "../teamNotes"

const components: Components = {
  a: ({ href, children }) => {
    const url = safeUrl(href ?? "")
    return url ? <a href={url} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span>
  },
  img: ({ alt }) => <span>{alt}</span>,
}

export function NoteText({ text }: { text: string }) {
  return (
    <div className="st-team-note-text prose prose-invert prose-sm max-w-none text-[#c8d2df] prose-headings:text-[#e8eef8] prose-headings:text-sm prose-a:text-sky-300 prose-strong:text-[#e8eef8]">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>{text}</ReactMarkdown>
    </div>
  )
}
