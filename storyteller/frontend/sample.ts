// Beispielbuch: „Die Verwandlung“ (Franz Kafka, 1915), gemeinfrei.
// Quelle: Projekt Gutenberg #22367. Kapitel wie im Original, je Kapitel 3 Szenen
// (an Absatzgrenzen geteilt), „--“ zu „–“ modernisiert. Wird erst beim Öffnen geladen.
import { GHOST_EMPTY, newId, type Book, type Entity } from "./model"

interface SampleScene { title: string; summary: string; paras: string[] }
interface SampleFile { chapters: { title: string; scenes: SampleScene[] }[] }

const ent = (kind: Entity["kind"], name: string, aliases: string[], description: string,
  fields: [string, string][] = []): Entity => ({
  id: newId(), kind, name, aliases, description, fields: fields.map(([key, value]) => ({ key, value })),
})

export async function loadSampleBook(): Promise<Book> {
  const data = (await import("./sample/verwandlung.json")).default as SampleFile
  return {
    id: newId(),
    title: "Die Verwandlung",
    kind: "novel",
    language: "de",
    audience: "Erwachsene",
    idea: "Ein Handlungsreisender erwacht als Ungeziefer, und seine Familie muss damit leben.",
    model: "",
    ghost: { ...GHOST_EMPTY },
    notes: "Beispielbuch (gemeinfrei, Projekt Gutenberg #22367). Zum Ausprobieren: Text ändern, Szenen verschieben, KI-Vorschläge testen.",
    updatedAt: new Date().toISOString(),
    parts: [{
      id: newId(),
      title: "Die Verwandlung",
      chapters: data.chapters.map((c) => ({
        id: newId(),
        title: c.title,
        scenes: c.scenes.map((s) => ({
          id: newId(), title: s.title, summary: s.summary, pov: "Gregor",
          status: "done" as const, origin: "human" as const, text: s.paras.join("\n\n"),
        })),
      })),
    }],
    entities: [
      ent("character", "Gregor", ["Gregor Samsa", "Samsa"], "Handlungsreisender, ernährt die Familie. Erwacht als Ungeziefer.",
        [["Beruf", "Reisender in Tuchwaren"], ["Zimmer", "neben dem Wohnzimmer, drei Türen"]]),
      ent("character", "Grete", ["die Schwester", "Schwester"], "Gregors siebzehnjährige Schwester, spielt Violine.",
        [["Alter", "17"], ["Wunsch", "Konservatorium"]]),
      ent("character", "Der Vater", ["Vater"], "Seit dem Geschäftszusammenbruch untätig, später Bankdiener."),
      ent("character", "Die Mutter", ["Mutter"], "Leidet an Asthma, liebt Gregor, kann seinen Anblick kaum ertragen."),
      ent("character", "Der Prokurist", ["Prokurist"], "Vorgesetzter aus der Firma, kommt am ersten Morgen nachsehen."),
      ent("place", "Gregors Zimmer", ["Zimmer"], "Kleines Menschenzimmer mit Bild der Dame im Pelz."),
      ent("item", "Der Apfel", ["Apfel", "Äpfel"], "Vom Vater geworfen, bleibt in Gregors Rücken stecken."),
    ],
  }
}
