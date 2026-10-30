import { AlertTriangle, Check, Copy, Loader2, Magnet, Redo2, RefreshCw, Scissors, Trash2, Undo2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import type { EditAction } from "./cutKeys"
import type { SaveState } from "./cutSave"

interface Props {
  save: SaveState
  selected: string | null
  canUndo: boolean
  canRedo: boolean
  canSplit: boolean
  snap: boolean
  onAction: (a: EditAction) => void
  onSnap: () => void
  onReload: () => void
}

const btn = "rounded-[4px] p-1 hover:bg-[rgb(var(--hh-s-hebung,17_24_39))] hover:text-[#e8eef8] disabled:opacity-30 disabled:hover:bg-transparent"

/** Werkzeuge der Zeitleiste (4b) und Speicherstand. Jeder Knopf hat auch ein Tastenkürzel. */
export function CutToolbar({ save, selected, canUndo, canRedo, canSplit, snap, onAction, onSnap, onReload }: Props) {
  const { t } = useTranslation("studio")
  const b = (a: EditAction["kind"], icon: React.ReactNode, title: string, disabled: boolean) => (
    <button type="button" className={btn} title={title} aria-label={title} disabled={disabled} data-cut-action={a}
      onClick={() => onAction({ kind: a } as EditAction)}>{icon}</button>
  )
  return (
    <span className="ml-2 flex items-center gap-0.5 border-l border-[rgb(var(--hh-s-rand,42_54_75))] pl-2">
      {b("split", <Scissors size={13} />, t("action.split"), !canSplit)}
      {b("delete", <Trash2 size={13} />, t("action.delete"), !selected)}
      {b("duplicate", <Copy size={13} />, t("action.duplicate"), !selected)}
      <span className="mx-1 h-4 w-px bg-[rgb(var(--hh-s-rand,42_54_75))]" />
      {b("undo", <Undo2 size={13} />, t("action.undo"), !canUndo)}
      {b("redo", <Redo2 size={13} />, t("action.redo"), !canRedo)}
      <button type="button" onClick={onSnap} aria-pressed={snap} data-cut-snap title={t("action.toggle-snap")} aria-label={t("action.toggle-snap")}
        className={`${btn} ${snap ? "text-[#69d7ff]" : ""}`}><Magnet size={13} /></button>
      <span className={`ml-2 flex items-center gap-1 text-[10px] ${save === "conflict" || save === "error" ? "text-[#ff6b8a]" : "text-[#9aa7bc]"}`} data-cut-save={save}>
        {save === "saving" ? <Loader2 size={11} className="animate-spin" /> : save === "saved" ? <Check size={11} /> : save === "dirty" ? null : <AlertTriangle size={11} />}
        {t(`cut_save.${save}`)}
      </span>
      {save === "conflict" && (
        <button type="button" onClick={onReload} data-cut-reload className="ml-1 flex items-center gap-1 rounded-[4px] border border-[#ff6b8a]/50 px-1.5 py-0.5 text-[10px] font-bold text-[#ff6b8a] hover:bg-[#ff6b8a]/10">
          <RefreshCw size={10} /> {t("reload")}
        </button>
      )}
    </span>
  )
}
