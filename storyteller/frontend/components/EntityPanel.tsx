// Reiter „Steckbrief“: Name, Spitznamen, Beschreibung, freie Eigenschaften (Schlüssel/Wert);
// G4c: Vorschlag des Agenten (Änderung oben im Steckbrief, neuer Eintrag als eigene Ansicht).
import { useTranslation } from "react-i18next"
import { Plus, X } from "lucide-react"
import { changeFor, proposalIdOf } from "../entityProposal"
import type { Entity } from "../model"
import type { BookState } from "../useBook"
import { EntityProposalBox } from "./EntityProposalBox"

const field = "w-full rounded-lg border border-white/10 bg-zinc-950 px-2.5 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600"
const label = "block space-y-1 text-xs text-zinc-400"

interface Props { state: BookState; entityId: string | null; onDeleted: () => void; onOpen: (id: string) => void }

export function EntityPanel({ state, entityId, onDeleted, onOpen }: Props) {
  const { t } = useTranslation("storyteller")
  const e = state.book.entities.find((x) => x.id === entityId)
  const pending = proposalIdOf(entityId)
  const newProp = pending ? state.entityProposals.find((p) => p.id === pending) : undefined
  if (newProp) return <EntityProposalBox key={newProp.id} state={state} proposal={newProp} onDone={(id) => (id ? onOpen(id) : onDeleted())} />
  if (!e) return <p className="text-sm text-zinc-500">{t("entity_none")}</p>
  const change = changeFor(state.entityProposals, e.id)

  const set = (patch: Partial<Entity>) =>
    state.change((b) => ({ ...b, entities: b.entities.map((x) => (x.id === e.id ? { ...x, ...patch, id: x.id } : x)) }))
  const setField = (i: number, key: "key" | "value", v: string) =>
    set({ fields: e.fields.map((f, j) => (j === i ? { ...f, [key]: v } : f)) })

  return (
    <div className="space-y-4">
      {change && <EntityProposalBox key={change.id} state={state} proposal={change} current={e} onDone={() => undefined} />}
      <label className={label}><span>{t("entity_name")}</span>
        <input className={`${field} text-base font-semibold`} value={e.name} maxLength={200} onChange={(ev) => set({ name: ev.target.value })} />
      </label>
      <label className={label}><span>{t("entity_aliases")}</span>
        <input className={field} placeholder={t("entity_aliases_ph")} defaultValue={e.aliases.join(", ")}
          onBlur={(ev) => set({ aliases: ev.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
      </label>
      <label className={label}><span>{t("entity_desc")}</span>
        <textarea className={`${field} min-h-[90px]`} value={e.description} onChange={(ev) => set({ description: ev.target.value })} />
      </label>
      <section className="space-y-1.5">
        <h3 className="text-xs font-semibold text-zinc-400">{t("entity_fields")}</h3>
        {e.fields.map((f, i) => (
          <div key={i} className="flex gap-1.5">
            <input className={`${field} w-2/5`} value={f.key} placeholder={t("entity_field_key")} onChange={(ev) => setField(i, "key", ev.target.value)} />
            <input className={field} value={f.value} placeholder={t("entity_field_value")} onChange={(ev) => setField(i, "value", ev.target.value)} />
            <button onClick={() => set({ fields: e.fields.filter((_, j) => j !== i) })} className="px-1 text-zinc-600 hover:text-red-300" aria-label="×">
              <X className="h-4 w-4" />
            </button>
          </div>
        ))}
        <button onClick={() => set({ fields: [...e.fields, { key: "", value: "" }] })}
          className="inline-flex items-center gap-1 rounded px-1.5 py-1 text-xs text-violet-300 hover:bg-violet-500/10">
          <Plus className="h-3.5 w-3.5" />{t("entity_field_add")}
        </button>
      </section>
      <button onClick={() => {
        if (!confirm(t("entity_delete_confirm", { name: e.name }))) return
        state.change((b) => ({ ...b, entities: b.entities.filter((x) => x.id !== e.id) }))
        onDeleted()
      }} className="text-xs text-zinc-600 hover:text-red-300">{t("entity_delete")}</button>
    </div>
  )
}
