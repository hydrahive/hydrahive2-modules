// Steckbrief-Gruppen im Navigator. Sach-/Lernbuch: andere Beschriftung, gleiches Datenmodell (Spec §6).
import { useTranslation } from "react-i18next"
import { Plus } from "lucide-react"
import { groupLabelKey } from "../bookFactory"
import { newId, type Book, type EntityKind } from "../model"

const KINDS: EntityKind[] = ["character", "place", "item"]

interface Props {
  book: Book
  activeId: string | null
  onOpen: (id: string) => void
  change: (fn: (b: Book) => Book) => void
}

export function EntityList({ book, activeId, onOpen, change }: Props) {
  const { t } = useTranslation("storyteller")
  const add = (kind: EntityKind) => {
    const id = newId()
    change((b) => ({ ...b, entities: [...b.entities, { id, kind, name: t("entity_new_name"), aliases: [], description: "", fields: [] }] }))
    onOpen(id)
  }
  return (
    <div className="space-y-3">
      {KINDS.map((k) => {
        const list = book.entities.filter((e) => e.kind === k)
        return (
          <div key={k}>
            <div className="flex items-center justify-between px-1 pb-1 text-[11px] font-semibold uppercase tracking-wider text-zinc-500">
              {t(groupLabelKey(book.kind, k))}
              <button onClick={() => add(k)} title={t("add_entity")} className="rounded p-0.5 text-zinc-600 hover:bg-white/10 hover:text-zinc-200">
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>
            {list.map((e) => (
              <button key={e.id} onClick={() => onOpen(e.id)}
                className={`block w-full truncate rounded px-2 py-1 text-left ${e.id === activeId ? "bg-violet-500/20 text-violet-100" : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"}`}>
                {e.name}
              </button>
            ))}
          </div>
        )
      })}
    </div>
  )
}
