import { AlertTriangle, Check, Combine, Download, Ear, Loader2, MessageSquareText, Plus, Redo2, Scissors, Trash2, Undo2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { SaveState } from "./cutSave"
import { addCue, cueAt, MIN_CUE, timeText, type Cue, type SubtitleFormat } from "./subtitleLogic"

export type SubAction = "split" | "join" | "delete" | "add" | "undo" | "redo"

interface Props {
  cues: Cue[]
  selected: string | null
  time: number
  hasSpeech: boolean
  busy: boolean
  save: SaveState
  canUndo: boolean
  canRedo: boolean
  onSelect: (id: string) => void
  onChange: (id: string, text: string) => void
  onAction: (a: SubAction) => void
  onFromSpeech: () => void
  onExport: (f: SubtitleFormat) => void
  /** „Aus dem Ton heraushören …“ (6b); während es läuft, ist die Liste gesperrt (der Auftrag ersetzt sie). */
  onHear: () => void
  hearing: boolean
}

const btn = "flex items-center gap-1 rounded-[4px] border border-[#2a364b] px-2 py-1 text-[11px] font-bold text-[#c3ccdd] hover:border-[#46617f] disabled:opacity-40"

/** Reiter „Untertitel“, links: alle Einträge (Zeit, Text), Bearbeiten, Erzeugen aus den Sprechtexten, Herunterladen. */
export function SubtitleList({ cues, selected, time, hasSpeech, busy, save, canUndo, canRedo, onSelect, onChange, onAction, onFromSpeech, onExport, onHear, hearing }: Props) {
  const { t } = useTranslation("studio")
  const sel = cues.find((c) => c.id === selected) ?? null
  const free = !hearing
  const can: Record<SubAction, boolean> = {
    split: free && !!sel && time - sel.start >= MIN_CUE && sel.end - time >= MIN_CUE,
    join: free && !!sel && cues.indexOf(sel) < cues.length - 1,
    delete: free && !!sel,
    add: free && !cueAt(cues, time) && !!addCue(cues, time, "x", () => "x").cue,
    undo: free && canUndo, redo: free && canRedo,
  }
  const tool = (a: SubAction, Icon: typeof Plus) => (
    <button type="button" onClick={() => onAction(a)} disabled={!can[a]} data-sub-action={a} className={btn} title={t(`sub_${a}_hint`)}>
      <Icon size={12} /> {t(`sub_${a}`)}
    </button>
  )
  return (
    <section className="flex h-full min-h-0 flex-col" data-sub-list>
      <div className="flex flex-wrap items-center gap-1.5 border-b border-[#2a364b] p-2">
        <button type="button" onClick={onFromSpeech} disabled={busy || hearing || !hasSpeech} data-sub-from-speech title={t("sub_from_speech_hint")}
          className="flex items-center gap-1.5 rounded-[4px] bg-[#69d7ff] px-2.5 py-1 text-[11px] font-black text-[#08111c] disabled:opacity-40">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <MessageSquareText size={12} />} {t("sub_from_speech")}
        </button>
        <button type="button" onClick={onHear} disabled={busy || hearing} data-sub-hear className={btn} title={t("hear_open_hint")}>
          {hearing ? <Loader2 size={12} className="animate-spin" /> : <Ear size={12} />} {t("hear_open")}
        </button>
        {(["srt", "vtt"] as const).map((f) => (
          <button key={f} type="button" onClick={() => onExport(f)} disabled={!cues.length} data-sub-export={f} className={btn} title={t("sub_export_hint")}>
            <Download size={12} /> {t(`sub_export_${f}`)}
          </button>
        ))}
        <span className={`ml-auto flex items-center gap-1 text-[10px] ${save === "conflict" || save === "error" ? "text-[#ff6b8a]" : "text-[#68758a]"}`} data-sub-save={save}>
          {save === "saving" ? <Loader2 size={11} className="animate-spin" /> : save === "saved" ? <Check size={11} /> : save === "dirty" ? null : <AlertTriangle size={11} />}
          {t(`cut_save.${save}`)}
        </span>
      </div>
      {hearing && <p className="flex items-center gap-1.5 px-3 pt-2 text-[11px] text-[#69d7ff]" data-sub-hearing><Loader2 size={11} className="animate-spin" /> {t("hear_running")}</p>}
      {!hasSpeech && !cues.length && <p className="px-3 pt-2 text-[11px] leading-relaxed text-[#8d9ab0]">{t("sub_no_speech_hint")}</p>}
      <div className="flex flex-wrap gap-1.5 border-b border-[#2a364b] p-2">
        {tool("add", Plus)}{tool("split", Scissors)}{tool("join", Combine)}{tool("delete", Trash2)}{tool("undo", Undo2)}{tool("redo", Redo2)}
      </div>
      <div className="px-3 pt-2 text-[10px] font-bold uppercase tracking-wide text-[#68758a]">{t("sub_count", { count: cues.length })}</div>
      {!cues.length ? <p className="p-3 text-xs leading-relaxed text-[#8d9ab0]">{t("sub_empty")}</p> : (
        <ol className="min-h-0 flex-1 space-y-1 overflow-y-auto p-2">
          {cues.map((c, i) => (
            <li key={c.id} data-sub-cue={c.id} aria-current={c.id === selected ? "true" : undefined} onClick={() => onSelect(c.id)}
              className={`cursor-pointer rounded-[4px] border p-1.5 ${c.id === selected ? "border-[#69d7ff] bg-[#1c2940]" : "border-[#2a364b] bg-[#0d1420] hover:border-[#46617f]"}`}>
              <div className="mb-1 flex items-center gap-2 font-mono text-[10px] text-[#8d9ab0]">
                <span className="text-[#68758a]">{i + 1}</span> {timeText(c.start)} – {timeText(c.end)}
              </div>
              <textarea rows={2} value={c.text} maxLength={200} readOnly={hearing} aria-label={t("sub_text_of", { n: i + 1 })} data-sub-text={c.id}
                onFocus={() => onSelect(c.id)} onChange={(e) => onChange(c.id, e.target.value)}
                className="w-full resize-none rounded-[3px] border border-[#2a364b] bg-[#111827] px-1.5 py-1 text-xs text-[#e8eef8] outline-none focus:border-[#69d7ff]" />
            </li>
          ))}
        </ol>
      )}
    </section>
  )
}
