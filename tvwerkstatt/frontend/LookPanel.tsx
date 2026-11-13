import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import type { Mood, TvwApp, TvwLook, TvwWallpaper } from "./api"
import { moveInDock, nudge, setLabel, toggleDock, toggleHidden } from "./desktopLogic"
import { BOX_HEAD, CHIP, CHIP_ON, MUTED } from "./ui"
import { WallpaperRow } from "./WallpaperRow"

const MOODS: Mood[] = ["morning", "evening", "night"]

/** Kasten „Aussehen“ (rechte Spalte der Demo). Ändert nur den Entwurf; Speichern/Schieben macht die Seite. */
export function LookPanel({ look, apps, walls, mood, onMood, onChange, onUpload, onDeleteWall, wallPath }: {
  look: TvwLook; apps: TvwApp[]; walls: TvwWallpaper[]; mood: Mood; onMood: (m: Mood) => void
  onChange: (l: TvwLook) => void; onUpload: (m: Mood, f: File) => void; onDeleteWall: (id: string) => void
  wallPath: (id: string) => string
}) {
  const { t } = useTranslation("tvwerkstatt")
  const [drag, setDrag] = useState<string | null>(null)
  const file = useRef<HTMLInputElement>(null)
  const docked = look.dock.map((p) => apps.find((a) => a.package === p)).filter((a): a is TvwApp => !!a)
  const others = apps.filter((a) => !look.dock.includes(a.package))
    .sort((x, y) => (x.label || x.package).localeCompare(y.label || y.package, "de"))
  const num = (k: keyof TvwLook, v: string) => onChange({ ...look, [k]: Number(v) })

  return (
    <section className="space-y-4" aria-label={t("desk.look")}>
      <h2 className={BOX_HEAD}>{t("desk.look")}</h2>

      <div className="space-y-2">
        <div className="text-xs text-[#9aa7bc]">{t("desk.bg_by_time")}</div>
        <div className="flex gap-1.5" role="tablist">
          {MOODS.map((m) => (
            <button key={m} type="button" role="tab" aria-selected={mood === m} onClick={() => onMood(m)}
              className={mood === m ? CHIP_ON : CHIP}>{t(`mood.${m}`)}</button>
          ))}
        </div>
        <WallpaperRow walls={walls.filter((w) => w.mood === mood)} path={wallPath} onDelete={onDeleteWall} />
        <input ref={file} type="file" accept="image/jpeg,image/png,image/webp" className="hidden"
          onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(mood, f); e.target.value = "" }} />
        <button type="button" className={CHIP} onClick={() => file.current?.click()}>
          {t("desk.own_image", { mood: t(`mood.${mood}`) })}
        </button>
      </div>

      <label className="block space-y-1 text-xs text-[#9aa7bc]">
        <span>{t("desk.dim")} · {look.wallpaper_dim} %</span>
        <input type="range" min={0} max={90} step={5} value={look.wallpaper_dim} className="w-full accent-[#69d7ff]"
          onChange={(e) => num("wallpaper_dim", e.target.value)} />
      </label>

      <div className="space-y-1">
        <div className="text-xs text-[#9aa7bc]">{t("desk.columns")}</div>
        <div className="flex gap-1.5">
          {[4, 5, 6, 7].map((n) => (
            <button key={n} type="button" aria-pressed={look.columns === n} onClick={() => num("columns", String(n))}
              className={look.columns === n ? CHIP_ON : CHIP}>{n}</button>
          ))}
        </div>
      </div>

      <div className="space-y-1">
        <div className="text-xs text-[#9aa7bc]">{t("desk.dock_title")}</div>
        {apps.length === 0 && <p className={MUTED}>{t("desk.read_first")}</p>}
        <ul className="space-y-1">
          {docked.map((a, i) => (
            <li key={a.package} draggable onDragStart={() => setDrag(a.package)} onDragEnd={() => setDrag(null)}
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => { if (drag) onChange(moveInDock(look, drag, a.package)); setDrag(null) }}
              className={`flex items-center gap-2 rounded border border-[rgb(var(--hh-s-rand,52_66_92))] px-2 py-1 text-sm
                ${drag === a.package ? "opacity-50" : ""}`}>
              <span className="cursor-grab select-none text-[#9aa7bc]" aria-hidden>⋮⋮</span>
              <span className="w-5 text-right text-xs text-[#9aa7bc]">{i + 1}</span>
              <LabelInput look={look} app={a} onChange={onChange} />
              <button type="button" className="px-1 text-[#9aa7bc]" aria-label={t("desk.up")}
                onClick={() => onChange(nudge(look, a.package, -1))}>↑</button>
              <button type="button" className="px-1 text-[#9aa7bc]" aria-label={t("desk.down")}
                onClick={() => onChange(nudge(look, a.package, 1))}>↓</button>
              <Switch on label={t("desk.in_dock")} onClick={() => onChange(toggleDock(look, a.package))} />
            </li>
          ))}
        </ul>
        {others.length > 0 && <div className="pt-2 text-xs text-[#9aa7bc]">{t("desk.other_apps")}</div>}
        <ul className="space-y-1">
          {others.map((a) => {
            const hidden = look.hidden.includes(a.package)
            return (
              <li key={a.package} className="flex items-center gap-2 px-2 py-1 text-sm">
                <LabelInput look={look} app={a} onChange={onChange} />
                <button type="button" className={hidden ? CHIP_ON : CHIP}
                  onClick={() => onChange(toggleHidden(look, a.package))}>{t(hidden ? "desk.hidden" : "desk.hide")}</button>
                <Switch on={false} label={t("desk.in_dock")} disabled={hidden}
                  onClick={() => onChange(toggleDock(look, a.package))} />
              </li>
            )
          })}
        </ul>
      </div>
    </section>
  )
}

function LabelInput({ look, app, onChange }: { look: TvwLook; app: TvwApp; onChange: (l: TvwLook) => void }) {
  const { t } = useTranslation("tvwerkstatt")
  return (
    <input value={look.labels[app.package] ?? ""} placeholder={app.label || app.package} maxLength={24}
      aria-label={t("desk.rename", { app: app.label || app.package })}
      className="min-w-0 flex-1 bg-transparent text-[#e8eef8] placeholder:text-[#e8eef8] focus:placeholder:text-[#9aa7bc]"
      onChange={(e) => onChange(setLabel(look, app.package, e.target.value))} />
  )
}

function Switch({ on, label, disabled, onClick }: { on: boolean; label: string; disabled?: boolean; onClick: () => void }) {
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} disabled={disabled} onClick={onClick}
      className={`relative h-5 w-9 shrink-0 rounded-full transition disabled:opacity-30
        ${on ? "bg-[#69d7ff]" : "bg-[rgb(var(--hh-s-rand,52_66_92))]"}`}>
      <span className={`absolute top-0.5 h-4 w-4 rounded-full bg-[#e8eef8] transition ${on ? "left-[18px]" : "left-0.5"}`} />
    </button>
  )
}
