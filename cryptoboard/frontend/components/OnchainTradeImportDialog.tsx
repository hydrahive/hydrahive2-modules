import { History, Info } from "lucide-react"
import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { cryptoApi } from "../api"
import {
  buildCommitPayload, defaultSelection, errorKey, isBookable, mergePreview, SKIP_REASONS,
  type Edits, type EntryEdit,
} from "../onchainImport"
import type { OnchainCommitResult, OnchainPreview, WalletAddress } from "../types"
import { OnchainPreviewTable } from "./OnchainPreviewTable"
import { OnchainSideLists } from "./OnchainSideLists"

interface Props {
  address: Pick<WalletAddress, "id" | "chain" | "address" | "label">
  onDone: (imported: number) => void
  onCancel: () => void
}

// On-Chain-Trade-Import für eine verknüpfte Base/Ethereum-Adresse:
// Preview (kann dauern) → Pflichtfelder ergänzen → gewählte Einträge buchen.
export function OnchainTradeImportDialog({ address, onDone, onCancel }: Props) {
  const { t } = useTranslation("cryptoboard")
  const [preview, setPreview] = useState<OnchainPreview | null>(null)
  const [edits, setEdits] = useState<Edits>({})
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [busy, setBusy] = useState<"" | "preview" | "more" | "commit">("")
  const [err, setErr] = useState<{ text: string; keyMissing: boolean } | null>(null)
  const [result, setResult] = useState<OnchainCommitResult | null>(null)

  const fail = useCallback((e: unknown) => {
    const key = errorKey(e)
    setErr({ text: key ? t(key) : t("oc_err_generic"), keyMissing: key === "oc_err_alchemy_key_missing" })
  }, [t])

  const load = useCallback(async (toBlock?: string | null) => {
    setErr(null)
    setBusy(toBlock ? "more" : "preview")
    try {
      const next = await cryptoApi.onchainPreview(address.id, toBlock)
      setPreview((prev) => {
        const merged = prev && toBlock ? mergePreview(prev, next) : next
        // Neu hinzugekommene buchbare Einträge vorwählen, bestehende Auswahl behalten.
        setSelected((sel) => {
          const out = new Set(sel)
          const known = new Set(prev && toBlock ? prev.transactions.map((e) => e.hash) : [])
          for (const h of defaultSelection(merged.transactions.filter((e) => !known.has(e.hash)))) out.add(h)
          return out
        })
        return merged
      })
    } catch (e) {
      fail(e)
    } finally {
      setBusy("")
    }
  }, [address.id, fail])

  useEffect(() => { void load() }, [load])

  function toggle(hash: string, on: boolean) {
    setSelected((s) => { const n = new Set(s); if (on) n.add(hash); else n.delete(hash); return n })
  }

  function edit(hash: string, e: EntryEdit) {
    setEdits((all) => ({ ...all, [hash]: e }))
    // Wird ein Eintrag durch die Ergänzung buchbar, gleich mit auswählen.
    const entry = preview?.transactions.find((x) => x.hash === hash)
    if (entry && isBookable(entry, e) && !isBookable(entry, edits[hash])) toggle(hash, true)
  }

  async function commit() {
    if (!preview) return
    const payload = buildCommitPayload(preview.transactions, selected, edits)
    if (payload.length === 0) { setErr({ text: t("imp_nothing"), keyMissing: false }); return }
    setErr(null)
    setBusy("commit")
    try {
      const res = await cryptoApi.onchainCommit(payload)
      setResult(res)
      if (res.imported > 0) onDone(res.imported)
    } catch (e) {
      fail(e)
    } finally {
      setBusy("")
    }
  }

  const count = preview ? buildCommitPayload(preview.transactions, selected, edits).length : 0
  const c = preview?.counts
  const btn = "px-4 py-2 rounded-lg text-sm disabled:opacity-50"

  return (
    <div className="space-y-3">
      <p className="flex items-start gap-1.5 text-[11px] text-[#9aa7bc]">
        <Info size={12} className="mt-0.5 shrink-0" /> {t("oc_hint")}
      </p>

      {busy === "preview" && <p className="text-xs text-[#9aa7bc] text-center py-3">{t("oc_loading")}</p>}

      {c && (
        <div className="flex flex-wrap gap-3 text-[11px]">
          <span className="text-[#c8d2df]">{t("oc_count_swaps", { count: c.swaps })}</span>
          {c.duplicates > 0 && <span className="text-[#9aa7bc]">{c.duplicates} {t("imp_duplicate")}</span>}
          {c.preis_fehlt > 0 && <span className="text-amber-400">{c.preis_fehlt} {t("oc_count_price_missing")}</span>}
          {c.unresolved > 0 && <span className="text-amber-400">{c.unresolved} {t("imp_unresolved")}</span>}
          {c.gebuehr_fehlt > 0 && <span className="text-[#9aa7bc]">{c.gebuehr_fehlt} {t("oc_count_fee_missing")}</span>}
          {c.wraps > 0 && <span className="text-[#9aa7bc]">{c.wraps} {t("oc_wraps")}</span>}
          {c.unklar > 0 && <span className="text-amber-300">{c.unklar} {t("oc_unklar")}</span>}
        </div>
      )}
      {preview?.kurs_abruf_fehlgeschlagen && <p className="text-[11px] text-amber-400">{t("oc_price_fetch_failed")}</p>}

      {preview && preview.transactions.length === 0 && <p className="text-xs text-[#9aa7bc]">{t("oc_no_swaps")}</p>}
      {preview && preview.transactions.length > 0 && (
        <OnchainPreviewTable entries={preview.transactions} edits={edits} selected={selected} onToggle={toggle} onEdit={edit} />
      )}
      {preview && <OnchainSideLists wraps={preview.wraps} unklar={preview.unklar} />}

      {preview?.truncated && preview.before_block && (
        <button onClick={() => void load(preview.before_block)} disabled={busy !== ""}
          className="flex items-center gap-1.5 text-xs text-sky-300 hover:underline disabled:opacity-50">
          <History size={13} /> {busy === "more" ? t("oc_loading") : t("oc_load_older")}
        </button>
      )}

      {err && (
        <p className="text-xs text-rose-400">
          {err.text}{" "}
          {err.keyMissing && <a href="#cryptoboard-alchemy-key" className="text-sky-300 hover:underline">{t("oc_goto_key")}</a>}
        </p>
      )}

      {result && (
        <div className="text-xs space-y-0.5">
          <p className="text-emerald-400">{t("oc_result", { imported: result.imported, skipped: result.skipped })}</p>
          {result.skipped_details.map((d) => (
            <p key={d.hash} className="text-[11px] text-[#9aa7bc]">
              <span className="font-mono">{d.hash.split(":")[1]?.slice(0, 10)}… {d.hash.split(":")[2]}</span>{" — "}
              {SKIP_REASONS.includes(d.reason) ? t(`oc_skip_${d.reason}`) : d.reason}
            </p>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2 pt-1">
        {preview && (
          <button disabled={busy !== "" || count === 0} onClick={commit}
            className={`${btn} bg-emerald-500/20 text-emerald-300 font-medium hover:bg-emerald-500/30`}>
            {busy === "commit" ? t("oc_booking") : `${t("oc_commit")} (${count})`}
          </button>
        )}
        <button onClick={onCancel} className={`${btn} bg-[rgb(var(--hh-s-innen,17_24_39))] text-[#c8d2df] hover:text-[#e8eef8]`}>
          {result ? t("oc_close") : t("tx_cancel")}
        </button>
      </div>
    </div>
  )
}
