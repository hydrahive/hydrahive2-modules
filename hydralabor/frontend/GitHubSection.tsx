import { useCallback, useEffect, useState } from "react"
import { useTranslation } from "react-i18next"
import { useDialog } from "@/shared/dialog/useDialog"
import { ModalPortal } from "@/shared/ModalPortal"
import * as api from "./api"
import { GitHubBoxView } from "./GitHubBox"
import { submitResult, type DeviceCode, type GitHubState, type Submission, type Target } from "./githubLogic"
import { errorKey, type LabState } from "./logic"
import { ReportDialogView } from "./ReportDialog"
import { SubmissionList } from "./SubmissionList"
import { SubmitDialogView } from "./SubmitDialog"
import { BOX, BTN } from "./ui"

const POLL_MS = 3000

/** L2 auf der Seite: GitHub-Verbindung, „Änderung einreichen“ / „Fehler melden“ (nur im fertigen Labor), Einreichungen.
 * `s` = Zustand des Labors (Einreichen läuft als Auftrag), `onJobStarted` lädt ihn neu. */
export function GitHubSection({ s, onJobStarted }: { s: LabState; onJobStarted: () => void }) {
  const { t } = useTranslation("hydralabor")
  const [gh, setGh] = useState<GitHubState | null>(null)
  const [code, setCode] = useState<DeviceCode | null>(null)
  const [subs, setSubs] = useState<Submission[]>([])
  const [busy, setBusy] = useState(false)
  const [msg, setMsg] = useState("")
  const [open, setOpen] = useState<"" | "submit" | "report">("")
  const loadGh = useCallback(() => api.getGitHub().then(setGh).catch(() => {}), [])
  const loadSubs = useCallback(() => api.getSubmissions().then((r) => setSubs(r.items)).catch(() => {}), [])
  useEffect(() => { loadGh(); loadSubs() }, [loadGh, loadSubs])
  // Nur während des Wartens auf die Freigabe bei GitHub nachsehen.
  useEffect(() => {
    if (!gh?.pending) return
    const id = setTimeout(loadGh, POLL_MS)
    return () => clearTimeout(id)
  }, [gh, loadGh])
  const wasSubmitting = s.running === "submit"
  useEffect(() => { if (!wasSubmitting) loadSubs() }, [wasSubmitting, loadSubs])

  const act = async (fn: () => Promise<unknown>) => {
    setBusy(true); setMsg("")
    try { await fn() } catch (e) { setMsg(errorKey(e)) } finally { setBusy(false) }
  }
  if (!gh) return null
  const ready = s.step === "ready"
  return (
    <>
      <GitHubBoxView gh={gh} code={gh.connected ? null : code} busy={busy}
        onConnect={() => act(async () => { setCode(await api.connectGitHub()); await loadGh() })}
        onDisconnect={() => act(async () => setGh(await api.disconnectGitHub()))} />
      {msg && <p role="alert" className="text-sm text-red-300">{t(msg)}</p>}
      {ready && gh.connected && (
        <section className={`${BOX} flex flex-wrap gap-2`}>
          <button type="button" className={BTN} disabled={!!s.running} onClick={() => setOpen("submit")}>{t("submit.open")}</button>
          <button type="button" className={BTN} onClick={() => setOpen("report")}>{t("report.open")}</button>
        </section>
      )}
      {ready && gh.connected && <SubmissionList items={subs} busy={busy} onRefresh={() => act(async () => setSubs((await api.refreshSubmissions()).items))} />}
      {open === "submit" && <SubmitDialog s={s} onClose={() => { setOpen(""); loadSubs() }} onStarted={onJobStarted} />}
      {open === "report" && <ReportDialog onClose={() => { setOpen(""); loadSubs() }} />}
    </>
  )
}

function SubmitDialog({ s, onClose, onStarted }: { s: LabState; onClose: () => void; onStarted: () => void }) {
  const dlg = useDialog({ onEscape: s.running === "submit" ? undefined : onClose })
  const [target, setTarget] = useState<Target>("core")
  const [title, setTitle] = useState("")
  const [body, setBody] = useState("")
  const [sent, setSent] = useState(false)
  const [err, setErr] = useState("")
  useEffect(() => { api.suggestTarget().then((r) => { if (r.target) setTarget(r.target) }).catch(() => {}) }, [])
  const running = s.running === "submit"
  const finished = sent && !running
  const send = async () => {
    setErr("")
    try { await api.startSubmit(target, title, body); setSent(true); onStarted() } catch (e) { setErr(errorKey(e).slice(4)) }
  }
  return (
    <ModalPortal>
      <SubmitDialogView titleId={dlg.titelId} dialogRef={dlg.ref} target={target} title={title} body={body}
        running={running} progress={s.progress} error={finished ? s.error_code : err}
        detail={finished ? s.submit_out?.detail ?? null : null} result={finished ? submitResult(s.submit_out ?? {}) : null}
        onTarget={setTarget} onTitle={setTitle} onBody={setBody} onSubmit={send} onClose={onClose} />
    </ModalPortal>
  )
}

function ReportDialog({ onClose }: { onClose: () => void }) {
  const dlg = useDialog({ onEscape: onClose })
  const [v, setV] = useState({ target: "core" as Target, title: "", what: "", expected: "", steps: "" })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState("")
  const [result, setResult] = useState<{ number: number; url: string } | null>(null)
  const send = async () => {
    setBusy(true); setErr("")
    try { setResult(await api.reportBug(v)) } catch (e) { setErr(errorKey(e).slice(4)) } finally { setBusy(false) }
  }
  return (
    <ModalPortal>
      <ReportDialogView titleId={dlg.titelId} dialogRef={dlg.ref} {...v} busy={busy} error={err} result={result}
        onChange={(k, val) => setV((o) => ({ ...o, [k]: val }))} onSubmit={send} onClose={onClose} />
    </ModalPortal>
  )
}
