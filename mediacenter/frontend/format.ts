import type { MediaType } from "./types"

export const MEDIA_TYPES: { id: MediaType; label: string }[] = [
  { id: "movie", label: "Filme" },
  { id: "tv", label: "Serien" },
  { id: "book", label: "Bücher" },
  { id: "audiobook", label: "Hörbücher" },
  { id: "audioplay", label: "Hörspiele" },
  { id: "music", label: "Musik" },
]

const REASONS: Record<string, string> = {
  eligible: "Profil erfüllt",
  german_confirmed: "Deutsch bestätigt",
  resolution_allowed: "Zulässige Auflösung",
  format_allowed: "Zulässiges Format",
  requested_artist_match: "Künstler passt",
  requested_album_complete: "Vollständiges Album",
  requested_album_incomplete: "Unvollständiges Album",
  requested_year_match: "Jahr passt",
  category_mismatch: "Falsche Indexer-Kategorie",
  language_unconfirmed: "Deutsche Sprache nicht bestätigt",
  resolution_missing: "Auflösung fehlt",
  resolution_rejected: "Auflösung nicht zulässig",
  forbidden_source: "Nicht zulässige Aufnahmequelle",
  format_rejected: "Format nicht zulässig",
  format_missing: "Format nicht erkannt",
  sample_or_incomplete: "Sample oder unvollständig",
  size_unknown: "Größe unbekannt",
  size_below_minimum: "Unter Mindestgröße",
  size_above_maximum: "Über Maximalgröße",
  age_unknown: "Alter unbekannt",
  age_above_maximum: "Älter als erlaubt",
}

export function reasonLabel(reason: string): string {
  return REASONS[reason] ?? reason.replaceAll("_", " ")
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null || !Number.isFinite(bytes) || bytes < 0) return "Größe unbekannt"
  const units = ["B", "KB", "MB", "GB", "TB"]
  let value = bytes
  let index = 0
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024
    index += 1
  }
  return `${value.toFixed(index > 1 ? 1 : 0)} ${units[index]}`
}

export function formatSpeed(kbps: number | null): string | null {
  if (kbps === null || !Number.isFinite(kbps) || kbps < 0) return null
  return kbps >= 1024 ? `${(kbps / 1024).toFixed(1)} MB/s` : `${kbps.toFixed(0)} KB/s`
}

export function formatDate(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? "–" : date.toLocaleString()
}
