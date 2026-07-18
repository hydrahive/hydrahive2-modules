import { useEffect, useState, type FormEvent } from "react"
import { FileUp, Save, Trash2 } from "lucide-react"
import { AdminDialog } from "@/features/cockpit/admin/ui/AdminDialog"
import { errorMessage, haushaltsbuchApi } from "./api"
import type {
  Account, CsvColumnMapping, CsvDelimiter, CsvEncoding, CsvImportMapping, ImportBatch,
  ImportFormat, ImportProfile, ImportProfileCreate,
} from "./types"
import { Button, ErrorState, Field, Input, Select } from "./ui"

const MAX_FILE_SIZE = 10 * 1024 * 1024
const EMPTY_MAPPING: CsvImportMapping = {
  booking_date: "", amount: "", debit_amount: "", credit_amount: "", value_date: "",
  currency: "", counterparty: "", purpose: "", bank_reference: "",
  counterparty_identifier: "", category_hint: "", delimiter: ";", encoding: "utf-8",
  decimal_separator: ",", date_format: "%d.%m.%Y",
}
const COLUMN_LABELS: { key: keyof CsvColumnMapping; label: string }[] = [
  { key: "booking_date", label: "Buchungsdatum *" }, { key: "amount", label: "Betrag" },
  { key: "debit_amount", label: "Sollbetrag" }, { key: "credit_amount", label: "Habenbetrag" },
  { key: "value_date", label: "Valutadatum" }, { key: "currency", label: "Währung" },
  { key: "counterparty", label: "Gegenpartei" }, { key: "purpose", label: "Verwendungszweck" },
  { key: "bank_reference", label: "Bankreferenz" }, { key: "counterparty_identifier", label: "Gegenkonto" },
  { key: "category_hint", label: "Kategoriehinweis" },
]

function firstCsvRow(text: string, delimiter: string): string[] {
  const values: string[] = []
  let value = ""; let quoted = false
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index]
    if (char === '"') {
      if (quoted && text[index + 1] === '"') { value += '"'; index += 1 }
      else quoted = !quoted
    } else if (char === delimiter && !quoted) { values.push(value.trim()); value = "" }
    else if ((char === "\n" || char === "\r") && !quoted) { break }
    else value += char
  }
  values.push(value.trim())
  return values.filter((header) => header.length > 0)
}

function profileBody(name: string, mapping: CsvImportMapping): ImportProfileCreate {
  const columns: CsvColumnMapping = {
    booking_date: mapping.booking_date,
    amount: mapping.amount || null,
    debit_amount: mapping.debit_amount || null,
    credit_amount: mapping.credit_amount || null,
    value_date: mapping.value_date || null,
    currency: mapping.currency || null,
    counterparty: mapping.counterparty || null,
    purpose: mapping.purpose || null,
    bank_reference: mapping.bank_reference || null,
    counterparty_identifier: mapping.counterparty_identifier || null,
    category_hint: mapping.category_hint || null,
  }
  return { name: name.trim(), delimiter: mapping.delimiter, encoding: mapping.encoding, decimal_separator: mapping.decimal_separator, date_format: mapping.date_format, mapping: columns }
}

function profileMapping(profile: ImportProfile): CsvImportMapping {
  return { ...EMPTY_MAPPING, ...profile.mapping, delimiter: profile.delimiter, encoding: profile.encoding, decimal_separator: profile.decimal_separator, date_format: profile.date_format }
}

export function ImportUploadDialog({ accounts, baseCurrency, profiles, onProfilesChanged, onClose, onCreated }: {
  accounts: Account[]
  baseCurrency: string
  profiles: ImportProfile[]
  onProfilesChanged: () => Promise<void>
  onClose: () => void
  onCreated: (batch: ImportBatch) => void
}) {
  const activeAccounts = accounts.filter((account) => !account.archived && account.currency === baseCurrency)
  const [accountId, setAccountId] = useState(String(activeAccounts[0]?.id ?? ""))
  const [file, setFile] = useState<File>()
  const [format, setFormat] = useState<ImportFormat>("auto")
  const [mapping, setMapping] = useState<CsvImportMapping>(EMPTY_MAPPING)
  const [headers, setHeaders] = useState<string[]>([])
  const [previewError, setPreviewError] = useState<string>()
  const [profileId, setProfileId] = useState("")
  const [profileName, setProfileName] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const csvSelected = format === "csv" || (format === "auto" && file?.name.toLowerCase().endsWith(".csv"))

  useEffect(() => {
    if (!file || !csvSelected) { setHeaders([]); setPreviewError(undefined); return }
    let cancelled = false
    file.slice(0, 64 * 1024).arrayBuffer().then((buffer) => {
      const decoderEncoding = mapping.encoding === "utf-8-sig" ? "utf-8" : mapping.encoding
      const text = new TextDecoder(decoderEncoding).decode(buffer)
      const parsed = firstCsvRow(text.replace(/^\uFEFF/, ""), mapping.delimiter)
      if (!parsed.length) throw new Error("Keine CSV-Kopfzeile gefunden.")
      if (!cancelled) { setHeaders(parsed); setPreviewError(undefined) }
    }).catch((cause: unknown) => { if (!cancelled) setPreviewError(errorMessage(cause)) })
    return () => { cancelled = true }
  }, [file, csvSelected, mapping.delimiter, mapping.encoding])

  function chooseProfile(id: string) {
    setProfileId(id)
    const profile = profiles.find((item) => item.id === Number(id))
    if (profile) { setProfileName(profile.name); setMapping(profileMapping(profile)) }
  }
  function validateMapping() {
    if (!mapping.booking_date) throw new Error("Ordne die Spalte für das Buchungsdatum zu.")
    const hasAmount = Boolean(mapping.amount)
    const hasPair = Boolean(mapping.debit_amount && mapping.credit_amount)
    if (hasAmount === hasPair) throw new Error("Ordne entweder einen Betrag oder genau ein Soll-/Haben-Spaltenpaar zu.")
  }
  async function saveProfile() {
    setError(undefined)
    try {
      validateMapping()
      if (!profileName.trim()) throw new Error("Gib einen Profilnamen ein.")
      setBusy(true)
      const selected = profiles.find((item) => item.id === Number(profileId))
      const saved = selected
        ? await haushaltsbuchApi.updateImportProfile(selected.id, { ...profileBody(profileName, mapping), revision: selected.revision })
        : await haushaltsbuchApi.createImportProfile(profileBody(profileName, mapping))
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
      if (csvSelected) validateMapping()
      setBusy(true)
      const batch = await haushaltsbuchApi.createImport({
        file,
        account_id: Number(accountId),
        format,
        csv_mapping: csvSelected ? mapping : undefined,
        profile_id: profileId ? Number(profileId) : undefined,
      })
      onCreated(batch)
    } catch (cause) { setError(cause) } finally { setBusy(false) }
  }

  return <AdminDialog title="Bankexport importieren" eyebrow="Haushaltsbuch · Importe" icon={<FileUp size={16} />} maxWidthClass="max-w-4xl" onClose={busy ? undefined : onClose} footer={<><Button onClick={onClose} disabled={busy}>Abbrechen</Button><Button tone="primary" type="submit" form="import-upload-form" disabled={busy}>{busy ? "Wird geprüft …" : "Als Entwurf hochladen"}</Button></>}>
    <form id="import-upload-form" onSubmit={submit} className="grid gap-5">
      {error !== undefined && <ErrorState error={errorMessage(error)} />}
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="Zielkonto" hint={`Etappe 2 unterstützt Konten in der Haushaltsbasiswährung ${baseCurrency}.`}><Select required value={accountId} onChange={(event) => setAccountId(event.target.value)}><option value="">Auswählen …</option>{activeAccounts.map((account) => <option key={account.id} value={account.id}>{account.name} ({account.currency})</option>)}</Select></Field>
        <Field label="Datei" hint="CAMT XML, MT940 oder CSV; maximal 10 MiB"><Input required type="file" accept=".xml,.mt940,.sta,.txt,.csv,text/csv,application/xml,text/xml" onChange={(event) => setFile(event.target.files?.[0])} /></Field>
        <Field label="Format"><Select value={format} onChange={(event) => setFormat(event.target.value as ImportFormat)}><option value="auto">Automatisch erkennen</option><option value="camt">CAMT V2/V8 (XML)</option><option value="mt940">MT940</option><option value="csv">CSV</option></Select></Field>
      </div>
      {file && <p className={`text-xs ${file.size > MAX_FILE_SIZE ? "text-rose-200" : "text-[#8d9ab0]"}`}>{file.name} · {(file.size / 1024).toLocaleString("de-DE", { maximumFractionDigits: 1 })} KiB</p>}
      {csvSelected && <section className="grid gap-4 rounded-[6px] border border-[#2a364b] bg-[#0d1420] p-4">
        <div><h3 className="font-bold text-[#e8eef8]">CSV-Zuordnung</h3><p className="mt-1 text-xs text-[#8d9ab0]">Die Kopfzeile wird nur lokal im Browser gelesen. Datei und Mapping werden erst beim Upload gemeinsam gesendet.</p></div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Profil"><Select value={profileId} onChange={(event) => chooseProfile(event.target.value)}><option value="">Neues Profil</option>{profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</Select></Field>
          <Field label="Profilname"><Input maxLength={120} value={profileName} onChange={(event) => setProfileName(event.target.value)} placeholder="z. B. Meine Bank" /></Field>
          <div className="flex items-end gap-2"><Button type="button" onClick={saveProfile} disabled={busy}><Save size={13} className="mr-1 inline" />{profileId ? "Aktualisieren" : "Speichern"}</Button>{profileId && <Button type="button" tone="danger" className="px-2" aria-label="Profil löschen" onClick={deleteProfile} disabled={busy}><Trash2 size={13} /></Button>}</div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Trennzeichen"><Select value={mapping.delimiter} onChange={(event) => setMapping({ ...mapping, delimiter: event.target.value as CsvDelimiter })}><option value=";">Semikolon (;)</option><option value=",">Komma (,)</option><option value="\t">Tabulator</option></Select></Field>
          <Field label="Zeichensatz"><Select value={mapping.encoding} onChange={(event) => setMapping({ ...mapping, encoding: event.target.value as CsvEncoding })}><option value="utf-8">UTF-8</option><option value="utf-8-sig">UTF-8 mit BOM</option><option value="cp1252">Windows-1252</option><option value="iso-8859-1">ISO-8859-1</option></Select></Field>
          <Field label="Dezimaltrennzeichen"><Select value={mapping.decimal_separator} onChange={(event) => setMapping({ ...mapping, decimal_separator: event.target.value as "." | "," })}><option value=",">Komma</option><option value=".">Punkt</option></Select></Field>
          <Field label="Datumsformat" hint="Deutsche Jahreszahlen mit zwei oder vier Stellen werden automatisch erkannt."><Input required maxLength={40} value={mapping.date_format} onChange={(event) => setMapping({ ...mapping, date_format: event.target.value })} /></Field>
        </div>
        {previewError && <ErrorState error={previewError} />}
        {!previewError && headers.length > 0 && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{COLUMN_LABELS.map(({ key, label }) => <Field key={key} label={label}><Select required={key === "booking_date"} value={mapping[key] ?? ""} onChange={(event) => setMapping({ ...mapping, [key]: event.target.value })}><option value="">Nicht zuordnen</option>{headers.map((header) => <option key={header} value={header}>{header}</option>)}</Select></Field>)}</div>}
      </section>}
    </form>
  </AdminDialog>
}
