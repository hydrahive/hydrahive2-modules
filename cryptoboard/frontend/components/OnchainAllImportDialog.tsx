import { Info } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import {
  applyChoice, bookingSummary, buildAllPayload, chosenEntries, defaultSelectionAll, emptySummary, hashLabel, isEmptyResult,
  markBookedAll, selectableHashes,
  type Choice,
} from "../onchainAll"
import { errorKey, isBookable, SKIP_REASONS, type Edits, type EntryEdit } from "../onchainImport"
import type { OnchainCommitResult, OnchainMehrdeutig, OnchainPreviewAll } from "../types"
import { AddressStatusList, MehrdeutigList, PairHeader, SpamList } from "./OnchainAllSections"
import { OnchainPreviewTable } from "./OnchainPreviewTable"
import { OnchainSideLists } from "./OnchainSideLists"

interface Props {
  onDone: (imported: number) => void
  onCancel: () => void
}

const box = "rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-2.5 space-y-1.5"

// Trades aller Adressen: Preview_all → Paare, Swaps, Mehrdeutiges (Auswahl), Ausgaben (Standard aus) → EIN Commit.
export function OnchainAllImportDialog({ onDone, onCancel }: Props) {
  const { t } = useTranslation("cryptoboard")
  const [preview, setPreview] = useState<OnchainPreviewAll | null>(null)
  const [edits, setEdits] = useState<Edits>({})
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [choice, setChoice] = useState<Choice>({})
  const [busy, setBusy] = useState<"" | "preview" | "commit">("")
  const [err, setErr] = useState<{ text: string; keyMissing: boolean } | null>(null)
  const [result, setResult] = useState<OnchainCommitResult | null>(null)

  const load = useCallback(async () => {
    setErr(null)
    setBusy("preview")
    try {
      const p = await cryptoApi.onchainPreviewAll()
      setSelected(defaultSelectionAll(p))
      setChoice({})
      setPreview(p)
    } catch (e) {
      const key = errorKey(e)
      setErr({ text: key ? t(key) : t("oc_err_generic"), keyMissing: key === "oc_err_alchemy_key_missing" })
    } finally {
      setBusy("")
    }
  }, [t])

  useEffect(() => { void load() }, [load])

  const toggle = (hash: string, on: boolean) =>
    setSelected((s) => { const n = new Set(s); if (on) n.add(hash); else n.delete(hash); return n })
  const toggleMany = (hashes: string[], on: boolean) =>
    setSelected((s) => { const n = new Set(s); for (const h of hashes) { if (on) n.add(h); else n.delete(h) } return n })

  const allEntries = preview ? [...preview.transactions, ...preview.pairs.flatMap((x) => x.entries),
    ...preview.mehrdeutig.flatMap((m) => m.candidates.flatMap((c) => c.entries)), ...preview.ausgaben] : []

  function edit(hash: string, e: EntryEdit) {
    setEdits((all) => ({ ...all, [hash]: e }))
    const entry = allEntries.find((x) => x.hash === hash)
    if (entry && entry.kind !== "transfer_out" && isBookable(entry, e) && !isBookable(entry, edits[hash])) toggle(hash, true)
  }

  function choose(m: OnchainMehrdeutig, key: string) {
    setChoice((c) => ({ ...c, [m.tron_tx]: key || undefined }))
    setSelected((s) => applyChoice(s, m, key, edits))
  }

  const chosen = preview ? chosenEntries(preview, choice) : []
  const payload = preview ? buildAllPayload(preview, selected, edits, choice) : []

  async function commit() {
    if (!preview) return
    if (payload.length === 0) { setErr({ text: t("imp_nothing"), keyMissing: false }); return }
    setErr(null)
    setBusy("commit")
    try {
      const res = await cryptoApi.onchainCommit(payload)
      setResult(res)
      const done = markBookedAll(preview, payload, res)
      setPreview(done.preview)
      setSelected((sel) => new Set([...sel].filter((h) => !done.booked.has(h))))
      if (res.imported > 0) onDone(res.imported)
    } catch (e) {
      const key = errorKey(e)
      setErr({ text: key ? t(key) : t("oc_err_generic"), keyMissing: false })
    } finally {
      setBusy("")
    }
  }

  const c = preview?.counts
  const btn = "px-4 py-2 rounded-lg text-sm disabled:opacity-50"
  const empty = c ? isEmptyResult(c) : false
  const sum = c ? emptySummary(c) : null

  return (
    <div className="space-y-3">
      <p className="flex items-start gap-1.5 text-[11px] text-[#9aa7bc]">
        <Info size={12} className="mt-0.5 shrink-0" /> {t("oc_hint")}
      </p>
      {busy === "preview" && <p className="text-xs text-[#9aa7bc] text-center py-3">{t("oc_loading")}</p>}
      {preview && preview.addresses.length > 0 && <AddressStatusList addresses={preview.addresses} />}
      {preview?.kurs_abruf_fehlgeschlagen && <p className="text-[11px] text-amber-400">{t("oc_price_fetch_failed")}</p>}
      {preview && !result && (
        <div className="sticky top-0 z-10 flex flex-wrap items-center gap-2 rounded-lg border border-emerald-500/30 bg-[rgb(var(--hh-s-innen,17_24_39))] p-2.5">
          <span className="text-xs text-[#c8d2df]">{t("oc_summary", bookingSummary(preview))}</span>
          <button disabled={busy !== "" || payload.length === 0} onClick={commit}
            className={`${btn} ml-auto bg-emerald-500/20 text-emerald-300 font-medium hover:bg-emerald-500/30`}>
            {busy === "commit" ? t("oc_booking") : `${t("oc_commit")} (${payload.length})`}
          </button>
        </div>
      )}

      {preview && empty && sum && (
        <div className={box}>
          <p className="text-sm font-medium text-[#e8eef8]">{t("oc_all_empty")}</p>
          <p className="text-[11px] text-[#9aa7bc]">{t("oc_all_empty_sum", sum)}</p>
        </div>
      )}

      {preview && preview.pairs.length > 0 && (
        <section className="space-y-1.5">
          <h4 className="text-xs font-medium text-[#c8d2df]">{t("oc_pairs_title")} ({preview.pairs.length})</h4>
          <p className="text-[11px] text-[#9aa7bc]">{t("oc_pairs_hint", { min: preview.window_minutes })}</p>
          <OnchainPreviewTable entries={preview.pairs.flatMap((p) => p.entries)} edits={edits} selected={selected}
            onToggle={toggle} onEdit={edit}
            headerExtra={(id) => {
              const p = preview.pairs.find((x) => x.id === id)
              return p ? <PairHeader pair={p} /> : null
            }} />
        </section>
      )}

      {preview && preview.transactions.length > 0 && (
        <section className="space-y-1.5">
          <h4 className="text-xs font-medium text-[#c8d2df]">{t("oc_all_swaps_title")}</h4>
          <OnchainPreviewTable entries={preview.transactions} edits={edits} selected={selected}
            onToggle={toggle} onEdit={edit} />
        </section>
      )}

      {preview && <MehrdeutigList items={preview.mehrdeutig} choice={choice} onChoose={choose} />}
      {preview && chosen.length > 0 && (
        <OnchainPreviewTable entries={chosen} edits={edits} selected={selected} onToggle={toggle} onEdit={edit} />
      )}

      {preview && (["kartenzahlung", "abgang"] as const).map((art) => {
        const list = preview.ausgaben.filter((e) => (e.art === "kartenzahlung" ? "kartenzahlung" : "abgang") === art)
        if (list.length === 0) return null
        const hashes = selectableHashes(list, edits)
        const allOn = hashes.length > 0 && hashes.every((h) => selected.has(h))
        return (
          <section key={art} className="space-y-1.5">
            <div className="flex items-center gap-2">
              <h4 className="text-xs font-medium text-amber-300">{t(`oc_ausgaben_${art}`)} ({list.length})</h4>
              {hashes.length > 0 && (
                <button onClick={() => toggleMany(hashes, !allOn)}
                  className="ml-auto rounded-full border border-amber-400/30 px-2 py-0.5 text-[11px] text-amber-200 hover:bg-amber-400/10">
                  {allOn ? t("oc_select_none") : t("oc_select_all", { n: hashes.length })}
                </button>
              )}
            </div>
            <p className="text-[11px] text-[#9aa7bc]">{t(`oc_ausgaben_${art}_hint`)}</p>
            <OnchainPreviewTable entries={list} edits={edits} selected={selected} onToggle={toggle} onEdit={edit} />
          </section>
        )
      })}

      {preview && <SpamList items={preview.spam} />}
      {preview && <OnchainSideLists wraps={preview.wraps} unklar={preview.unklar} />}

      {err && (
        <p className="text-xs text-rose-400">
          {err.text}{" "}
          {err.keyMissing && (
            <a href="#cryptoboard-alchemy-key" className="text-sky-300 hover:underline">{t("oc_goto_key")}</a>
          )}
        </p>
      )}

      {result && (
        <div className="text-xs space-y-0.5">
          <p className="text-emerald-400">{t("oc_result", { imported: result.imported, skipped: result.skipped })}</p>
          {result.skipped_details.map((d) => {
            const h = hashLabel(d.hash)
            return (
              <p key={d.hash} className="text-[11px] text-[#9aa7bc]">
                <span className="font-mono">{h.tx} {h.kind}</span>{" — "}
                {SKIP_REASONS.includes(d.reason) ? t(`oc_skip_${d.reason}`) : d.reason}
              </p>
            )
          })}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        {preview && (
          <button disabled={busy !== "" || payload.length === 0} onClick={commit}
            className={`${btn} bg-emerald-500/20 text-emerald-300 font-medium hover:bg-emerald-500/30`}>
            {busy === "commit" ? t("oc_booking") : `${t("oc_commit")} (${payload.length})`}
          </button>
        )}
        <button onClick={onCancel}
          className={`${btn} bg-[rgb(var(--hh-s-innen,17_24_39))] text-[#c8d2df] hover:text-[#e8eef8]`}>
          {result ? t("oc_close") : t("tx_cancel")}
        </button>
      </div>
    </div>
  )
}
