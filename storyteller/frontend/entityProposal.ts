// Ghostwriter G4c – Steckbrief-Vorschläge des Agenten ohne React (Spec §11.5): Server-Antwort → Liste,
// Zuordnung zu Steckbriefen, Vergleich alt → neu je Feld. Neue Vorschläge haben noch keine Steckbrief-ID;
// sie werden über die Kennung „proposal:<id>“ geöffnet.
import type { Entity, EntityKind } from "./model"

export type EntityChangeKey = "name" | "aliases" | "description" | "fields"
export const ENTITY_KEYS: EntityChangeKey[] = ["name", "aliases", "description", "fields"]
const PREFIX = "proposal:"

export interface EntityProposal {
  id: string; entity_id: string; kind: EntityKind
  changes: Partial<Pick<Entity, EntityChangeKey>>
  base_structure_version: number; source: "run" | "agent"; session_id: string; note: string; at: string
}

export const proposalKey = (p: EntityProposal) => `${PREFIX}${p.id}`
export const proposalIdOf = (key: string | null) => (key?.startsWith(PREFIX) ? key.slice(PREFIX.length) : null)

/** Neue Steckbriefe (noch ohne ID im Buch), nach Art. */
export function newProposals(list: EntityProposal[], kind: EntityKind): EntityProposal[] {
  return list.filter((p) => !p.entity_id && p.kind === kind)
}

/** Offener Änderungsvorschlag zu einem Steckbrief (höchstens einer). */
export function changeFor(list: EntityProposal[], entityId: string): EntityProposal | undefined {
  return list.find((p) => p.entity_id === entityId)
}

export interface EntityRow { key: EntityChangeKey; old: string; proposed: string }

const show = (key: EntityChangeKey, v: Entity[EntityChangeKey] | undefined): string => {
  if (v === undefined) return ""
  if (key === "aliases") return (v as string[]).join(", ")
  if (key === "fields") return (v as Entity["fields"]).map((f) => `${f.key}: ${f.value}`).join("\n")
  return v as string
}

/** Zeilen für den Vergleich (bei neuen Steckbriefen ist „alt“ leer). */
export function entityRows(p: EntityProposal, current?: Entity): EntityRow[] {
  return ENTITY_KEYS.filter((k) => p.changes[k] !== undefined)
    .map((k) => ({ key: k, old: show(k, current?.[k]), proposed: show(k, p.changes[k]) }))
}
