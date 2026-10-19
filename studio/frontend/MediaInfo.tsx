import { useTranslation } from "react-i18next"
import type { LibraryItem } from "./api"
import { formatSize } from "./libraryView"
import { MediaActions } from "./MediaActions"

const label = "block text-[10px] font-bold uppercase tracking-wide text-[#68758a]"

/** Rechts: Angaben zum gewählten Medium der Bibliothek (oder ein Hinweis, wenn nichts gewählt ist). */
export function MediaInfo({ item, onDelete }: { item: LibraryItem | null; onDelete?: (item: LibraryItem) => void }) {
  const { t } = useTranslation("studio")
  return (
    <section className="flex h-full min-h-0 flex-col overflow-y-auto p-3" data-studio-panel="inspector">
      <h2 className="text-[11px] font-black uppercase tracking-[0.14em] text-[#68758a]">{t("properties")}</h2>
      {item ? <><ItemInfo item={item} />{onDelete && <MediaActions item={item} onDelete={() => onDelete(item)} />}</> : <p className="mt-3 text-xs text-[#68758a]">{t("pick_medium")}</p>}
    </section>
  )
}

function ItemInfo({ item }: { item: LibraryItem }) {
  const { t } = useTranslation("studio")
  const rows: [string, string][] = [
    [t("info.kind"), t(`kind.${item.kind}`)],
    [t("info.source"), t(`source.${item.source}`)],
    [t("info.origin"), t(`origin.${item.origin}`)],
    [t("info.created"), item.created_at.slice(0, 16).replace("T", " ")],
    ...(item.kind !== "element" ? [[t("info.size"), formatSize(item.size)] as [string, string]] : []),
    ...(item.duration ? [[t("length"), `${item.duration} s`] as [string, string]] : []),
    ...(item.model ? [[t("model"), item.model] as [string, string]] : []),
  ]
  return (
    <div className="mt-3 space-y-3 text-xs" data-studio-info={item.id}>
      <p className="break-words font-bold text-[#e8eef8]">{item.name}</p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
        {rows.map(([k, v]) => (
          <div key={k} className="contents"><dt className="text-[#8d9ab0]">{k}</dt><dd className="break-all text-right text-[#e8eef8]">{v}</dd></div>
        ))}
      </dl>
      {item.prompt && (
        <div><span className={label}>{t("prompt")}</span><p className="mt-1 whitespace-pre-wrap rounded-[4px] bg-[#111827] p-2 text-[#c3ccdd]">{item.prompt}</p></div>
      )}
    </div>
  )
}
