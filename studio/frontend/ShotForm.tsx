import { useState } from "react"
import { useTranslation } from "react-i18next"
import type { Job, PlanElement, Shot } from "./planApi"
import { ShotCast } from "./ShotCast"
import { ShotImage } from "./ShotImage"
import { ShotSpeech } from "./ShotSpeech"
import { ShotVideo } from "./ShotVideo"
import { Field, FormActions, Label, fieldCls } from "./formParts"
import { shotChanges } from "./planLogic"

interface Props {
  shot: Shot
  index: number
  elements: PlanElement[]
  /** nicht mehr benutzt (C2: jeder Baustein darf in den Shot) – bleibt für ältere Aufrufer */
  sceneElementIds?: string[]
  presets: string[]
  busy: boolean
  onSave: (s: Partial<Shot>) => void
  onDelete: () => void
  base?: string
  job?: Job | null
  onGenerate?: () => void
  onChoose?: (rel: string) => void
  videoJob?: Job | null
  onVideo?: () => void
  /** 5c: Stimmen des Sprachmodells (leer = nur Standardstimme, null = lädt noch), Sprache erzeugen. */
  voices?: string[] | null
  speechJob?: Job | null
  onSpeech?: () => void
  /** C1: Bild/Video des Shots löschen (mit Rückfrage) */
  onDeleteMedia?: (rel: string) => void
  /** C3: Modelle des Drehbuchs für die Kosten-Hinweise */
  models?: { image?: string; video?: string; voice?: string }
}

/** Planen, rechts: ein Shot (Kamera, Beschreibung, Bausteine der Szene, Dauer). Status und Medien ändert das Erzeugen. */
export function ShotForm({ shot, index, elements, presets, busy, onSave, onDelete, base = "", job = null, onGenerate, onChoose, videoJob = null, onVideo,
  voices = [], speechJob = null, onSpeech, onDeleteMedia, models = {} }: Props) {
  const { t } = useTranslation("studio")
  const [s, setS] = useState(shot)
  const dirty = JSON.stringify(s) !== JSON.stringify(shot)
  const toggle = (id: string) => setS((x) => ({ ...x, element_ids: x.element_ids.includes(id) ? x.element_ids.filter((y) => y !== id) : [...x.element_ids, id] }))
  return (
    <div className="mt-3 space-y-3 text-xs" data-plan-form="shot">
      <p className="font-bold text-[#e8eef8]">{t("shot", { n: index + 1 })}</p>
      {onGenerate && onChoose && <ShotImage shot={shot} base={base} job={job} onGenerate={onGenerate} onChoose={onChoose} onDelete={onDeleteMedia} model={models.image} />}
      {onVideo && <ShotVideo shot={shot} base={base} job={videoJob} onGenerate={onVideo} onDelete={onDeleteMedia} model={models.video} />}
      <div className="grid grid-cols-2 gap-2">
        <label className="block"><Label>{t("f.camera")}</Label>
          <select value={s.shot} onChange={(e) => setS({ ...s, shot: e.target.value })} className={fieldCls}>
            <option value="">{t("cam_any")}</option>
            {presets.map((v) => <option key={v} value={v}>{t(`cam.shot.${v}`)}</option>)}
          </select>
        </label>
        <label className="block"><Label>{t("f.shot_duration")}</Label>
          <input type="number" min={1} max={60} value={s.duration} className={fieldCls}
            onChange={(e) => setS({ ...s, duration: Math.max(1, Math.min(60, Number(e.target.value) || 1)) })} />
        </label>
      </div>
      <Field name="prompt" label={t("f.shot_prompt")} value={s.prompt} max={2000} rows={5} onChange={(v) => setS({ ...s, prompt: v })} />
      <Field name="speech" label={t("f.speech")} value={s.speech ?? ""} max={1000} rows={3} onChange={(v) => setS({ ...s, speech: v })} />
      {voices === null ? <p className="text-[11px] text-[#9aa7bc]" data-shot-voice-loading>{t("voices_loading")}</p> : voices.length ? (
        <label className="block"><Label>{t("f.voice")}</Label>
          <select value={s.voice ?? ""} onChange={(e) => setS({ ...s, voice: e.target.value })} className={fieldCls} data-shot-voice>
            <option value="">{t("voice_default")}</option>
            {voices.map((v) => <option key={v} value={v}>{v}</option>)}
            {s.voice && !voices.includes(s.voice) && <option value={s.voice}>{s.voice}</option>}
          </select>
        </label>
      ) : <p className="text-[11px] text-[#9aa7bc]">{t("voice_only_default")}</p>}
      {onSpeech && <ShotSpeech shot={shot} base={base} job={speechJob} onGenerate={onSpeech} model={models.voice} />}
      <ShotCast shot={shot} elements={elements} />
      <details>
        <summary className="cursor-pointer text-[11px] text-[#9aa7bc] hover:text-[#e8eef8]">{t("shot_extra_elements")}</summary>
        <div className="mt-1 flex flex-wrap gap-1">
          {elements.map((e) => (
            <label key={e.id} className="flex items-center gap-1 rounded-full bg-[rgb(var(--hh-s-innen,17_24_39))] px-2 py-0.5 text-[11px] text-[#c3ccdd]">
              <input type="checkbox" checked={s.element_ids.includes(e.id)} onChange={() => toggle(e.id)} data-shot-element={e.id} /> {e.name}
            </label>
          ))}
        </div>
      </details>
      <p className="text-[11px] text-[#9aa7bc]">{t("f.status")}: <span className="text-[#e8eef8]">{t(`shot_status.${shot.status}`, { defaultValue: shot.status })}</span></p>
      <FormActions busy={busy} dirty={dirty} onDelete={onDelete}
        onSave={() => onSave(shotChanges(s))} />
    </div>
  )
}
