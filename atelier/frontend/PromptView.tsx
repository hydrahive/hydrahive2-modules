import { useState } from "react"
import { useTranslation } from "react-i18next"

interface Props {
  text: string
  /** Zeilen im eingeklappten Zustand (default 2). */
  clamp?: number
}

/** Prompt lesbar anzeigen: standardmäßig auf ein paar Zeilen begrenzt (nicht
 *  einzeilig abgeschnitten), auf Klick voll ausklappbar, mit Kopier-Button.
 *  Ersetzt das alte truncate unter Medien-Kacheln. */
export function PromptView({ text, clamp = 2 }: Props) {
  const { t } = useTranslation("atelier")
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)

  async function copy() {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch { /* clipboard nicht verfügbar — ignorieren */ }
  }

  return (
    <div className="px-2 py-1">
      <p
        onClick={() => setOpen((o) => !o)}
        title={open ? t("prompt_collapse") : t("prompt_expand")}
        className="text-[10px] text-slate-400 whitespace-pre-wrap cursor-pointer break-words"
        style={open ? undefined : {
          display: "-webkit-box",
          WebkitLineClamp: clamp,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {text}
      </p>
      <div className="flex gap-2 mt-0.5">
        <button onClick={() => setOpen((o) => !o)} className="text-[9px] text-slate-500 hover:text-slate-300">
          {open ? `▴ ${t("prompt_collapse")}` : `▾ ${t("prompt_expand")}`}
        </button>
        <button onClick={copy} className="text-[9px] text-slate-500 hover:text-slate-300">
          {copied ? `✓ ${t("prompt_copied")}` : `⧉ ${t("prompt_copy")}`}
        </button>
      </div>
    </div>
  )
}
