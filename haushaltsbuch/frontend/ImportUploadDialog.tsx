import { useEffect, useState, type FormEvent } from "react"
import { FileUp } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage, haushaltsbuchApi } from "./api"
import { CsvMappingSection } from "./CsvMappingSection"
import { decodePreview, firstCsvRow } from "./csvHeader"
import { EMPTY_MAPPING, profileBody, profileMapping, validateMapping } from "./csvMapping"
import type { Account, CsvImportMapping, CsvPreview, ImportBatch, ImportFormat, ImportProfile } from "./types"
import { FORMAT_HINTS, FORMAT_OPTIONS, UPLOAD_ACCEPT, importErrorText, needsCsvMapping, shouldOpenMapping } from "./importFormats"
import { Button, ErrorState, Field, Input, Select } from "./ui"

const MAX_FILE_SIZE = 10 * 1024 * 1024
const HEAD_BYTES = 64 * 1024
export const UNKNOWN_BANK_NOTICE = "Diese Bank wird noch nicht automatisch erkannt. Ordne die Spalten einmal zu – die Kopfzeile und Beispielzeilen aus deiner Datei sind schon eingetragen. Als Profil gespeichert klappt der nächste Import ohne Zuordnung."

export function ImportUploadDialog({ accounts, baseCurrency, profiles, onProfilesChanged, onClose, onCreated, initialFormat = "auto" }: {
  accounts: Account[]
  baseCurrency: string
  profiles: ImportProfile[]
  onProfilesChanged: () => Promise<void>
  onClose: () => void
  onCreated: (batch: ImportBatch) => void
  initialFormat?: ImportFormat
}) {
  const activeAccounts = accounts.filter((account) => !account.archived && account.currency === baseCurrency)
  const [accountId, setAccountId] = useState(String(activeAccounts[0]?.id ?? ""))
  const [file, setFile] = useState<File>()
  const [format, setFormat] = useState<ImportFormat>(initialFormat)
  const [mapping, setMapping] = useState<CsvImportMapping>(EMPTY_MAPPING)
  const [headers, setHeaders] = useState<string[]>([])
  const [previewError, setPreviewError] = useState<string>()
  const [profileId, setProfileId] = useState("")
  const [profileName, setProfileName] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const [mappingRequested, setMappingRequested] = useState(false)
  const [preview, setPreview] = useState<CsvPreview>()
  const csvSelected = needsCsvMapping(format, file?.name) || mappingRequested
  const csvPreviewKey = `${file?.name ?? ""}:${file?.size ?? 0}:${file?.lastModified ?? 0}`

  function chooseFile(next: File | undefined) { setFile(next); setMappingRequested(false); setPreview(undefined); setError(undefined) }
  function chooseFormat(next: ImportFormat) { setFormat(next); setMappingRequested(false); setPreview(undefined); setError(undefined) }

  // Kopfzeile lokal lesen (Format „CSV“; bei „Automatisch“ erst/auch nach csv_mapping_required als Rückfall).
  useEffect(() => {
    if (!file || !csvSelected) { setHeaders([]); setPreviewError(undefined); return }
    let cancelled = false
    const head = file.slice(0, HEAD_BYTES)
    head.arrayBuffer().then((buffer) => {
      const text = decodePreview(buffer, mapping.encoding, file.size > HEAD_BYTES)
      const parsed = firstCsvRow(text.replace(/^\uFEFF/, ""), mapping.delimiter)
      if (!parsed.length) throw new Error("Keine CSV-Kopfzeile gefunden.")
      if (!cancelled) { setHeaders(parsed); setPreviewError(undefined) }
    }).catch((cause: unknown) => { if (!cancelled) setPreviewError(errorMessage(cause)) })
    return () => { cancelled = true }
  }, [csvPreviewKey, csvSelected, mapping.delimiter, mapping.encoding])

  // Unbekannte Bank: Kopfzeile + Beispielzeilen vom Server (POST /imports/csv-preview) vorbelegen.
  useEffect(() => {
    if (!file || !mappingRequested || !accountId) return
    let cancelled = false
    haushaltsbuchApi.csvPreview(file, Number(accountId)).then((data) => {
      if (cancelled) return
      setPreview(data); setHeaders(data.header.filter((name) => name.length > 0)); setPreviewError(undefined)
      setMapping((current) => ({ ...current, delimiter: data.delimiter }))
    }).catch(() => { /* Rückfall: lokale Kopfzeilen-Vorschau (Effekt oben) */ })
    return () => { cancelled = true }
  }, [csvPreviewKey, mappingRequested, accountId])

  function chooseProfile(id: string) {
    setProfileId(id)
    const profile = profiles.find((item) => item.id === Number(id))
    if (profile) { setProfileName(profile.name); setMapping(profileMapping(profile)) }
  }
  async function saveProfile() {
    setError(undefined)
    try {
      validateMapping(mapping)
      if (!profileName.trim()) throw new Error("Gib einen Profilnamen ein.")
      setBusy(true)
      const selected = profiles.find((item) => item.id === Number(profileId))
      const saved = selected
        ? await haushaltsbuchApi.updateImportProfile(selected.id, { ...profileBody(profileName, mapping, preview?.encoding), revision: selected.revision })
        : await haushaltsbuchApi.createImportProfile(profileBody(profileName, mapping, preview?.encoding))
      await onProfilesChanged(); setProfileId(String(saved.id)); setProfileName(saved.name)
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  async function deleteProfile() {
    const selected = profiles.find((item) => item.id === Number(profileId))
    if (!selected || !window.confirm(`CSV-Profil „${selected.name}“ löschen?`)) return
    setError(undefined); setBusy(true)
    try { await haushaltsbuchApi.deleteImportProfile(selected.id, selected.revision); setProfileId(""); setProfileName(""); setMapping(EMPTY_MAPPING); await onProfilesChanged() }
    catch (cause) { setError(cause) } finally { setBusy(false) }
  }
  async function submit(event: FormEvent) {
    event.preventDefault(); setError(undefined)
    try {
      if (!file) throw new Error("Wähle eine Bankexport-Datei aus.")
      if (file.size > MAX_FILE_SIZE) throw new Error("Die Datei ist größer als 10 MiB.")
      if (!accountId) throw new Error("Wähle ein Zielkonto aus.")
      if (csvSelected) validateMapping(mapping)
      setBusy(true)
      const batch = await haushaltsbuchApi.createImport({
        file,
        account_id: Number(accountId),
        format,
        csv_mapping: csvSelected ? mapping : undefined,
        profile_id: csvSelected && profileId ? Number(profileId) : undefined,
      })
      onCreated(batch)
    } catch (cause) {
      // „Automatisch“ ohne Zuordnung: unbekannte Bank → jetzt (und nur jetzt) die Zuordnung öffnen.
      if (shouldOpenMapping(format, csvSelected, cause)) setMappingRequested(true)
      else setError(cause)
    } finally { setBusy(false) }
  }

  return <AdminDialog title="Bankexport importieren" eyebrow="Haushaltsbuch · Importe" icon={<FileUp size={16} />} maxWidthClass="max-w-4xl" onClose={busy ? undefined : onClose} footer={<><Button onClick={onClose} disabled={busy}>Abbrechen</Button><Button tone="primary" type="submit" form="import-upload-form" disabled={busy}>{busy ? "Wird geprüft …" : "Als Entwurf hochladen"}</Button></>}>
    <form id="import-upload-form" onSubmit={submit} className="grid gap-5">
      {error !== undefined && <ErrorState error={importErrorText(error, errorMessage, format)} />}
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Zielkonto" hint={`Etappe 2 unterstützt Konten in der Haushaltsbasiswährung ${baseCurrency}.`}><Select required value={accountId} onChange={(event) => setAccountId(event.target.value)}><option value="">Auswählen …</option>{activeAccounts.map((account) => <option key={account.id} value={account.id}>{account.name} ({account.currency})</option>)}</Select></Field>
        <Field label="Datei" hint="CAMT XML, MT940, CSV, PDF-Kontoauszug oder PayPal-Export; maximal 10 MiB"><Input required type="file" accept={UPLOAD_ACCEPT} onChange={(event) => chooseFile(event.target.files?.[0])} /></Field>
        <Field label="Format" hint={FORMAT_HINTS[format]}><Select value={format} onChange={(event) => chooseFormat(event.target.value as ImportFormat)}>{FORMAT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</Select></Field>
      </div>
      {file && <p className={`text-xs ${file.size > MAX_FILE_SIZE ? "text-rose-200" : "text-[#9aa7bc]"}`}>{file.name} · {(file.size / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} KiB</p>}
      {csvSelected && <CsvMappingSection mapping={mapping} onMapping={setMapping} headers={headers} previewError={previewError} preview={preview} notice={mappingRequested ? UNKNOWN_BANK_NOTICE : undefined} profiles={profiles} profileId={profileId} profileName={profileName} onProfileId={chooseProfile} onProfileName={setProfileName} onSave={saveProfile} onDelete={deleteProfile} busy={busy} />}
    </form>
  </AdminDialog>
}
