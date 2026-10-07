// Dialog „Neues Buch“: Titel, Art, Sprache, Zielgruppe, Idee. Die Vorlage Teil/Kapitel/Szene legt der Server an.
// T1c: Ort wählen – eigenes Projekt mit Schreib-Team (nur mit Freigabe) oder das gerade gewählte Projekt.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { Users } from "lucide-react"
import { defaultPlace, placesFor, type BookPlace } from "../bookProject"
import type { BookKind } from "../model"

const KINDS: BookKind[] = ["novel", "story", "nonfiction", "learning"]
const input = "w-full rounded-lg border border-white/10 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-600"

export interface NewBookFields { title: string; kind: BookKind; language: string; audience: string; idea: string }

interface Props {
  onCancel: () => void
  onCreate: (f: NewBookFields, place: BookPlace) => void
  canCreateProject: boolean
  currentProjectName?: string
}

export function NewBookDialog({ onCancel, onCreate, canCreateProject, currentProjectName }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const [f, setF] = useState({ title: "", kind: "novel" as BookKind, language: i18n.language.startsWith("en") ? "en" : "de", audience: "", idea: "" })
  const set = <K extends keyof typeof f>(k: K, v: (typeof f)[K]) => setF((x) => ({ ...x, [k]: v }))
  const places = placesFor(canCreateProject, Boolean(currentProjectName))
  const [place, setPlace] = useState<BookPlace>(defaultPlace(canCreateProject, Boolean(currentProjectName)))
  const ok = f.title.trim().length > 0 && places.includes(place)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4" role="dialog" aria-modal="true"
      onKeyDown={(e) => { if (e.key === "Escape") onCancel() }}>
      <form className="w-full max-w-lg space-y-4 rounded-2xl border border-white/10 bg-zinc-900 p-6 shadow-2xl"
        onSubmit={(e) => { e.preventDefault(); if (ok) onCreate({ ...f, title: f.title.trim(), audience: f.audience.trim(), idea: f.idea.trim() }, place) }}>
        <h2 className="text-lg font-bold text-zinc-100">{t("new_book")}</h2>
        <label className="block space-y-1 text-xs text-zinc-400">
          <span>{t("nb_title")}</span>
          <input autoFocus className={input} value={f.title} maxLength={200} onChange={(e) => set("title", e.target.value)} />
        </label>
        <fieldset className="space-y-1 text-xs text-zinc-400">
          <legend>{t("nb_kind")}</legend>
          <div className="mt-1 grid grid-cols-2 gap-2 sm:grid-cols-4">
            {KINDS.map((k) => (
              <button type="button" key={k} onClick={() => set("kind", k)} aria-pressed={f.kind === k}
                className={`rounded-lg border px-2 py-2 text-sm ${f.kind === k ? "border-violet-400 bg-violet-500/15 text-violet-100" : "border-white/10 text-zinc-300 hover:bg-white/5"}`}>
                {t(`kind_${k}`)}
              </button>
            ))}
          </div>
        </fieldset>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="space-y-1 text-xs text-zinc-400">
            <span>{t("nb_language")}</span>
            <select className={input} value={f.language} onChange={(e) => set("language", e.target.value)}>
              <option value="de">Deutsch</option>
              <option value="en">English</option>
            </select>
          </label>
          <label className="space-y-1 text-xs text-zinc-400">
            <span>{t("nb_audience")}</span>
            <input className={input} value={f.audience} maxLength={200} placeholder={t("nb_audience_ph")} onChange={(e) => set("audience", e.target.value)} />
          </label>
        </div>
        <label className="block space-y-1 text-xs text-zinc-400">
          <span>{t("nb_idea")}</span>
          <textarea className={`${input} min-h-[80px]`} value={f.idea} maxLength={2000} placeholder={t("nb_idea_ph")} onChange={(e) => set("idea", e.target.value)} />
        </label>
        {places.length > 1 && (
          <fieldset className="st-nb-place space-y-2 text-xs text-zinc-400">
            <legend>{t("nb_place")}</legend>
            {places.map((pl) => (
              <label key={pl} className={`flex cursor-pointer gap-2 rounded-lg border p-2 ${place === pl ? "border-violet-400 bg-violet-500/10" : "border-white/10 hover:bg-white/5"}`}>
                <input type="radio" name="place" value={pl} checked={place === pl} onChange={() => setPlace(pl)} className="mt-0.5" />
                <span>
                  <span className="flex items-center gap-1.5 text-sm text-zinc-100">
                    {pl === "own" && <Users className="h-3.5 w-3.5 text-violet-300" />}
                    {t(pl === "own" ? "nb_place_own" : "nb_place_current", { name: currentProjectName })}
                  </span>
                  <span className="block text-zinc-400">{t(pl === "own" ? "nb_place_own_hint" : "nb_place_current_hint")}</span>
                </span>
              </label>
            ))}
          </fieldset>
        )}
        {places.length === 1 && places[0] === "own" && <p className="text-xs text-zinc-400">{t("nb_place_own_hint")}</p>}
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onCancel} className="rounded-lg px-3 py-2 text-sm text-zinc-300 hover:bg-white/5">{t("cancel")}</button>
          <button type="submit" disabled={!ok} className="rounded-lg bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-500 disabled:opacity-40">{t("nb_create")}</button>
        </div>
      </form>
    </div>
  )
}
