import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { PresetCatalog } from "./types"

interface Props {
  catalog: PresetCatalog
  value: Record<string, string>
  onChange: (next: Record<string, string>) => void
}

const GROUP_ICONS: Record<string, string> = {
  shot: "🎥",
  lens: "🔭",
  light: "💡",
  weather: "🌦️",
  time: "🕐",
  mood: "🎨",
}

/** Aufklappbares Regie-Panel: Kamera/Objektiv/Licht/Wetter/Tageszeit/Stimmung
 *  als Dropdowns. Leere Auswahl = Preset wird nicht in den Prompt eingefügt. */
export function CameraControls({ catalog, value, onChange }: Props) {
  const { t } = useTranslation("atelier")
  const [open, setOpen] = useState(false)

  const groups = Object.keys(catalog)
  const activeCount = groups.filter((g) => value[g]).length

  function set(group: string, key: string) {
    const next = { ...value }
    if (key) next[group] = key
    else delete next[group]
    onChange(next)
  }

  function reset() {
    onChange({})
  }

  return (
    <div className="border border-slate-700 rounded">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-slate-200"
      >
        <span>🎬 {t("camera_panel")}{activeCount > 0 ? ` (${activeCount})` : ""}</span>
        <span className="text-slate-400">{open ? "▾" : "▸"}</span>
      </button>

      {open && (
        <div className="px-3 pb-3 flex flex-col gap-2">
          {groups.map((group) => (
            <label key={group} className="flex flex-col gap-1 text-xs text-slate-400">
              <span>
                {GROUP_ICONS[group] ?? "•"} {t(`cam_group_${group}`)}
              </span>
              <select
                value={value[group] ?? ""}
                onChange={(e) => set(group, e.target.value)}
                className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
              >
                <option value="">{t("cam_any")}</option>
                {catalog[group].map((key) => (
                  <option key={key} value={key}>
                    {t(`cam_${group}_${key}`)}
                  </option>
                ))}
              </select>
            </label>
          ))}
          {activeCount > 0 && (
            <button onClick={reset} className="text-[10px] text-slate-400 hover:text-slate-200 self-end">
              {t("cam_reset")}
            </button>
          )}
        </div>
      )}
    </div>
  )
}
