/** Nur die zuletzt gestartete Anfrage zählt (Projektwechsel, schnelles Neuladen). Spätere Antworten älterer Anfragen
 *  werden verworfen, sonst überschreiben sie die Daten des inzwischen gewählten Projekts. */
export function latestOnly() {
  let seq = 0
  return {
    async run<T>(_key: string, fn: () => Promise<T>): Promise<{ current: true; value: T } | { current: false; value: undefined }> {
      const mine = ++seq
      try {
        const value = await fn()
        return mine === seq ? { current: true as const, value } : { current: false as const, value: undefined }
      } catch (e) {
        if (mine !== seq) return { current: false as const, value: undefined }
        throw e
      }
    },
  }
}
