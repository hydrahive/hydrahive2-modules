import { useTranslation } from "react-i18next"
import { MoonStar, PlugZap, Save } from "lucide-react"
import type { VitrineStatus } from "./api"
import type { LightStatus } from "./light"
import { toPicker } from "./light"
import { statusLabel } from "./rules"

/** Kompakter Kopf (immer sichtbar): kleine Vorschau, Zustand, Licht-Punkt, Speichern. */
export function VitrineHeader({ st, light, previewUrl, dirty, invalid, saving, saveMsg, onSave }: {
  st: VitrineStatus | null; light: LightStatus | null; previewUrl: string
  dirty: boolean; invalid: boolean; saving: boolean; saveMsg: { ok: boolean; text: string } | null; onSave: () => void
}) {
  const { t } = useTranslation("vitrine")
  const { text, ok } = statusLabel(t, st)
  const lit = light?.available && light.device && light.state && light.state !== "disabled"
  return (
    <header className="flex flex-wrap items-center gap-3">
      <img src={previewUrl} alt="" aria-hidden className="h-16 w-9 shrink-0 rounded-[3px] border border-[#2a364b] bg-black object-cover" />
      <div className="min-w-0">
        <p className="font-mono text-[10px] uppercase tracking-[0.16em] text-[#69d7ff]">{t("eyebrow")}</p>
        <h1 className="text-xl font-black tracking-tight text-[#e8eef8]">{t("title")}</h1>
        <p className={`flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs ${ok ? "text-emerald-300" : "text-amber-300"}`}>
          <span className="flex items-center gap-1">{st?.night ? <MoonStar size={12} /> : <PlugZap size={12} />}{text}</span>
          {st?.video && <span className="truncate text-[#8d9ab0]">{st.video}</span>}
          {lit && (
            <span className="flex items-center gap-1 text-[#8d9ab0]" title={t("light_title")}>
              <span className="h-2.5 w-2.5 rounded-full border border-white/20" style={{ background: light.effect === "off" || !light.color ? "#000" : toPicker(light.color) }} />
              {t(`light_state_${light.state}`, { defaultValue: light.state ?? "" })}
            </span>
          )}
        </p>
      </div>
      <div className="ml-auto flex items-center gap-2">
        {saveMsg ? <span className={`text-xs ${saveMsg.ok ? "text-emerald-300" : "text-rose-300"}`}>{saveMsg.text}</span>
          : dirty && <span className="text-xs text-amber-200">{t("unsaved")}</span>}
        <button type="button" onClick={onSave} disabled={!dirty || invalid || saving}
          className="flex items-center gap-1.5 rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1.5 text-sm font-semibold text-[#69d7ff] disabled:opacity-40">
          <Save size={14} />{saving ? t("saving") : t("save")}
        </button>
      </div>
    </header>
  )
}
