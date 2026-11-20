import { Save, Trash2 } from "lucide-react"
import { COLUMN_LABELS } from "./csvMapping"
import type { CsvDelimiter, CsvEncoding, CsvImportMapping, CsvPreview, ImportProfile } from "./types"
import { Button, ErrorState, Field, Input, Select } from "./ui"

const SECTION = "grid gap-4 rounded-[6px] border border-[rgb(var(--hh-s-rand,42_54_75))] bg-[rgb(var(--hh-s-tief,13_20_32))] p-4"

/** Unterdialog „CSV-Zuordnung“ (Format „CSV“ oder unbekannte Bank bei „Automatisch“). */
export function CsvMappingSection({ mapping, onMapping, headers, previewError, preview, notice, profiles, profileId, profileName, onProfileId, onProfileName, onSave, onDelete, busy }: {
  mapping: CsvImportMapping
  onMapping: (mapping: CsvImportMapping) => void
  headers: string[]
  previewError?: string
  preview?: CsvPreview
  notice?: string
  profiles: ImportProfile[]
  profileId: string
  profileName: string
  onProfileId: (id: string) => void
  onProfileName: (name: string) => void
  onSave: () => void
  onDelete: () => void
  busy: boolean
}) {
  return <section className={SECTION}>
    <div><h3 className="font-bold text-[#e8eef8]">CSV-Zuordnung</h3><p className="mt-1 text-xs text-[#9aa7bc]">Die Kopfzeile wird nur lokal im Browser gelesen. Datei und Mapping werden erst beim Upload gemeinsam gesendet.</p></div>
    {notice && <p role="status" className="rounded border border-amber-500/35 bg-amber-500/10 p-3 text-sm text-amber-100">{notice}</p>}
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Field label="Profil"><Select value={profileId} onChange={(event) => onProfileId(event.target.value)}><option value="">Neues Profil</option>{profiles.map((profile) => <option key={profile.id} value={profile.id}>{profile.name}</option>)}</Select></Field>
      <Field label="Profilname"><Input maxLength={120} value={profileName} onChange={(event) => onProfileName(event.target.value)} placeholder="z. B. Meine Bank" /></Field>
      <div className="flex items-end gap-2"><Button type="button" onClick={onSave} disabled={busy}><Save size={13} className="mr-1 inline" />{profileId ? "Aktualisieren" : "Speichern"}</Button>{profileId && <Button type="button" tone="danger" className="px-2" aria-label="Profil löschen" onClick={onDelete} disabled={busy}><Trash2 size={13} /></Button>}</div>
    </div>
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      <Field label="Trennzeichen"><Select value={mapping.delimiter} onChange={(event) => onMapping({ ...mapping, delimiter: event.target.value as CsvDelimiter })}><option value=";">Semikolon (;)</option><option value=",">Komma (,)</option><option value={"\t"}>Tabulator</option></Select></Field>
      <Field label="Zeichensatz" hint={mapping.encoding === "auto" && preview ? `Erkannt: ${preview.encoding}` : undefined}><Select value={mapping.encoding} onChange={(event) => onMapping({ ...mapping, encoding: event.target.value as CsvEncoding })}><option value="auto">Automatisch</option><option value="utf-8">UTF-8</option><option value="utf-8-sig">UTF-8 mit BOM</option><option value="cp1252">Windows-1252</option><option value="iso-8859-1">ISO-8859-1</option></Select></Field>
      <Field label="Dezimaltrennzeichen"><Select value={mapping.decimal_separator} onChange={(event) => onMapping({ ...mapping, decimal_separator: event.target.value as "." | "," })}><option value=",">Komma</option><option value=".">Punkt</option></Select></Field>
      <Field label="Datumsformat" hint="Deutsche Jahreszahlen mit zwei oder vier Stellen werden automatisch erkannt."><Input required maxLength={40} value={mapping.date_format} onChange={(event) => onMapping({ ...mapping, date_format: event.target.value })} /></Field>
    </div>
    {previewError && <ErrorState error={previewError} />}
    {!previewError && headers.length > 0 && <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{COLUMN_LABELS.map(({ key, label }) => <Field key={key} label={label}><Select required={key === "booking_date"} value={mapping[key] ?? ""} onChange={(event) => onMapping({ ...mapping, [key]: event.target.value })}><option value="">Nicht zuordnen</option>{headers.map((header) => <option key={header} value={header}>{header}</option>)}</Select></Field>)}</div>}
    {preview && preview.sample_rows.length > 0 && <SampleRows preview={preview} />}
  </section>
}

function SampleRows({ preview }: { preview: CsvPreview }) {
  return <div className="overflow-x-auto" data-testid="csv-sample-rows"><p className="mb-1 text-xs font-bold text-[#b5c1d2]">Beispielzeilen aus der Datei</p><table className="w-full text-left text-[11px] text-[#c4cfdd]"><thead><tr>{preview.header.map((name, index) => <th key={`${name}-${index}`} className="border-b border-[#33425a] px-2 py-1">{name}</th>)}</tr></thead><tbody>{preview.sample_rows.map((cells, rowIndex) => <tr key={rowIndex}>{cells.map((cell, index) => <td key={index} className="max-w-[14rem] truncate border-b border-[#33425a] px-2 py-1">{cell}</td>)}</tr>)}</tbody></table></div>
}
