import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { Trash2 } from "lucide-react"
import { mailApi, type ShareLevel, type SharesInfo } from "./api"

const FIELD = "min-w-0 flex-1 rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-2 py-1 text-sm text-[#e8eef8]"

/** Noch freigebbare Ziele: Buddy + Projekte des Nutzers, ohne die schon freigegebenen. */
export function shareOptions(info: SharesInfo, buddyLabel: string): { target: string; label: string }[] {
  const taken = new Set(info.shares.map((s) => s.target))
  return [{ target: "buddy", label: buddyLabel }, ...info.projects.map((p) => ({ target: `project:${p.id}`, label: p.name }))]
    .filter((o) => !taken.has(o.target))
}

/** Freigaben eines Kontos für Agenten (Spec §7, PLAN-M3a): Projekte oder der eigene Buddy, Stufe „lesen“. */
export function AccountShares({ accountId, initial = null }: { accountId: string; initial?: SharesInfo | null }) {
  const { t } = useTranslation("mailbox")
  const [info, setInfo] = useState<SharesInfo | null>(initial)
  const [pick, setPick] = useState("")
  const [level, setLevel] = useState<ShareLevel>("read")
  const [err, setErr] = useState(false)

  const load = useCallback(() => {
    mailApi.shares(accountId).then((i) => { setInfo(i); setErr(false) }).catch(() => setErr(true))
  }, [accountId])
  useEffect(() => { load() }, [load])

  async function run(fn: () => Promise<unknown>) {
    try { await fn(); setPick(""); load() } catch { setErr(true) }
  }

  if (!info) return err ? <p role="alert" className="text-xs text-rose-300">{t("shares.failed")}</p> : null
  const options = shareOptions(info, t("shares.buddy"))
  const label = (target: string, name: string) => (target === "buddy" ? t("shares.buddy") : name || t("shares.unknown"))

  return (
    <section className="space-y-2 border-t border-[#2a364b] pt-3" data-mbx-shares="1">
      <h3 className="text-xs font-bold text-[#e8eef8]">{t("shares.title")}</h3>
      <p className="text-[11px] text-[#718097]">{t("shares.hint")}</p>
      <p className="text-[11px] text-[#718097]">{t("shares.levelHint")}</p>
      {info.shares.length === 0 ? <p className="text-xs text-[#8d9ab0]">{t("shares.none")}</p> : (
        <ul className="space-y-1">
          {info.shares.map((s) => (
            <li key={s.target} className="flex items-center gap-2 text-sm text-[#c8d2df]" data-mbx-share={s.target}>
              <span className="min-w-0 flex-1 truncate">{label(s.target, s.name)}</span>
              <select value={s.level} aria-label={t("shares.level")} data-mbx-share-level={s.target}
                onChange={(e) => void run(() => mailApi.addShare(accountId, s.target, e.target.value as ShareLevel))}
                className="rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-1 py-0.5 text-[11px] text-[#c8d2df]">
                <option value="read">{t("shares.read")}</option><option value="draft">{t("shares.draft")}</option>
              </select>
              <button type="button" onClick={() => void run(() => mailApi.removeShare(accountId, s.target))}
                aria-label={t("shares.remove")} title={t("shares.remove")} className="rounded p-1 text-rose-300 hover:bg-rose-400/10">
                <Trash2 size={12} /></button>
            </li>))}
        </ul>)}
      {options.length > 0 && (
        <div className="flex gap-2">
          <select value={pick} onChange={(e) => setPick(e.target.value)} className={FIELD} aria-label={t("shares.pick")} data-mbx-share-pick="1">
            <option value="">{t("shares.pick")}</option>
            {options.map((o) => <option key={o.target} value={o.target}>{o.label}</option>)}
          </select>
          <select value={level} onChange={(e) => setLevel(e.target.value as ShareLevel)} aria-label={t("shares.level")}
            data-mbx-share-new-level="1" className="rounded-[4px] border border-[#2a364b] bg-[#0d131f] px-1 py-1 text-sm text-[#c8d2df]">
            <option value="read">{t("shares.read")}</option><option value="draft">{t("shares.draft")}</option>
          </select>
          <button type="button" disabled={!pick} onClick={() => void run(() => mailApi.addShare(accountId, pick, level))} data-mbx-share-add="1"
            className="rounded-[4px] border border-[#69d7ff]/50 bg-[#69d7ff]/15 px-3 py-1 text-sm text-[#69d7ff] disabled:opacity-40">
            {t("shares.add")}</button>
        </div>)}
      {err && <p role="alert" className="text-xs text-rose-300">{t("shares.failed")}</p>}
      {info.audit.length > 0 && (
        <details className="text-[11px] text-[#8d9ab0]">
          <summary className="cursor-pointer">{t("shares.audit", { n: info.audit.length })}</summary>
          <ul className="mt-1 space-y-0.5">
            {info.audit.map((a, i) => (
              <li key={i}>{a.at.slice(0, 16).replace("T", " ")} · {a.username} · {a.tool} · {a.result}</li>))}
          </ul>
        </details>)}
    </section>
  )
}
