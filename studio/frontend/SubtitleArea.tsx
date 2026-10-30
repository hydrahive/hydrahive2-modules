/** Reiter „Untertitel“ (Spec 6a): Zeiten des gewählten Eintrags rechts und Rückfrage vor dem Ersetzen. */
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fieldCls, Label } from "./formParts"
import { Backdrop } from "./StudioDialogs"
import { MIN_CUE, timeText, type Cue } from "./subtitleLogic"

/** Rechts: Zeiten des gewählten Eintrags (Sekunden, auf Zehntel). */
export function SubtitleInspector({ cue, onTime }: { cue: Cue | null; onTime: (id: string, v: { start?: number; end?: number }) => void }) {
  const { t } = useTranslation("studio")
  if (!cue) return <p className="p-3 text-xs leading-relaxed text-[#9aa7bc]" data-sub-inspector>{t("sub_pick")}</p>
  const field = (k: "start" | "end") => (
    <label className="block"><Label>{t(`sub_${k}`)}</Label>
      <input type="number" step={0.1} min={0} value={cue[k]} data-sub-time={k} className={fieldCls}
        onChange={(e) => { const v = Number(e.target.value); if (Number.isFinite(v)) onTime(cue.id, { [k]: v }) }} />
    </label>
  )
  return (
    <div className="space-y-3 p-3 text-xs text-[#c3ccdd]" data-sub-inspector={cue.id}>
      <div className="font-mono text-[11px] text-[#9aa7bc]">{timeText(cue.start)} – {timeText(cue.end)}</div>
      <div className="grid grid-cols-2 gap-2">{field("start")}{field("end")}</div>
      <p className="text-[10px] leading-relaxed text-[#9aa7bc]">{t("sub_time_hint", { min: MIN_CUE })}</p>
    </div>
  )
}

export function ReplaceDialog({ count, busy, onConfirm, onClose }: { count: number; busy: boolean; onConfirm: () => void; onClose: () => void }) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("sub_from_speech")}>
      <div className="space-y-3 p-4 text-xs text-[#c3ccdd]" data-sub-replace-dialog>
        <h3 className="text-sm font-black text-[#e8eef8]">{t("sub_from_speech")}</h3>
        <p className="text-sm text-[#e8eef8]">{t("sub_replace_question", { count })}</p>
        <div className="flex justify-end gap-2">
          <button type="button" onClick={onClose} className="rounded-[4px] px-3 py-1.5 text-[#9aa7bc] hover:text-[#e8eef8]">{t("cancel")}</button>
          <button type="button" onClick={onConfirm} disabled={busy} data-sub-replace
            className="flex items-center gap-1.5 rounded-[4px] bg-[#ff6b8a] px-3 py-1.5 font-black text-[#08111c] disabled:opacity-50">
            {busy && <Loader2 size={13} className="animate-spin" />} {t("sub_replace")}
          </button>
        </div>
      </div>
    </Backdrop>
  )
}
