import { useEffect, useState, useCallback } from "react"
import { useTranslation } from "react-i18next"
import { atelierApi } from "./api"
import { CameraControls } from "./CameraControls"
import type { AtelierCharacter, MediaModel, PresetCatalog, Scene, Screenplay, SceneInput } from "./types"

interface Props {
  projectId: string
  characters: AtelierCharacter[]
  presets: PresetCatalog
}

const EMPTY_SCENE: SceneInput = {
  title: "",
  description: "",
  character_ids: [],
  dialogues: [],
  music: { enabled: false, prompt: "", music_rel: null },
  camera: {},
  location: "",
  time_of_day: "",
}

/** Regie-Tab: Drehbuch-Kopf + Szenen-Liste (Beschreibung, Charaktere, Dialoge,
 *  Musik, Kamera-Presets) mit Reorder. Reiner Planer (E1-Backend) — noch kein
 *  Regieagent / Render (folgt in E4/E5). */
export function ScreenplayPanel({ projectId, characters, presets }: Props) {
  const { t } = useTranslation("atelier")
  const [head, setHead] = useState<Screenplay | null>(null)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [headDirty, setHeadDirty] = useState(false)
  const [savingHead, setSavingHead] = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [videoModels, setVideoModels] = useState<MediaModel[]>([])
  const [audioModels, setAudioModels] = useState<MediaModel[]>([])

  useEffect(() => {
    atelierApi.mediaModels("video").then((r) => setVideoModels(r.models)).catch(() => setVideoModels([]))
    atelierApi.mediaModels("audio").then((r) => setAudioModels(r.models)).catch(() => setAudioModels([]))
  }, [])

  const reload = useCallback(async () => {
    if (!projectId) return
    const [sp, sc] = await Promise.all([
      atelierApi.getScreenplay(projectId),
      atelierApi.listScenes(projectId),
    ])
    setHead(sp)
    setScenes(sc)
    setHeadDirty(false)
  }, [projectId])

  useEffect(() => { reload() }, [reload])

  function patchHead(patch: Partial<Screenplay>) {
    setHead((h) => (h ? { ...h, ...patch } : h))
    setHeadDirty(true)
  }

  async function saveHead() {
    if (!head) return
    setSavingHead(true)
    try {
      const saved = await atelierApi.saveScreenplay(projectId, head)
      setHead(saved)
      setHeadDirty(false)
    } finally {
      setSavingHead(false)
    }
  }

  async function addScene() {
    const created = await atelierApi.createScene(projectId, {
      ...EMPTY_SCENE,
      title: `${t("scene_word")} ${scenes.length + 1}`,
    })
    setScenes((s) => [...s, created])
    setExpanded(created.id)
  }

  async function saveScene(id: string, patch: Partial<SceneInput>) {
    const updated = await atelierApi.updateScene(projectId, id, patch)
    setScenes((s) => s.map((x) => (x.id === id ? updated : x)))
  }

  async function removeScene(id: string) {
    if (!confirm(t("scene_delete_confirm"))) return
    await atelierApi.deleteScene(projectId, id)
    setScenes((s) => s.filter((x) => x.id !== id))
    if (expanded === id) setExpanded(null)
  }

  async function move(index: number, dir: -1 | 1) {
    const next = [...scenes]
    const target = index + dir
    if (target < 0 || target >= next.length) return
    ;[next[index], next[target]] = [next[target], next[index]]
    setScenes(next)
    await atelierApi.reorderScenes(projectId, next.map((s) => s.id))
  }

  if (!head) return <div className="text-slate-400 text-sm p-2">{t("saving")}</div>

  return (
    <div className="flex flex-col gap-4">
      {/* Drehbuch-Kopf */}
      <div className="rounded-lg border border-slate-700 bg-slate-900/40 p-3 flex flex-col gap-2">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-slate-200">🎬 {t("regie_head")}</h2>
          <button
            onClick={saveHead}
            disabled={!headDirty || savingHead}
            className="text-xs px-3 py-1 rounded bg-emerald-600 text-white disabled:opacity-40"
          >
            {savingHead ? t("saving") : t("save")}
          </button>
        </div>
        <input
          value={head.title}
          onChange={(e) => patchHead({ title: e.target.value })}
          placeholder={t("regie_title_placeholder")}
          className="px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-slate-100 text-sm"
        />
        <input
          value={head.logline}
          onChange={(e) => patchHead({ logline: e.target.value })}
          placeholder={t("regie_logline_placeholder")}
          className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs"
        />
        <textarea
          value={head.description}
          onChange={(e) => patchHead({ description: e.target.value })}
          placeholder={t("regie_description_placeholder")}
          rows={3}
          className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs resize-y"
        />
        <div className="grid grid-cols-2 gap-2">
          <label className="flex flex-col gap-0.5 text-[11px] text-slate-400">
            {t("regie_film_model")}
            <ModelSelect
              value={head.film_model}
              models={videoModels}
              placeholder="google/veo-3.1"
              onChange={(v) => patchHead({ film_model: v })}
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] text-slate-400">
            {t("regie_audio_model")}
            <ModelSelect
              value={head.audio_model}
              models={audioModels}
              placeholder="google/lyria-3-pro-preview"
              onChange={(v) => patchHead({ audio_model: v })}
            />
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] text-slate-400">
            {t("regie_aspect")}
            <select
              value={head.aspect_ratio}
              onChange={(e) => patchHead({ aspect_ratio: e.target.value })}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 text-xs"
            >
              {["16:9", "9:16", "1:1", "4:3", "21:9"].map((a) => (
                <option key={a} value={a}>{a}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-0.5 text-[11px] text-slate-400">
            {t("regie_default_duration")}
            <input
              type="number"
              min={1}
              max={60}
              value={head.default_duration}
              onChange={(e) => patchHead({ default_duration: Number(e.target.value) })}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 text-xs"
            />
          </label>
        </div>
      </div>

      {/* Szenen */}
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-200">
          {t("scenes_word")} <span className="text-slate-500">({scenes.length})</span>
        </h2>
        <button onClick={addScene} className="text-xs px-3 py-1 rounded bg-slate-700 text-slate-100 hover:bg-slate-600">
          ＋ {t("scene_add")}
        </button>
      </div>

      {scenes.length === 0 && (
        <div className="text-slate-500 text-xs p-3 text-center border border-dashed border-slate-700 rounded">
          {t("scenes_empty")}
        </div>
      )}

      {scenes.map((scene, i) => (
        <SceneCard
          key={scene.id}
          index={i}
          total={scenes.length}
          scene={scene}
          characters={characters}
          presets={presets}
          expanded={expanded === scene.id}
          onToggle={() => setExpanded((e) => (e === scene.id ? null : scene.id))}
          onSave={(patch) => saveScene(scene.id, patch)}
          onDelete={() => removeScene(scene.id)}
          onMove={(dir) => move(i, dir)}
        />
      ))}
    </div>
  )
}

interface SceneCardProps {
  index: number
  total: number
  scene: Scene
  characters: AtelierCharacter[]
  presets: PresetCatalog
  expanded: boolean
  onToggle: () => void
  onSave: (patch: Partial<SceneInput>) => void
  onDelete: () => void
  onMove: (dir: -1 | 1) => void
}

function SceneCard({
  index, total, scene, characters, presets, expanded, onToggle, onSave, onDelete, onMove,
}: SceneCardProps) {
  const { t } = useTranslation("atelier")
  const [draft, setDraft] = useState<Scene>(scene)

  useEffect(() => { setDraft(scene) }, [scene])

  function patch(p: Partial<Scene>) { setDraft((d) => ({ ...d, ...p })) }

  function toggleChar(id: string) {
    patch({
      character_ids: draft.character_ids.includes(id)
        ? draft.character_ids.filter((x) => x !== id)
        : [...draft.character_ids, id],
    })
  }

  function setDialogue(idx: number, field: keyof Scene["dialogues"][number], val: string) {
    const dl = draft.dialogues.map((d, j) => (j === idx ? { ...d, [field]: val } : d))
    patch({ dialogues: dl })
  }
  function addDialogue() {
    patch({ dialogues: [...draft.dialogues, { character_id: "", line: "", emotion: "" }] })
  }
  function removeDialogue(idx: number) {
    patch({ dialogues: draft.dialogues.filter((_, j) => j !== idx) })
  }

  function save() {
    onSave({
      title: draft.title,
      description: draft.description,
      character_ids: draft.character_ids,
      dialogues: draft.dialogues.filter((d) => d.line.trim()),
      music: draft.music,
      camera: draft.camera,
      location: draft.location,
      time_of_day: draft.time_of_day,
    })
  }

  const charName = (id: string) => characters.find((c) => c.id === id)?.name || t("untitled")

  return (
    <div className="rounded-lg border border-slate-700 bg-slate-900/40">
      <div className="flex items-center gap-2 px-3 py-2">
        <div className="flex flex-col">
          <button onClick={() => onMove(-1)} disabled={index === 0}
            className="text-slate-500 hover:text-slate-200 disabled:opacity-20 leading-none text-[10px]">▲</button>
          <button onClick={() => onMove(1)} disabled={index === total - 1}
            className="text-slate-500 hover:text-slate-200 disabled:opacity-20 leading-none text-[10px]">▼</button>
        </div>
        <span className="text-[10px] text-slate-500 w-5">{index + 1}</span>
        <button onClick={onToggle} className="flex-1 text-left text-sm text-slate-200 truncate">
          {draft.title || t("untitled")}
          {draft.character_ids.length > 0 && (
            <span className="ml-2 text-[10px] text-slate-500">
              👤 {draft.character_ids.length}
            </span>
          )}
          {draft.music.enabled && <span className="ml-1 text-[10px]">🎵</span>}
        </button>
        <button onClick={onDelete} className="text-slate-500 hover:text-rose-400 text-xs">✕</button>
        <span className="text-slate-500 text-xs">{expanded ? "▾" : "▸"}</span>
      </div>

      {expanded && (
        <div className="px-3 pb-3 flex flex-col gap-2 border-t border-slate-800 pt-2">
          <input
            value={draft.title}
            onChange={(e) => patch({ title: e.target.value })}
            placeholder={t("scene_title_placeholder")}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 text-xs"
          />
          <textarea
            value={draft.description}
            onChange={(e) => patch({ description: e.target.value })}
            placeholder={t("scene_description_placeholder")}
            rows={2}
            className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs resize-y"
          />
          <div className="grid grid-cols-2 gap-2">
            <input
              value={draft.location}
              onChange={(e) => patch({ location: e.target.value })}
              placeholder={t("scene_location")}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs"
            />
            <input
              value={draft.time_of_day}
              onChange={(e) => patch({ time_of_day: e.target.value })}
              placeholder={t("scene_time")}
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs"
            />
          </div>

          {/* Charaktere */}
          <div className="flex flex-col gap-1">
            <span className="text-[11px] text-slate-400">{t("scene_characters")}</span>
            <div className="flex flex-wrap gap-1">
              {characters.length === 0 && <span className="text-[10px] text-slate-500">{t("no_characters")}</span>}
              {characters.map((c) => (
                <button
                  key={c.id}
                  onClick={() => toggleChar(c.id)}
                  className={`text-[11px] px-2 py-0.5 rounded-full border ${
                    draft.character_ids.includes(c.id)
                      ? "bg-emerald-600/30 border-emerald-500 text-emerald-200"
                      : "border-slate-600 text-slate-400 hover:border-slate-400"
                  }`}
                >
                  {c.name || t("untitled")}
                </button>
              ))}
            </div>
          </div>

          {/* Dialoge */}
          <div className="flex flex-col gap-1">
            <div className="flex items-center justify-between">
              <span className="text-[11px] text-slate-400">{t("scene_dialogues")}</span>
              <button onClick={addDialogue} className="text-[10px] text-slate-400 hover:text-slate-200">＋ {t("scene_dialogue_add")}</button>
            </div>
            {draft.dialogues.map((d, j) => (
              <div key={j} className="flex gap-1 items-start">
                <select
                  value={d.character_id}
                  onChange={(e) => setDialogue(j, "character_id", e.target.value)}
                  className="px-1 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-[10px] w-24 shrink-0"
                >
                  <option value="">—</option>
                  {draft.character_ids.map((id) => (
                    <option key={id} value={id}>{charName(id)}</option>
                  ))}
                </select>
                <input
                  value={d.line}
                  onChange={(e) => setDialogue(j, "line", e.target.value)}
                  placeholder={t("scene_dialogue_line")}
                  className="flex-1 px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-200 text-xs"
                />
                <input
                  value={d.emotion}
                  onChange={(e) => setDialogue(j, "emotion", e.target.value)}
                  placeholder={t("scene_dialogue_emotion")}
                  className="w-20 px-1 py-1 rounded bg-slate-800 border border-slate-700 text-slate-400 text-[10px] shrink-0"
                />
                <button onClick={() => removeDialogue(j)} className="text-slate-500 hover:text-rose-400 text-xs px-1">✕</button>
              </div>
            ))}
          </div>

          {/* Musik */}
          <div className="flex flex-col gap-1">
            <label className="flex items-center gap-2 text-[11px] text-slate-400">
              <input
                type="checkbox"
                checked={draft.music.enabled}
                onChange={(e) => patch({ music: { ...draft.music, enabled: e.target.checked } })}
              />
              🎵 {t("scene_music")}
            </label>
            {draft.music.enabled && (
              <input
                value={draft.music.prompt}
                onChange={(e) => patch({ music: { ...draft.music, prompt: e.target.value } })}
                placeholder={t("scene_music_placeholder")}
                className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 text-xs"
              />
            )}
          </div>

          {/* Kamera-Presets */}
          <CameraControls
            catalog={presets}
            value={draft.camera}
            onChange={(camera) => patch({ camera })}
          />

          <div className="flex justify-end">
            <button onClick={save} className="text-xs px-3 py-1 rounded bg-emerald-600 text-white">
              {t("scene_save")}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

interface ModelSelectProps {
  value: string
  models: MediaModel[]
  placeholder: string
  onChange: (value: string) => void
}

/** Dropdown der Live-Modelle (OpenRouter). Ist die Liste leer (kein Key /
 *  Ladefehler), wird ein Freitext-Feld gezeigt. Ein gespeicherter Wert, der
 *  nicht in der Liste steht, bleibt als eigene Option erhalten (kein Datenverlust). */
function ModelSelect({ value, models, placeholder, onChange }: ModelSelectProps) {
  const { t } = useTranslation("atelier")
  const inputCls = "px-2 py-1 rounded bg-slate-800 border border-slate-700 text-slate-100 text-xs font-mono"

  if (models.length === 0) {
    return (
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={inputCls}
      />
    )
  }

  const known = models.some((m) => m.id === value)
  return (
    <select value={value} onChange={(e) => onChange(e.target.value)} className={inputCls}>
      <option value="">{t("model_auto_default")}</option>
      {value && !known && <option value={value}>{value}</option>}
      {models.map((m) => (
        <option key={m.id} value={m.id}>{m.name || m.id}</option>
      ))}
    </select>
  )
}
