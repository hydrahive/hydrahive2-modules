// Steckbrief-Gruppen im Navigator. Sach-/Lernbuch: andere Beschriftung, gleiches Datenmodell (Spec §6).
import { useTranslation } from "react-i18next"
import { Plus } from "lucide-react"
import { groupLabelKey } from "../bookFactory"
import { changeFor, newProposals, proposalKey, type EntityProposal } from "../entityProposal"
import { newId, type Book, type EntityKind } from "../model"

const KINDS: EntityKind[] = ["character", "place", "item"]

interface Props {
  book: Book
  activeId: string | null
  onOpen: (id: string) => void
  change: (fn: (b: Book) => Book) => void
  /** G4c: offene Steckbrief-Vorschläge des Agenten (neue als eigene Einträge, Änderungen als Punkt). */
  proposals?: EntityProposal[]
}

const dot = <span className="st-has-proposal h-1.5 w-1.5 shrink-0 rounded-full bg-amber-300" />

export function EntityList({ book, activeId, onOpen, change, proposals = [] }: Props) {
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
            <div className="flex items-center justify-between px-1 pb-1 text-[11px] font-semibold uppercase tracking-wider text-[#9aa7bc]">
              {t(groupLabelKey(book.kind, k))}
              <button onClick={() => add(k)} title={t("add_entity")} className="rounded p-0.5 text-[#9aa7bc] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] hover:text-[#e8eef8]">
                <Plus className="h-3.5 w-3.5" />
              </button>
            </div>
            {list.map((e) => (
              <button key={e.id} onClick={() => onOpen(e.id)}
                className={`flex w-full items-center gap-2 rounded px-2 py-1 text-left ${e.id === activeId ? "bg-[#69d7ff]/20 text-[#c8f2ff]" : "text-[#c8d2df] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))] hover:text-[#e8eef8]"}`}>
                <span className="truncate">{e.name}</span>{changeFor(proposals, e.id) && dot}
              </button>
            ))}
            {newProposals(proposals, k).map((p) => (
              <button key={p.id} onClick={() => onOpen(proposalKey(p))}
                className={`st-entity-new-proposal flex w-full items-center gap-2 rounded px-2 py-1 text-left italic ${proposalKey(p) === activeId ? "bg-[#69d7ff]/20 text-[#c8f2ff]" : "text-[#69d7ff] hover:bg-[rgb(var(--hh-s-hebung,27_37_54))]"}`}>
                <span className="truncate">{p.changes.name}</span>
                <span className="ml-auto shrink-0 text-[10px] not-italic text-amber-300">{t("entity_proposal_badge")}</span>{dot}
              </button>
            ))}
          </div>
        )
      })}
    </div>
  )
}
