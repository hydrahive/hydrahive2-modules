/** G1: die Geschichte als Karten – Text ändern (speichert beim Verlassen), verschieben, löschen, Szene hinzufügen. */
import { useState } from "react"
import { ArrowDown, ArrowUp, Check, Plus, Trash2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { Card } from "./guidedLogic"
import { SmallButton } from "./ui"

interface Props {
  cards: Card[]
  /** ID der zuletzt gespeicherten Karte (für „Gespeichert“) */
  saved: string | null
  busy: boolean
  onText: (id: string, text: string) => void
  onMove: (id: string, dir: -1 | 1) => void
  onDelete: (id: string, n: number) => void
  onAdd: () => void
}

function CardText({ card, n, onText }: { card: Card; n: number; onText: Props["onText"] }) {
  const { t } = useTranslation("studio")
  const [text, setText] = useState(card.text)
  return (
    <textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} maxLength={4000} aria-label={t("guided.scene_n", { n })}
      onBlur={() => { if (text.trim() && text !== card.text) onText(card.id, text.trim()) }} placeholder={t("guided.scene_placeholder")}
      className="min-w-0 flex-1 resize-none rounded-[6px] border border-transparent bg-transparent p-1 text-base text-[#e8eef8] outline-none hover:border-[#2a364b] focus:border-[#69d7ff]" />
  )
}

export function IdeaCards({ cards, saved, busy, onText, onMove, onDelete, onAdd }: Props) {
  const { t } = useTranslation("studio")
  return (
    <section className="mt-6">
      <h2 className="mb-1 text-xl font-black text-[#f2f6fc]">{t("guided.story_title", { count: cards.length })}</h2>
      <p className="mb-3 text-sm text-[#8d9ab0]">{t("guided.story_text")}</p>
      <ol className="space-y-2">
        {cards.map((c, i) => (
          <li key={c.id} className="flex items-start gap-3 rounded-[10px] border border-[#2a364b] bg-[#0e1420] p-3" data-guided-card={c.id}>
            <span className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#1c2940] text-sm font-black text-[#69d7ff]">{i + 1}</span>
            <CardText key={`${c.id}:${c.text}`} card={c} n={i + 1} onText={onText} />
            <div className="flex shrink-0 items-center gap-1">
              {saved === c.id && <span className="mr-1 flex items-center gap-1 text-xs font-semibold text-[#3ddc97]"><Check size={13} /> {t("guided.saved")}</span>}
              <SmallButton label={t("guided.up")} onClick={() => onMove(c.id, -1)} disabled={busy || i === 0}><ArrowUp size={14} /></SmallButton>
              <SmallButton label={t("guided.down")} onClick={() => onMove(c.id, 1)} disabled={busy || i === cards.length - 1}><ArrowDown size={14} /></SmallButton>
              <SmallButton label={t("guided.delete_scene")} onClick={() => onDelete(c.id, i + 1)} disabled={busy}><Trash2 size={14} /></SmallButton>
            </div>
          </li>
        ))}
      </ol>
      <div className="mt-3"><SmallButton onClick={onAdd} disabled={busy}><Plus size={14} /> {t("guided.add_scene")}</SmallButton></div>
    </section>
  )
}
