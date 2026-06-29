import { useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi, fileUrl } from "./api"
import { CharacterReferences } from "./CharacterReferences"
import type { AtelierCharacter, CharacterInput } from "./types"

interface Props {
  projectId: string
  characters: AtelierCharacter[]
  selectedIds: string[]
  onToggle: (id: string) => void
  onChanged: () => void
  refAbsPath: (rel: string) => string
}

const EMPTY: CharacterInput = {
  name: "",
  description: "",
  style_anchor: "",
  palette: [],
  seed: null,
  model: "",
}

/** Linke Spalte: Charakter-Bibliothek des Projekts — anlegen, wählen, löschen. */
export function CharacterLibrary({
  projectId,
  characters,
  selectedIds,
  onToggle,
  onChanged,
  refAbsPath,
}: Props) {
  const { t } = useTranslation("atelier")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<CharacterInput>(EMPTY)
  const [busy, setBusy] = useState(false)

  // Editing-Figur immer aus der frischen Liste ableiten → nach Upload/Reload
  // hat sie die aktuellen Referenzen (kein veralteter lokaler Snapshot).
  const editing = editingId ? characters.find((c) => c.id === editingId) ?? null : null

  function startNew() {
    setEditingId(null)
    setDraft(EMPTY)
  }

  function startEdit(c: AtelierCharacter) {
    setEditingId(c.id)
    setDraft({
      name: c.name,
      description: c.description,
      style_anchor: c.style_anchor,
      palette: c.palette,
      seed: c.seed,
      model: c.model,
    })
  }

  async function save() {
    if (!draft.name.trim()) return
    setBusy(true)
    try {
      if (editing) {
        await atelierApi.updateCharacter(projectId, editing.id, draft)
      } else {
        // Neue Figur direkt in den Edit-Modus → Referenzbilder hochladbar.
        const created = await atelierApi.createCharacter(projectId, draft)
        setEditingId(created.id)
      }
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    if (!confirm(t("delete_confirm"))) return
    await atelierApi.deleteCharacter(projectId, id)
    if (editingId === id) startNew()
    onChanged()
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">{t("characters")}</h3>
        <button onClick={startNew} className="text-xs px-2 py-1 rounded bg-slate-700 hover:bg-slate-600">
          {t("new_character")}
        </button>
      </div>

      <ul className="flex flex-col gap-1.5">
        {characters.map((c) => {
          const active = selectedIds.includes(c.id)
          const hero = c.references[0]
          return (
            <li
              key={c.id}
              className={`flex items-center gap-2 rounded p-1.5 border transition-colors ${
                active ? "border-emerald-500 bg-emerald-500/10" : "border-slate-700 bg-slate-800/50"
              }`}
            >
              <button onClick={() => onToggle(c.id)} className="flex items-center gap-2 flex-1 text-left">
                {hero ? (
                  <img src={fileUrl(refAbsPath(hero))} alt="" className="h-8 w-8 rounded object-cover" />
                ) : (
                  <span className="h-8 w-8 rounded bg-slate-700 grid place-items-center text-xs">🎭</span>
                )}
                <span className="text-xs text-slate-100 truncate">{c.name || t("untitled")}</span>
              </button>
              <button onClick={() => startEdit(c)} title={t("edit")} className="text-xs text-slate-400 hover:text-slate-200">✎</button>
              <button onClick={() => remove(c.id)} title={t("delete")} className="text-xs text-slate-400 hover:text-red-400">✕</button>
            </li>
          )
        })}
        {characters.length === 0 && <li className="text-xs text-slate-500">{t("no_characters")}</li>}
      </ul>

      <div className="border-t border-slate-700 pt-3 flex flex-col gap-2">
        <h4 className="text-xs font-semibold text-slate-300">
          {editing ? t("edit_character") : t("new_character")}
        </h4>
        <input
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          placeholder={t("char_name")}
          className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
        />
        <textarea
          value={draft.description}
          onChange={(e) => setDraft({ ...draft, description: e.target.value })}
          placeholder={t("char_description")}
          rows={3}
          className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 resize-y"
        />
        <input
          value={draft.style_anchor}
          onChange={(e) => setDraft({ ...draft, style_anchor: e.target.value })}
          placeholder={t("char_style")}
          className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
        />
        <div className="flex gap-2">
          <input
            value={draft.palette.join(", ")}
            onChange={(e) => setDraft({ ...draft, palette: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })}
            placeholder={t("char_palette")}
            className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 flex-1"
          />
          <input
            type="number"
            value={draft.seed ?? ""}
            onChange={(e) => setDraft({ ...draft, seed: e.target.value ? Number(e.target.value) : null })}
            placeholder={t("char_seed")}
            className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 w-20"
          />
        </div>
        <button
          onClick={save}
          disabled={busy || !draft.name.trim()}
          className="text-xs px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40"
        >
          {editing ? t("save") : t("create")}
        </button>

        {editing ? (
          <CharacterReferences
            projectId={projectId}
            character={editing}
            onChanged={onChanged}
            refAbsPath={refAbsPath}
          />
        ) : (
          <p className="text-[10px] text-slate-500">{t("references_after_create")}</p>
        )}
      </div>
    </div>
  )
}
