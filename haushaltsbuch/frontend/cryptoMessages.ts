// Crypto-Brücke (V9 Phase 3): laienverständliche Meldungen zu den Fehlercodes des Backends.
export const CRYPTO_MESSAGES: Record<string, string> = {
  crypto_wallet_required: "Nur Konten vom Typ „PayPal/Wallet“ (nicht archiviert) lassen sich mit Cryptoboard verknüpfen.",
  crypto_portfolio_not_found: "Dieses Portfolio gibt es in deinem Cryptoboard nicht (mehr). Bitte wähle ein anderes Portfolio.",
  crypto_account_linked: "Dieses Konto ist mit Cryptoboard verknüpft. Sein Wert kommt live von dort, deshalb sind manuelle Buchungen gesperrt. Trenne zuerst die Verknüpfung oder nutze den Trade-Import.",
  crypto_account_not_linked: "Dieses Konto ist gar nicht mit Cryptoboard verknüpft. Bitte lade die Kontenliste neu.",
  crypto_portfolio_already_linked: "Dieses Portfolio ist bereits mit einem anderen Konto verknüpft.",
  crypto_currency_unsupported: "Die Verknüpfung funktioniert derzeit nur, wenn Haushalt und Konto in Euro (EUR) geführt werden.",
  crypto_wallet_not_linked: "Das Wallet-Konto ist nicht mit Cryptoboard verknüpft. Verknüpfe es zuerst.",
  crypto_link_owner_only: "Trades kann nur das Mitglied importieren, das dieses Konto mit Cryptoboard verknüpft hat.",
  crypto_fiat_account_invalid: "Bitte wähle ein normales Konto (z. B. Girokonto) in Euro, das nicht archiviert und kein Wallet ist.",
  crypto_fee_category_invalid: "Als Gebühren-Kategorie ist nur eine Ausgaben-Kategorie erlaubt.",
  crypto_bridge_unavailable: "Cryptoboard ist gerade nicht erreichbar (nicht installiert oder nicht aktiv). Bitte versuche es später noch einmal.",
  crypto_addresses_required: "Bitte wähle mindestens eine Adresse aus. Zum Entfernen aller Adressen nutze „Alle Adressen lösen“.",
  crypto_address_not_found: "Diese Adresse gibt es in deinem Cryptoboard nicht (mehr). Bitte lade die Liste neu und wähle erneut.",
  crypto_address_already_linked: "Mindestens eine dieser Adressen ist bereits mit einem anderen Konto verknüpft. Löse sie dort zuerst.",
  owner_only: "Nur wer die Verknüpfung angelegt hat oder der Haushaltseigentümer darf das.",
  no_records: "Es gibt keine passenden Einträge, die sich importieren lassen (bei Trades: keine Käufe oder Verkäufe im gewählten Zeitraum).",
}

export const STALE_REASONS: Record<string, string> = {
  module_missing: "Cryptoboard ist nicht installiert.",
  module_not_loaded: "Cryptoboard ist nicht aktiv.",
  port_incompatible: "Cryptoboard hat eine inkompatible Version.",
  portfolio_unavailable: "Das Portfolio liefert gerade keine Werte.",
}
export const staleReason = (reason: string | null): string => (reason && STALE_REASONS[reason]) || "Cryptoboard antwortet gerade nicht."
