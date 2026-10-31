import { useTranslation } from "react-i18next"
import { PickField, TypedField } from "./MixFields"
import { DECADES, FEW, type Preview, type Rules } from "./programLogic"
import { BOX, BTN, BTN_DANGER, BTN_MAIN, INPUT } from "./ui"

interface Props {
  name: string; rules: Rules; allowLong: boolean; genres: string[]; folders: string[]; preview: Preview | null
  canModerate: boolean; busy: boolean; isNew?: boolean
  onChange: (v: { name?: string; rules?: Rules; allowLong?: boolean }) => void
  onSave: () => void; onDelete: () => void; onPlayNow: () => void
}
type ListKey = "genres" | "artists" | "folders" | "exclude_genres" | "exclude_artists" | "exclude_folders"

/** Mix als Regel: Genres, Interpreten, Jahrzehnte, Ordner, Ausschließen. Zeigt sofort Anzahl und Beispiele. */
export function MixEditor({ name, rules, allowLong, genres, folders, preview, canModerate, busy, isNew, onChange, onSave, onDelete, onPlayNow }: Props) {
  const { t } = useTranslation("radiostream")
  const ro = !canModerate || busy
  const set = (k: ListKey, v: string[]) => onChange({ rules: { ...rules, [k]: v } })
  const f = (k: ListKey) => ({ values: rules[k], readOnly: ro, exclude: k.startsWith("exclude"), onChange: (v: string[]) => set(k, v) })
  return (
    <section className={BOX} data-radiostream-mix>
      <label className="block space-y-1"><span className="text-sm text-[#c8d2df]">{t("program.name")}</span>
        <input className={INPUT} value={name} maxLength={80} disabled={ro} onChange={(e) => onChange({ name: e.target.value })} /></label>
      <div className="grid gap-3 md:grid-cols-2">
        <PickField {...f("genres")} options={genres} label="mix.genres" />
        <TypedField {...f("artists")} label="mix.artists" />
        <TypedField {...f("folders")} options={folders} listId="rs-folders" label="mix.folders" />
        <div className="space-y-1"><span className="text-sm text-[#c8d2df]">{t("mix.decades")}</span>
          <div className="flex flex-wrap gap-1">{DECADES.map((d) => {
            const on = rules.decades.includes(d)
            return <button key={d} type="button" disabled={ro} aria-pressed={on} onClick={() => onChange({ rules: { ...rules, decades: on ? rules.decades.filter((x) => x !== d) : [...rules.decades, d] } })}
              className={`rounded border px-2 py-1 text-xs ${on ? "border-emerald-400 text-emerald-300" : "border-[rgb(var(--hh-s-rand,42_54_75))] text-[#c8d2df]"}`}>{d}er</button>
          })}</div>
          {rules.decades.length === 0 && <p className="text-xs text-[#9aa7bc]">{t("mix.any")}</p>}
        </div>
      </div>
      <details className="space-y-2"><summary className="cursor-pointer text-sm text-[#c8d2df]">{t("mix.exclude")}</summary>
        <div className="grid gap-3 pt-2 md:grid-cols-3">
          <PickField {...f("exclude_genres")} options={genres} label="mix.exclude_genres" />
          <TypedField {...f("exclude_artists")} label="mix.exclude_artists" />
          <TypedField {...f("exclude_folders")} options={folders} listId="rs-exfolders" label="mix.exclude_folders" />
        </div>
      </details>
      <label className="flex items-center gap-2 text-sm text-[#c8d2df]"><input type="checkbox" checked={allowLong} disabled={ro} onChange={(e) => onChange({ allowLong: e.target.checked })} />{t("mix.allow_long")}</label>
      {preview && <div className="space-y-1">
        <p className="text-sm font-semibold text-emerald-300">{t("mix.count", { count: preview.count })}</p>
        {preview.count > 0 && preview.count < FEW && <p className="text-xs text-amber-300">{t("mix.few")}</p>}
        {preview.examples.length > 0 && <ul className="text-xs text-[#c8d2df]">{preview.examples.map((e) => <li key={e.track_id} className="break-words">{e.artist} – {e.title}{e.year ? ` (${e.year})` : ""}</li>)}</ul>}
      </div>}
      {canModerate && <div className="flex flex-wrap gap-2">
        <button type="button" className={BTN_MAIN} disabled={busy || !name.trim()} onClick={onSave}>{t("mix.save")}</button>
        {!isNew && <button type="button" className={BTN} disabled={busy} onClick={onPlayNow}>{t("mix.play_now")}</button>}
        {!isNew && <button type="button" className={BTN_DANGER} disabled={busy} onClick={onDelete}>{t("mix.delete")}</button>}
      </div>}
    </section>
  )
}
