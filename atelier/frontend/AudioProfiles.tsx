import { useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi } from "./api"
import type { AudioProfile, AudioProfileInput } from "./types"

interface Props {
  projectId: string
  profiles: AudioProfile[]
  selectedIds: string[]
  onToggle: (id: string) => void
  onChanged: () => void
}

const EMPTY: AudioProfileInput = { name: "", description: "", model: "" }

/** Sound-Profile: wiederverwendbare Track-Anker (Genre/Mood/Instrumente/BPM),
 *  analog zur Charakter-Bibliothek, aber ohne Bild/Seed/Palette. */
export function AudioProfiles({ projectId, profiles, selectedIds, onToggle, onChanged }: Props) {
  const { t } = useTranslation("atelier")
  const [editingId, setEditingId] = useState<string | null>(null)
  const [draft, setDraft] = useState<AudioProfileInput>(EMPTY)
  const [busy, setBusy] = useState(false)

  function startNew() {
    setEditingId(null)
    setDraft(EMPTY)
  }

  function startEdit(p: AudioProfile) {
    setEditingId(p.id)
    setDraft({ name: p.name, description: p.description, model: p.model })
  }

  async function save() {
    if (!draft.name.trim()) return
    setBusy(true)
    try {
      if (editingId) {
        await atelierApi.updateAudioProfile(projectId, editingId, draft)
      } else {
        await atelierApi.createAudioProfile(projectId, draft)
      }
      startNew()
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  async function remove(id: string) {
    if (!confirm(t("audio_delete_profile_confirm"))) return
    await atelierApi.deleteAudioProfile(projectId, id)
    if (editingId === id) startNew()
    onChanged()
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">{t("audio_profiles")}</h3>
        <button onClick={startNew} className="text-xs px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 font-medium">
          ✚ {t("audio_new_profile")}
        </button>
      </div>

      <ul className="flex flex-col gap-1.5">
        {profiles.map((p) => {
          const active = selectedIds.includes(p.id)
          return (
            <li
              key={p.id}
              className={`flex items-center gap-2 rounded p-1.5 border transition-colors ${
                active ? "border-emerald-500 bg-emerald-500/10" : "border-slate-700 bg-slate-800/50"
              }`}
            >
              <button onClick={() => onToggle(p.id)} className="flex items-center gap-2 flex-1 text-left">
                <span className="h-8 w-8 rounded bg-slate-700 grid place-items-center text-xs">🎼</span>
                <span className="text-xs text-slate-100 truncate">{p.name || t("untitled")}</span>
              </button>
              <button onClick={() => startEdit(p)} title={t("edit")} className="text-xs text-slate-400 hover:text-slate-200">✎</button>
              <button onClick={() => remove(p.id)} title={t("delete")} className="text-xs text-slate-400 hover:text-red-400">✕</button>
            </li>
          )
        })}
        {profiles.length === 0 && <li className="text-xs text-slate-500">{t("audio_no_profiles")}</li>}
      </ul>

      <div className="rounded-lg border border-emerald-700/60 bg-emerald-500/5 p-3 flex flex-col gap-2">
        <h4 className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
          <span>{editingId ? "✎" : "✚"}</span>
          {editingId ? t("audio_edit_profile") : t("audio_new_profile")}
        </h4>
        <input
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          placeholder={t("audio_profile_name")}
          className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
        />
        <textarea
          value={draft.description}
          onChange={(e) => setDraft({ ...draft, description: e.target.value })}
          placeholder={t("audio_profile_description")}
          rows={3}
          className="text-xs px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 resize-y"
        />
        <button
          onClick={save}
          disabled={busy || !draft.name.trim()}
          className="text-xs px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40"
        >
          {editingId ? t("save") : t("create")}
        </button>
      </div>
    </div>
  )
}
