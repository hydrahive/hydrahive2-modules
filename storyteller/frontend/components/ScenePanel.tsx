// Reiter „Szene“: Titel, Zusammenfassung, Perspektive, Stand, erkannte Steckbriefe, Schnappschüsse.
import { useTranslation } from "react-i18next"
import { entitiesInText, removeScene, type Scene, type SceneStatus } from "../model"
import type { useBook } from "../useBook"

const STATUSES: SceneStatus[] = ["idea", "draft", "revised", "done"]
const field = "w-full rounded-lg border border-white/10 bg-zinc-950 px-2.5 py-1.5 text-sm text-zinc-100 placeholder:text-zinc-600"
const label = "block space-y-1 text-xs text-zinc-400"

interface Props { state: ReturnType<typeof useBook>; scene: Scene; onOpenEntity: (id: string) => void }

export function ScenePanel({ state, scene, onOpenEntity }: Props) {
  const { t, i18n } = useTranslation("storyteller")
  const { book } = state
  const set = (patch: Partial<Scene>) => state.setScene(scene.id, patch)
  const found = entitiesInText(book.entities, scene.text)
  const chars = book.entities.filter((e) => e.kind === "character")
  const snaps = state.snapshots.filter((s) => s.sceneId === scene.id)
  const fmt = (iso: string) => new Date(iso).toLocaleTimeString(i18n.language, { hour: "2-digit", minute: "2-digit", second: "2-digit" })

  return (
    <div className="space-y-4">
      <label className={label}><span>{t("scene_title")}</span>
        <input className={field} value={scene.title} maxLength={200} onChange={(e) => set({ title: e.target.value })} />
      </label>
      <label className={label}><span>{t("scene_summary")}</span>
        <textarea className={`${field} min-h-[72px]`} value={scene.summary} placeholder={t("scene_summary_ph")} onChange={(e) => set({ summary: e.target.value })} />
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label className={label}><span>{t("scene_pov")}</span>
          <select className={field} value={scene.pov} onChange={(e) => set({ pov: e.target.value })}>
            <option value="">{t("scene_pov_none")}</option>
            {chars.map((c) => <option key={c.id} value={c.name}>{c.name}</option>)}
          </select>
        </label>
        <label className={label}><span>{t("scene_status")}</span>
          <select className={field} value={scene.status} onChange={(e) => set({ status: e.target.value as SceneStatus })}>
            {STATUSES.map((s) => <option key={s} value={s}>{t(`status_${s}`)}</option>)}
          </select>
        </label>
      </div>

      <section>
        <h3 className="mb-1 text-xs font-semibold text-zinc-400">{t("in_scene")}</h3>
        {found.length === 0 ? <p className="text-xs text-zinc-600">{t("in_scene_none")}</p> : (
          <div className="flex flex-wrap gap-1.5">
            {found.map((e) => (
              <button key={e.id} onClick={() => onOpenEntity(e.id)} title={e.description}
                className="rounded-full border border-white/10 bg-white/5 px-2.5 py-0.5 text-xs text-zinc-200 hover:border-violet-400/50">{e.name}</button>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="mb-1 flex items-center justify-between">
          <h3 className="text-xs font-semibold text-zinc-400">{t("snapshots")}</h3>
          <button onClick={() => state.snapshot(scene.id)} className="rounded px-2 py-0.5 text-xs text-violet-300 hover:bg-violet-500/10">{t("snapshot_now")}</button>
        </div>
        {snaps.length === 0 ? <p className="text-xs text-zinc-600">{t("snapshots_none")}</p> : (
          <ul className="space-y-1">
            {snaps.map((s) => (
              <li key={s.id} className="flex items-center justify-between rounded px-2 py-1 text-xs text-zinc-400 hover:bg-white/5">
                <span>{fmt(s.at)} · {s.text.split(/\s+/).filter(Boolean).length} W.</span>
                <button onClick={() => { if (confirm(t("snapshot_restore_confirm", { when: fmt(s.at) }))) state.restore(s) }}
                  className="text-violet-300 hover:underline">{t("snapshot_restore")}</button>
              </li>
            ))}
          </ul>
        )}
      </section>

      <button onClick={() => { if (confirm(t("remove_scene_confirm", { title: scene.title }))) state.change((b) => removeScene(b, scene.id)) }}
        className="text-xs text-zinc-600 hover:text-red-300">{t("remove_scene")}</button>
    </div>
  )
}
