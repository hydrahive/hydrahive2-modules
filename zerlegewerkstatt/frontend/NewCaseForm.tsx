// Fallanlage: Pflichtangaben inklusive Zweck und Berechtigungsbestaetigung.
import { useState } from "react"
import { useTranslation } from "react-i18next"
import { createCase, type CaseInput, type Purpose } from "./api"
import { MUTED, PURPOSES, TEXT, button, input, label, panel } from "./ui"
interface Props {
  projectId: string
  onCreated: (caseId: string) => void
}

export function NewCaseForm({ projectId, onCreated }: Props) {
  const { t } = useTranslation("zerlegewerkstatt")
  const [title, setTitle] = useState("")
  const [target, setTarget] = useState("")
  const [question, setQuestion] = useState("")
  const [purpose, setPurpose] = useState<Purpose>("interoperability")
  const [authorized, setAuthorized] = useState(false)
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const ready = title.trim().length >= 3 && question.trim().length >= 10 && authorized

  const submit = () => {
    if (!ready || busy) return
    setBusy(true)
    setError(null)
    const body: CaseInput = {
      project_id: projectId,
      title: title.trim(),
      target: target.trim(),
      question: question.trim(),
      purpose,
      authorized,
      authorization_note: note.trim(),
    }
    createCase(body)
      .then((created) => onCreated(created.id))
      .catch((e) => setError(String(e.message ?? e)))
      .finally(() => setBusy(false))
  }

  return (
    <div className={`${panel} space-y-3`}>
      <h2 className={`text-sm font-semibold ${TEXT}`}>{t("newCase")}</h2>

      <div>
        <label className={label} htmlFor="zw-title">{t("caseTitle")}</label>
        <input
          id="zw-title"
          className={`${input} w-full`}
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={t("caseTitlePlaceholder")}
        />
      </div>

      <div>
        <label className={label} htmlFor="zw-target">{t("caseTarget")}</label>
        <input
          id="zw-target"
          className={`${input} w-full`}
          value={target}
          onChange={(e) => setTarget(e.target.value)}
          placeholder={t("caseTargetPlaceholder")}
        />
      </div>

      <div>
        <label className={label} htmlFor="zw-question">{t("caseQuestion")}</label>
        <textarea
          id="zw-question"
          className={`${input} w-full min-h-20`}
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder={t("caseQuestionPlaceholder")}
        />
      </div>

      <div>
        <label className={label} htmlFor="zw-purpose">{t("casePurpose")}</label>
        <select
          id="zw-purpose"
          className={`${input} w-full`}
          value={purpose}
          onChange={(e) => setPurpose(e.target.value as Purpose)}
        >
          {PURPOSES.map((entry) => (
            <option key={entry.id} value={entry.id}>{entry.label}</option>
          ))}
        </select>
      </div>

      <label className={`flex items-start gap-2 text-sm ${TEXT}`}>
        <input
          type="checkbox"
          className="mt-1"
          checked={authorized}
          onChange={(e) => setAuthorized(e.target.checked)}
        />
        <span>{t("authorizationConfirm")}</span>
      </label>

      <div>
        <label className={label} htmlFor="zw-note">{t("authorizationNote")}</label>
        <input
          id="zw-note"
          className={`${input} w-full`}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder={t("authorizationNotePlaceholder")}
        />
      </div>

      {error && (
        <p className="text-sm text-rose-400" role="alert">{error}</p>
      )}

      <button className={button} onClick={submit} disabled={!ready || busy}>
        {busy ? t("creating") : t("createCase")}
      </button>
      {!authorized && (
        <p className={`text-xs ${MUTED}`}>{t("authorizationNeeded")}</p>
      )}
    </div>
  )
}
