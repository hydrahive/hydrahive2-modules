/** G6: Kurzhilfe des geführten Wegs – fünf Sätze, je Schritt einer. Eigener Dialog, kein Browser-Popup. */
import { useTranslation } from "react-i18next"
import { Backdrop } from "../StudioDialogs"

export function GuidedHelp({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation("studio")
  return (
    <Backdrop onClose={onClose} label={t("guided.help_title")}>
      <div className="space-y-4 p-5">
        <h2 className="text-lg font-black text-[#f2f6fc]">{t("guided.help_title")}</h2>
        <ol className="space-y-2">
          {[1, 2, 3, 4, 5].map((n) => (
            <li key={n} className="flex gap-3 text-base text-[#c3ccdd]">
              <span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-[#1c2940] text-sm font-black text-[#69d7ff]">{n}</span>
              <span>{t(`guided.help.${n}`)}</span>
            </li>
          ))}
        </ol>
        <div className="flex justify-end">
          <button type="button" onClick={onClose} className="rounded-[8px] bg-[#69d7ff] px-4 py-2 text-sm font-black text-[#06111c]">{t("guided.help_close")}</button>
        </div>
      </div>
    </Backdrop>
  )
}
