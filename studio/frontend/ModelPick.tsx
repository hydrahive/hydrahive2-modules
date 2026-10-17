import { useState } from "react"
import { Loader2 } from "lucide-react"
import { useTranslation } from "react-i18next"
import { fieldCls, Label } from "./formParts"
import { modelOptions, SEARCH_FROM, type Catalog, type ModelKind } from "./modelCatalog"

interface Props {
  kind: ModelKind
  value: string
  catalog: Catalog | null
  onChange: (v: string) => void
}

/** Ein Modell fürs Drehbuch: Auswahl aus dem Katalog („Standard“ = leer). Ohne Katalog ein Textfeld mit Hinweis. */
export function ModelPick({ kind, value, catalog, onChange }: Props) {
  const { t } = useTranslation("studio")
  const [q, setQ] = useState("")
  const name = `model_${kind}`
  let body: React.ReactNode
  if (!catalog) {
    body = <p className="mt-1 flex items-center gap-1.5 text-[11px] text-[#68758a]"><Loader2 size={11} className="animate-spin" /> {t("loading")}</p>
  } else if (!catalog.models.length) {
    body = (
      <>
        <input value={value} maxLength={200} onChange={(e) => onChange(e.target.value)} data-field={name} className={fieldCls} />
        <p className="mt-1 text-[10px] leading-relaxed text-[#68758a]">{t("model_catalog_empty")}</p>
      </>
    )
  } else {
    const groups = modelOptions(catalog, value, q)
    body = (
      <>
        {catalog.models.length >= SEARCH_FROM && (
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("model_search")} data-model-search={kind}
            className={`${fieldCls} py-0.5 text-[11px]`} />
        )}
        <select value={value} onChange={(e) => onChange(e.target.value)} data-field={name} className={fieldCls}>
          <option value="">{t("model_default", { model: catalog.default || t("model_auto") })}</option>
          {groups.map((g) => (
            <optgroup key={g.group} label={g.group === "kept" ? t("model_group_kept") : g.group === "cloud" ? t("model_group_cloud")
              : t("model_group_local", { device: g.group.slice(6) || t("model_local_device") })}>
              {g.models.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </optgroup>
          ))}
        </select>
      </>
    )
  }
  return <label className="block" data-model-pick={kind}><Label>{t(`gen.${kind}`)}</Label>{body}</label>
}
