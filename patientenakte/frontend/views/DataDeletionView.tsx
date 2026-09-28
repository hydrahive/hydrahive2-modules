import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { deletionApi, type DeletionOverview, type DeletionResult, type DeletionScope } from "../deletionApi"
import { DeleteConfirmDialog } from "../components/DeleteConfirmDialog"

interface Pending {
  scope: DeletionScope
  range?: { from: string; to: string }
}

function Card({ title, info, hint, empty, onDelete, children }: {
  title: string; info: string; hint?: string; empty: boolean; onDelete: () => void; children?: React.ReactNode
}) {
  const { t } = useTranslation("akte")
  return (
    <div className="rounded-xl border border-white/[6%] bg-zinc-900/40 p-4 space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-zinc-100">{title}</p>
          <p className="text-xs text-zinc-500">{empty ? t("deletion.nothing") : info}</p>
          {hint && <p className="mt-1 text-xs text-zinc-500">{hint}</p>}
        </div>
        <button onClick={onDelete} disabled={empty}
          className="shrink-0 px-3 py-1.5 rounded-lg text-xs border border-rose-500/30 text-rose-300 hover:bg-rose-500/10 disabled:opacity-30">
          {t("deletion.delete")}
        </button>
      </div>
      {children}
    </div>
  )
}

export function DataDeletionView() {
  const { t } = useTranslation("akte")
  const [ov, setOv] = useState<DeletionOverview | null>(null)
  const [loadError, setLoadError] = useState(false)
  const [from, setFrom] = useState("")
  const [to, setTo] = useState("")
  const [pending, setPending] = useState<Pending | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null)

  const load = useCallback(() => {
    setLoadError(false)
    deletionApi.overview().then(setOv).catch(() => setLoadError(true))
  }, [])
  useEffect(() => { load() }, [load])

  const summarize = (r: DeletionResult) => {
    const parts = Object.entries(r.deleted).map(([k, n]) => `${n} ${t(`deletion.tables.${k}`, { defaultValue: k })}`)
    let text = t("deletion.done", { summary: parts.join(", ") })
    if (r.raw_kept_partial) text += " " + t("deletion.kept_partial", { count: r.raw_kept_partial })
    return text
  }

  const run = async (word: string) => {
    if (!pending) return
    setBusy(true)
    setMessage(null)
    try {
      const result = await deletionApi.remove(pending.scope, word, pending.range)
      setMessage({ ok: true, text: summarize(result) })
      setPending(null)
      load()
    } catch (e) {
      setMessage({ ok: false, text: t("deletion.failed", { error: e instanceof Error ? e.message : String(e) }) })
    } finally {
      setBusy(false)
    }
  }

  if (loadError) return <p className="text-sm text-rose-400">{t("deletion.load_failed")}</p>
  if (!ov) return <p className="text-sm text-zinc-500">{t("deletion.loading")}</p>

  const ah = ov.apple_health
  const rangeSet = from !== "" && to !== ""
  const inputCls = "rounded-lg border border-white/10 bg-zinc-900 px-2 py-1 text-xs text-zinc-200"

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-base font-semibold text-zinc-100">{t("deletion.title")}</h2>
        <p className="text-xs text-zinc-500 mt-1">{t("deletion.subtitle")}</p>
      </div>

      {message && (
        <div className={`rounded-xl border p-3 text-sm ${message.ok
          ? "border-emerald-500/20 bg-emerald-500/[4%] text-emerald-300"
          : "border-rose-500/20 bg-rose-500/[4%] text-rose-300"}`}>{message.text}</div>
      )}
      {busy && <p className="text-xs text-zinc-400">{t("deletion.deleting")}</p>}

      <Card
        title={t("deletion.apple_health")}
        info={t("deletion.apple_health_count", { raw: ah.raw, daily: ah.daily })
          + (ah.first_day ? " · " + t("deletion.apple_health_span", { first: ah.first_day, last: ah.last_day }) : "")}
        hint={t("deletion.apple_health_hint")}
        empty={ah.raw === 0 && ah.daily === 0}
        onDelete={() => setPending({ scope: "apple_health", range: rangeSet ? { from, to } : undefined })}
      >
        <div className="flex items-center gap-2 flex-wrap text-xs text-zinc-400">
          <span>{t("deletion.range_label")}</span>
          <label className="flex items-center gap-1">{t("deletion.range_from")}
            <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className={inputCls} />
          </label>
          <label className="flex items-center gap-1">{t("deletion.range_to")}
            <input type="date" value={to} onChange={(e) => setTo(e.target.value)} className={inputCls} />
          </label>
        </div>
      </Card>

      <Card title={t("deletion.fhir")} info={t("deletion.entries", { count: ov.fhir })}
        empty={ov.fhir === 0} onDelete={() => setPending({ scope: "fhir" })} />
      <Card title={t("deletion.ega")} info={t("deletion.entries", { count: ov.ega })}
        empty={ov.ega === 0} onDelete={() => setPending({ scope: "ega" })} />
      <Card title={t("deletion.all")} info={t("deletion.all_hint")}
        empty={!ov.akte && ah.raw === 0 && ah.daily === 0 && ov.fhir === 0 && ov.ega === 0}
        onDelete={() => setPending({ scope: "all" })} />

      {pending && <DeleteConfirmDialog busy={busy} onConfirm={run} onCancel={() => !busy && setPending(null)} />}
    </div>
  )
}
