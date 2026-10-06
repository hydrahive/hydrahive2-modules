// KI-Vorschläge: Datenform, Vergleich alt/neu und (im Entwurf) eine Platzhalter-KI.
// Grundregel der Spec: Ein Vorschlag ändert nichts, bis er angenommen wird.

export type SuggestAction = "rewrite" | "expand" | "shorten" | "continue"

export interface Suggestion {
  id: string
  sceneId: string
  action: SuggestAction
  /** Markierter Originaltext (bei „continue“ leer). */
  original: string
  proposal: string
  /** Position im Editor (ProseMirror), nur gültig solange die Szene unverändert ist. */
  from: number
  to: number
  createdAt: string
  state: "open" | "accepted" | "rejected"
}

export interface DiffPart { kind: "same" | "del" | "add"; text: string }

/** Wortweiser Vergleich (LCS) für die Anzeige „gelöscht rot / neu grün“. */
export function wordDiff(a: string, b: string): DiffPart[] {
  const x = a.split(/(\s+)/).filter(Boolean)
  const y = b.split(/(\s+)/).filter(Boolean)
  if (x.length * y.length > 250_000) {
    return [{ kind: "del", text: a }, { kind: "add", text: b }].filter((p) => p.text) as DiffPart[]
  }
  const dp: number[][] = Array.from({ length: x.length + 1 }, () => new Array(y.length + 1).fill(0))
  for (let i = x.length - 1; i >= 0; i--) {
    for (let j = y.length - 1; j >= 0; j--) {
      dp[i][j] = x[i] === y[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }
  const out: DiffPart[] = []
  const push = (kind: DiffPart["kind"], text: string) => {
    const last = out[out.length - 1]
    if (last && last.kind === kind) last.text += text
    else out.push({ kind, text })
  }
  let i = 0
  let j = 0
  while (i < x.length && j < y.length) {
    if (x[i] === y[j]) { push("same", x[i]); i++; j++ }
    else if (dp[i + 1][j] >= dp[i][j + 1]) push("del", x[i++])
    else push("add", y[j++])
  }
  while (i < x.length) push("del", x[i++])
  while (j < y.length) push("add", y[j++])
  return out
}

/**
 * Platzhalter-KI für den klickbaren Entwurf (kein Modellaufruf, keine Kosten).
 * Liefert sichtbar markierte Beispieltexte, damit der Ablauf Vorschlag → Annehmen/Ablehnen
 * ausprobiert werden kann. Im Ausbau ersetzt durch den Backend-Aufruf (Spec §7).
 */
export function draftSuggestion(action: SuggestAction, original: string, variant = 0): string {
  const text = original.trim()
  const sentences = text.split(/(?<=[.!?…«])\s+/).filter(Boolean)
  switch (action) {
    case "shorten":
      return sentences.length > 1
        ? sentences.filter((_, i) => i % 2 === 0).join(" ")
        : text.split(/\s+/).slice(0, Math.max(3, Math.ceil(text.split(/\s+/).length * 0.6))).join(" ")
    case "expand":
      return `${text} ${["Für einen Augenblick war es ganz still.", "Draußen schlug der Regen gegen das Fensterblech.", "Niemand im Haus schien etwas zu bemerken."][variant % 3]}`
    case "rewrite":
      return sentences.length > 1 ? [...sentences].reverse().join(" ") : `${text.replace(/\.$/, "")} – so jedenfalls schien es.`
    case "continue":
      return ["Erst nach einer Weile wagte er, sich zu rühren.", "Da klopfte es leise an der Tür.", "Er beschloss, noch ein wenig zu warten."][variant % 3]
  }
}
