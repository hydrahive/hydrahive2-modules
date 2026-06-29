import { useState } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi } from "./api"
import { CameraControls } from "./CameraControls"
import type { AtelierCharacter, AtelierCI, PresetCatalog } from "./types"

interface Props {
  projectId: string
  ci: AtelierCI
  characters: AtelierCharacter[]
  selectedIds: string[]
  presets: PresetCatalog
  onGenerated: () => void
}

const MODELS = [
  "google/gemini-2.5-flash-image",
  "google/gemini-3-pro-image",
  "openai/gpt-image-1",
  "black-forest-labs/flux.2-max",
  "bytedance-seed/seedream-4.5",
]
const RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4"]

/** Mittlere Spalte: Szene beschreiben + Parameter, dann generieren. */
export function GeneratePanel({ projectId, ci, characters, selectedIds, presets, onGenerated }: Props) {
  const { t } = useTranslation("atelier")
  const [scene, setScene] = useState("")
  const [model, setModel] = useState("")
  const [ratio, setRatio] = useState("")
  const [seed, setSeed] = useState<string>("")
  const [camera, setCamera] = useState<Record<string, string>>({})
  const [style, setStyle] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const chosen = characters.filter((c) => selectedIds.includes(c.id))
  const styleKeys = presets.style ?? []

  async function generate() {
    setBusy(true)
    setError(null)
    try {
      await atelierApi.generate(projectId, {
        scene,
        character_ids: selectedIds,
        model: model || undefined,
        aspect_ratio: ratio || undefined,
        seed: seed ? Number(seed) : undefined,
        camera: Object.keys(camera).length > 0 ? camera : undefined,
        style: style || undefined,
      })
      onGenerated()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-sm font-semibold text-slate-200">{t("generate")}</h3>

      <div className="text-xs text-slate-400">
        {chosen.length > 0 ? (
          <span>
            {t("using_characters")}:{" "}
            <span className="text-emerald-400">{chosen.map((c) => c.name).join(", ")}</span>
          </span>
        ) : (
          <span className="text-amber-400">{t("no_character_selected")}</span>
        )}
      </div>

      <textarea
        value={scene}
        onChange={(e) => setScene(e.target.value)}
        placeholder={t("scene_placeholder")}
        rows={4}
        className="text-sm px-3 py-2 rounded bg-slate-800 border border-slate-700 text-slate-100 resize-y"
      />

      {styleKeys.length > 0 && (
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          🎨 {t("style")}
          <select
            value={style}
            onChange={(e) => setStyle(e.target.value)}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
          >
            <option value="">{t("style_none")}</option>
            {styleKeys.map((k) => (
              <option key={k} value={k}>{t(`style_${k}`)}</option>
            ))}
          </select>
        </label>
      )}

      <div className="grid grid-cols-2 gap-2">
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t("model")}
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
          >
            <option value="">{ci.default_model || MODELS[0]} ({t("default")})</option>
            {MODELS.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-xs text-slate-400">
          {t("aspect_ratio")}
          <select
            value={ratio}
            onChange={(e) => setRatio(e.target.value)}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
          >
            <option value="">{ci.aspect_ratio || "1:1"} ({t("default")})</option>
            {RATIOS.map((r) => (
              <option key={r} value={r}>{r}</option>
            ))}
          </select>
        </label>
      </div>

      <label className="flex flex-col gap-1 text-xs text-slate-400">
        {t("seed_optional")}
        <input
          type="number"
          value={seed}
          onChange={(e) => setSeed(e.target.value)}
          placeholder={t("seed_hint")}
          className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100"
        />
      </label>

      {Object.keys(presets).length > 0 && (
        <CameraControls catalog={presets} value={camera} onChange={setCamera} />
      )}

      {error && <div className="text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">{error}</div>}

      <button
        onClick={generate}
        disabled={busy}
        className="px-4 py-2 rounded bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-sm font-medium"
      >
        {busy ? t("generating") : t("generate_button")}
      </button>
    </div>
  )
}
