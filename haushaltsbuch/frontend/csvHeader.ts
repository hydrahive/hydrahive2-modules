// Kopfzeilen-Vorschau einer CSV im Browser (nichts wird gesendet).

/** Erste Zeile einer CSV in Felder zerlegen (Anführungszeichen, Trennzeichen). */
export function firstCsvRow(text: string, delimiter: string): string[] {
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

/** Browser-Entsprechung zur Backend-Erkennung: erst UTF-8, bei Ersatzzeichen (U+FFFD) Windows-1252.
 *  `truncated`: der Puffer ist nur der Dateianfang – ein am Ende abgeschnittenes UTF-8-Zeichen zählt nicht als Fehler. */
export function decodeAuto(buffer: ArrayBuffer, truncated = false): { text: string; encoding: "utf-8" | "windows-1252" } {
  const utf8 = (bytes: Uint8Array) => new TextDecoder("utf-8", { fatal: false }).decode(bytes)
  const bytes = new Uint8Array(buffer)
  for (let cut = 0; cut <= (truncated ? 3 : 0); cut += 1) {
    const text = utf8(bytes.subarray(0, bytes.length - cut))
    if (!text.includes("\uFFFD")) return { text, encoding: "utf-8" }
  }
  return { text: new TextDecoder("windows-1252").decode(bytes), encoding: "windows-1252" }
}

/** Text der Kopfvorschau für den gewählten Zeichensatz („auto“ = erkennen). */
export function decodePreview(buffer: ArrayBuffer, encoding: string, truncated = false): string {
  if (encoding === "auto") return decodeAuto(buffer, truncated).text
  const label = encoding === "utf-8-sig" ? "utf-8" : encoding
  return new TextDecoder(label).decode(buffer)
}
