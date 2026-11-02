// Artefakte: Upload, Samba-Eingang und Analyse starten.
import { useRef, useState } from "react"
import { useTranslation } from "react-i18next"
import {
  getIntake,
  scanIntake,
  startAnalysis,
  uploadArtifacts,
  type AnalysisType,
  type Artifact,
  type CaseFile,
  type IntakeInfo,
} from "./api"
import { MUTED, TEXT, analysisGroupsFor, artifactLabel, button, panel } from "./ui"

interface Props {
  caseFile: CaseFile
  onChanged: () => void
}

export function ArtifactPanel({ caseFile, onChanged }: Props) {
  const { t } = useTranslation("zerlegewerkstatt")
  const inputRef = useRef<HTMLInputElement>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [intake, setIntake] = useState<IntakeInfo | null>(null)

  const upload = (files: FileList | null) => {
    if (!files || files.length === 0) return
    setBusy(true)
    setError(null)
    setNotice(null)
    uploadArtifacts(caseFile.id, Array.from(files))
      .then((result) => {
        const failed = result.files.filter((file) => !file.ok)
        if (failed.length > 0) {
          setError(failed.map((file) => t(`error.${file.error}`)).join(", "))
        } else {
          setNotice(t("uploadDone", { count: result.files.length }))
        }
        onChanged()
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setBusy(false))
  }

  const checkIntake = () => {
    setBusy(true)
    setError(null)
    getIntake(caseFile.id)
      .then(setIntake)
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setBusy(false))
  }

  const runIntake = () => {
    setBusy(true)
    setError(null)
    setNotice(null)
    scanIntake(caseFile.id)
      .then((result) => {
        setNotice(t("intakeDone", { taken: result.taken, scanned: result.scanned }))
        onChanged()
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setBusy(false))
  }

  const analyze = (artifact: Artifact, analysisType: AnalysisType) => {
    setBusy(true)
    setError(null)
    setNotice(null)
    startAnalysis(caseFile.id, artifact.id, analysisType)
      .then(() => {
        setNotice(t("analysisStarted"))
        onChanged()
      })
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setBusy(false))
  }

  return (
    <div className={`${panel} space-y-3`}>
      <h2 className={`text-sm font-semibold ${TEXT}`}>{t("artifacts")}</h2>

      <div className="flex flex-wrap gap-2">
        <button className={button} disabled={busy} onClick={() => inputRef.current?.click()}>
          {t("upload")}
        </button>
        <input
          ref={inputRef}
          type="file"
          multiple
          className="hidden"
          onChange={(e) => upload(e.target.files)}
          accept=".exe,.dll,.apk,.bin,.pcap,.pcapng,.elf"
        />
        <button className={button} disabled={busy} onClick={checkIntake}>
          {t("intakeCheck")}
        </button>
        {intake && (
          <button className={button} disabled={busy} onClick={runIntake}>
            {t("intakeTake")}
          </button>
        )}
      </div>

      {intake && (
        <div className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] p-3 text-xs">
          <p className={TEXT}>{t("intakePath", { path: intake.path })}</p>
          <p className={`mt-1 ${MUTED}`}>
            {intake.files.length > 0 ? intake.files.join(", ") : t("intakeEmpty")}
          </p>
          <p className={`mt-2 ${MUTED}`}>{t("intakeSharedWarning")}</p>
        </div>
      )}

      {notice && <p className="text-sm text-[rgb(var(--hh-s-ok,120_190_140))]">{notice}</p>}
      {error && <p className="text-sm text-rose-400" role="alert">{error}</p>}

      {caseFile.artifacts.length === 0 ? (
        <p className={`text-sm ${MUTED}`}>{t("noArtifacts")}</p>
      ) : (
        <ul className="space-y-2">
          {caseFile.artifacts.map((artifact) => (
            <li
              key={artifact.id}
              className="rounded-lg border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-box,21_28_43)/0.6)] p-3"
            >
              <p className={`text-sm ${TEXT}`}>{artifactLabel(artifact)}</p>
              <p className={`mt-0.5 break-all text-xs ${MUTED}`}>{artifact.sha256}</p>
              <div className="mt-3 space-y-3">
                {analysisGroupsFor(artifact.kind).map(({ group, analyses }) => (
                  <div key={group}>
                    <p className={`mb-1 text-[11px] font-medium uppercase tracking-wide ${MUTED}`}>
                      {t(`analysisGroups.${group}`)}
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {analyses.map((analysisType) => (
                        <button
                          key={analysisType}
                          className={button}
                          disabled={busy}
                          onClick={() => analyze(artifact, analysisType)}
                        >
                          {t(`analysis.${analysisType}`)}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
