import { useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { akteApi, type AkteEntityKey, type AkteRecord } from "../api"
import { useAkteSchema } from "../useAkteSchema"
import { VerifyBadge } from "../components/VerifyBadge"
import { ResourceTable } from "../components/ResourceTable"
import { AkteEntryModal } from "../components/AkteEntryModal"

interface Column<T> {
  key: string
  label: string
  render?: (row: T) => React.ReactNode
}

interface Props {
  entity: AkteEntityKey
  statusFilter?: string
}

export function AkteEntityList({ entity, statusFilter }: Props) {
  const { t } = useTranslation("akte")
  const schema = useAkteSchema()
  const [rows, setRows] = useState<AkteRecord[] | null>(null)
  const [search, setSearch] = useState("")
  const [deleting, setDeleting] = useState<string | null>(null)
  const [modal, setModal] = useState<{ existing?: AkteRecord } | null>(null)

  const entitySchema = schema?.entities[entity]

  const load = () => {
    akteApi.listEntity(entity, { q: search || undefined, status: statusFilter }, entitySchema?.label_fields)
      .then(setRows)
      .catch(() => setRows([]))
  }

  useEffect(() => {
    if (entitySchema) load()
  }, [entity, search, statusFilter, entitySchema])

  const handleVerify = async (eid: string) => {
    await akteApi.verifyEntity(entity, eid)
    setRows((prev) => prev?.map((r) => r.id === eid ? { ...r, verifiziert: 1 } : r) ?? null)
  }

  const handleDelete = async (eid: string) => {
    if (!confirm(t("akte.delete_confirm"))) return
    setDeleting(eid)
    try {
      await akteApi.deleteEntity(entity, eid)
      setRows((prev) => prev?.filter((r) => r.id !== eid) ?? null)
    } finally {
      setDeleting(null)
    }
  }

  if (!entitySchema || rows === null) {
    return <div className="h-48 rounded-xl bg-[rgb(var(--hh-s-box,21_28_43)/0.5)] animate-pulse" />
  }

  const { label, list_columns, ui_fields } = entitySchema

  const fieldLabel = (key: string) =>
    ui_fields.find((f) => f.key === key)?.label ?? key

  const labelCol: Column<AkteRecord> = {
    key: "label",
    label: fieldLabel(entitySchema.label_fields[0] ?? "label"),
    render: (r) => <span className="text-[#e8eef8]">{r.label}</span>,
  }

  const dataCols: Column<AkteRecord>[] = list_columns.map((col) => ({
    key: col,
    label: fieldLabel(col),
    render: (r) => (
      <span className="text-[#c8d2df] text-xs">
        {(r.record as Record<string, unknown>)[col]?.toString() ?? "—"}
      </span>
    ),
  }))

  const dateCol: Column<AkteRecord> = {
    key: "sort_date",
    label: "Datum",
    render: (r) => (
      <span className="text-[#9aa7bc] text-xs">
        {r.sort_date ? new Date(r.sort_date).toLocaleDateString("de-DE") : "—"}
      </span>
    ),
  }

  const actionCol: Column<AkteRecord> = {
    key: "_actions",
    label: "",
    render: (r) => (
      <div className="flex items-center gap-2">
        {r.verifiziert ? (
          <VerifyBadge verifiziert={r.verifiziert} />
        ) : (
          <button
            onClick={() => handleVerify(r.id)}
            className="text-orange-400 cursor-pointer hover:text-orange-300"
            title="Zum Verifizieren klicken"
          >
            ●
          </button>
        )}
        <button
          onClick={() => setModal({ existing: r })}
          className="text-[#9aa7bc] hover:text-[#c8d2df] text-xs transition-colors"
          title={t("akte.edit_title")}
        >
          ✎
        </button>
        <button
          onClick={() => handleDelete(r.id)}
          disabled={deleting === r.id}
          className="text-[#9aa7bc] hover:text-red-400 text-xs transition-colors disabled:opacity-50"
          title={t("akte.delete_title")}
        >
          ✕
        </button>
      </div>
    ),
  }

  const columns = [labelCol, ...dataCols, dateCol, actionCol]

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-base font-semibold text-[#e8eef8]">{label}</h2>
        <span className="text-xs text-[#9aa7bc]">({rows.length})</span>
        <input
          type="search"
          placeholder={t("akte.search_placeholder")}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ml-auto rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-innen,17_24_39))] px-3 py-1.5 text-sm text-[#e8eef8] placeholder-[#9aa7bc] w-48"
        />
        <button
          onClick={() => setModal({})}
          className="rounded-lg bg-rose-500/20 border border-rose-500/30 text-rose-300 px-3 py-1.5 text-sm font-medium hover:bg-rose-500/30 transition-colors whitespace-nowrap"
        >
          + Neu
        </button>
      </div>
      <ResourceTable
        rows={rows}
        columns={columns}
        emptyText={`Keine ${label} vorhanden`}
      />
      {modal && (
        <AkteEntryModal
          entity={entity}
          title={label}
          fields={ui_fields}
          existing={modal.existing}
          onClose={() => setModal(null)}
          onSaved={load}
        />
      )}
    </div>
  )
}
