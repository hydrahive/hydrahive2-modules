# Cryptoboard – Krypto-Kurse, eigenes Portfolio und Wallets im Blick behalten

Das Cryptoboard zeigt dir Kurse, Charts und News zu Kryptowährungen. Dazu führst du ein eigenes Trade-Logbuch,
aus dem das Cryptoboard Bestände, Gewinn und Verlust in Euro berechnet, und du siehst die Bestände deiner
Wallet-Adressen. Es liest nur: Es handelt nicht, es sendet nichts und es braucht keine privaten Schlüssel.

## So startest du

1. Ein Admin installiert das Modul unter **Module** mit **Installieren**.
2. Öffne das **Cryptoboard** in der Navigation (Gruppe **Arbeiten**, auf der Startseite im Bereich
   **Zuhause & Privat**).
3. Das Cryptoboard ist ein geschützter Bereich. Beim ersten Mal legst du eine Vault-PIN fest (6 bis 12 Ziffern,
   dazu einmal dein Login-Passwort). Danach entsperrst du den Bereich mit dieser PIN.
4. In der **Übersicht** siehst du sofort die Coins mit der höchsten Marktkapitalisierung. Oben im Suchfeld
   **Coin suchen (z.B. Bitcoin)…** findest du jeden Coin und öffnest seine Detailseite.
5. Für dein Portfolio trägst du im Reiter **Trades** mit **Trade hinzufügen** deinen ersten Kauf ein oder lädst
   mit **CSV importieren** einen Export deiner Wallet oder Börse hoch.

## Was du damit machen kannst

Oben rechts wählst du die Währung EUR oder USD. Sie gilt für Übersicht, Coin-Seiten und Vergleich.
Portfolio, Auswertung, Trades, Wallets und Alarme rechnen immer in Euro.

### Übersicht
- **Fear & Greed Index**: die aktuelle Marktstimmung als Zahl von 0 bis 100.
- **Watchlist**: deine gemerkten Coins als Kacheln mit Kurs. Über das Kreuz auf der Kachel nimmst du einen Coin
  wieder heraus.
- **Top nach Marktkapitalisierung**: die 20 größten Coins mit **Preis** und der Änderung über **24h** und **7d**.
  Mit dem Plus am Zeilenende setzt du einen Coin auf die Watchlist.

Ein Klick auf einen Coin öffnet seine Detailseite.

### Coin-Detailseite
Der Chart lässt sich auf **24h**, **7T**, **30T** und **1J** umstellen. Darunter stehen **Rang**, **Marktkap.**,
**Volumen (24h)**, **Allzeithoch**, **Allzeittief** sowie die Coin-Mengen **Umlauf**, **Gesamt** und **Max**.
Mit **Zur Watchlist** bzw. **Aus Watchlist entfernen** pflegst du deine Watchlist, **Zurück** führt zurück.
Der zugeklappte Kasten **Technische Analyse** zeigt für die letzten 90 Tage **Kurs & gleitende Durchschnitte**,
**RSI (14)** und **MACD (12/26/9)**. Ganz unten steht eine kurze Beschreibung des Coins (auf Englisch).

### Portfolio
Oben stehen **Gesamtwert** (mit der Zahl offener **Positionen**), **Nicht realisiert**, **Realisiert (FIFO)** und
**Einstandskosten**. **Verteilung** zeigt als Ring, wie sich der Wert auf die Coins verteilt. Die Tabelle
**Bestände** listet je Coin **Menge**, **Ø-Einstand**, **Kurs**, **Wert**, **G/V** und **Anteil**. Komplett
verkaufte Coins stehen als **geschlossen** darin, weil ihr realisierter Gewinn weiter zählt.
Die Zahlen kommen nur aus deinen eingetragenen Trades, nicht aus den Wallets.

So rechnet das Cryptoboard (FIFO): Ein Verkauf baut immer zuerst den ältesten Kauf ab. Gebühren beim Kauf erhöhen
den Einstand, Gebühren beim Verkauf mindern den Erlös.

### Auswertung
**Aktueller Wert**, **Allzeithoch** (mit Datum), Veränderung über **30 Tage** und **1 Jahr** sowie der Chart
**Portfolio-Wert (letzte 12 Monate)**. Er zeigt den reinen Marktwert deiner Bestände zu Tageskursen in Euro,
keinen Gewinn oder Verlust und keine Steuerangabe. Beim ersten Öffnen werden die Kurse nachgeladen, das kann etwas
dauern. Fehlen für einen Coin Kurse, steht er unter **Keine Kurshistorie für**.

### Trades
Das Logbuch aller Transaktionen mit **Datum**, **Art**, **Coin**, **Menge**, **Preis** und **Gebühr**.
- **Trade hinzufügen**: Coin suchen, Art wählen (**Kauf**, **Verkauf**, **Eingang**, **Ausgang**), dann
  **Menge**, **Stückpreis (€)**, **Gebühr (€)**, **Datum** und eine **Notiz** eintragen und **Hinzufügen**.
  Bei Eingang und Ausgang ist der Preis optional.
- Über den Stift in der Zeile änderst du einen Trade (**Trade bearbeiten**, dann **Speichern**). Der Coin
  selbst lässt sich dabei nicht ändern. Über den Papierkorb löschst du ihn nach einer Rückfrage.
- **Alle löschen** entfernt nach einer Rückfrage alle Trades. Das lässt sich nicht rückgängig machen.
- **CSV importieren**: Mit **CSV-Datei wählen (Wallet-Export)** lädst du die Datei. Das Cryptoboard ordnet die
  Spalten selbst zu. Passt etwas nicht, wählst du für **Art**, **Coin**, **Menge**, **Preis**, **Gebühr** und
  **Datum** die richtige Spalte. Die Vorschau zeigt, was **importierbar** ist, was **bereits importiert** wurde,
  bei welchem Kürzel der **Coin nicht erkannt** wurde und wie viele **fehlerhafte Zeilen** es gibt. Mit
  **Importieren** übernimmst du die importierbaren Zeilen. Fehlgeschlagene oder stornierte Vorgänge aus dem
  Export werden übersprungen, schon importierte Zeilen nicht doppelt gebucht.

### Wallets
Hier trägst du öffentliche Adressen ein und siehst, was darauf liegt. Diese Bestände sind vom Portfolio getrennt.
- **Adresse hinzufügen**: Chain wählen (**Base**, **Ethereum**, **Tron**, **Bitcoin**), **Adresse** und
  optional eine **Bezeichnung** eintragen, dann **Hinzufügen**. Bei Base und Ethereum kannst du die Adresse
  auch mit **Mit Wallet verbinden** aus einer Wallet-Erweiterung im Browser holen. Dabei wird nur die Adresse
  abgefragt, nie eine Transaktion signiert oder gesendet. Wechselst du in der Wallet das Netz, fragt das
  Cryptoboard, ob es die Adresse auch für das andere Netz hinzufügen soll.
- **Wallet-Gesamtwert**: der Euro-Wert aller Adressen zusammen.
- **Token-Übersicht**: alle Token über alle Adressen zusammengefasst. Token ohne Marktpreis stehen mit
  **Wert unbekannt** trotzdem da. **verifiziert** markiert auf Tron geprüfte Token.
- **Adressen & Bestände**: jede Adresse mit ihren Beständen. Über den Papierkorb entfernst du eine Adresse.

#### Trades aus der Blockchain übernehmen
Dafür brauchst du einen eigenen kostenlosen Schlüssel von Alchemy. Im Kasten
**Alchemy-Key (On-Chain-Trade-Import)** fügst du ihn ein und klickst **Testen & speichern**. Der Schlüssel wird
erst geprüft, dann verschlüsselt gespeichert und danach nur noch gekürzt angezeigt. Über das Löschen-Symbol
daneben entfernst du ihn wieder.
- **Trades importieren** an einer Base- oder Ethereum-Adresse sucht Tausch-Vorgänge dieser Adresse und macht daraus
  je einen Verkauf und einen Kauf. Mit **Ältere nachladen** holst du weiter zurückliegende Vorgänge.
- **Trades aller Adressen importieren** fragt alle Base-, Ethereum- und Tron-Adressen auf einmal ab. Zusätzlich
  erkennt es **Chain-übergreifende Tausche**: einen Verkauf auf Tron und einen Kauf auf Base oder Ethereum, die
  zeitlich zusammenpassen. Passen zu einem Verkauf mehrere Käufe, stehen sie unter **Mehrdeutig**, und du wählst
  den richtigen. Unter **Ausgaben / Abgänge** stehen **Kartenzahlungen (MetaMask Card)** und
  **Sonstige Abgänge**. Sie sind nicht vorausgewählt und werden, wenn du sie anhakst, als Ausgang gebucht, nicht als
  Verkauf. Vermutlicher Spam steht zur Kontrolle unter **Ausgeblendet (vermutlich Spam)** und wird nie gebucht.

In beiden Fällen prüfst du die Vorschau: Fehlt ein Coin, ordnest du ihn zu (**Coin zuordnen (Pflicht)**). Fehlt
ein Kurs, trägst du ihn ein (**Preis in € (Pflicht)**). Kurse holt das Cryptoboard nur für die letzten 365 Tage
selbst. Tausch zwischen ETH und WETH (**Wraps (kein Trade)**) und nicht eindeutig erkennbare Vorgänge
(**Unklar**) werden nicht gebucht. Mit **Buchen** übernimmst du die angehakten Einträge ins Trade-Logbuch.
Schon gebuchte Einträge sind als **bereits gebucht** markiert.

### Vergleich
**Performance-Vergleich (% seit Start)** legt die Kursentwicklung mehrerer Coins übereinander, alle ab demselben
Startpunkt in Prozent. Am Anfang sind Bitcoin und Ethereum gewählt. Über **Coin…** fügst du weitere hinzu (bis zu
sechs), über das Kreuz entfernst du einen. Zeitraum: **7T**, **30T**, **90T** oder **1J**.

### Alarme
1. **Alarm erstellen** klicken und die Art wählen: **Kurs über**, **Kurs unter**, **24h-Änd. über**,
   **24h-Änd. unter**, **Portfolio über** oder **Portfolio unter**.
2. Bei Kurs- und 24h-Alarmen den Coin suchen. Portfolio-Alarme beziehen sich auf den Gesamtwert deines Portfolios.
3. Die Schwelle eintragen (**Schwelle (€)** bzw. bei 24h-Änderungen **Schwelle (%)**) und **Erstellen**.

Unter **Aktive Alarme** schaltest du einen Alarm mit der Glocke an oder aus und löschst ihn mit dem Papierkorb.
Das Cryptoboard prüft alle zwei Minuten. Ein Alarm löst nur aus, wenn der Wert die Schwelle gerade überschreitet,
nicht immer wieder, solange er darüber liegt. Ausgelöste Alarme stehen mit Uhrzeit unter **Ausgelöste Alarme**, und
am Reiter **Alarme** erscheint eine rote Zahl. Sie verschwindet, sobald du den Reiter öffnest.

### News
**Krypto-News** zeigt aktuelle Schlagzeilen mit kurzer Vorschau und Quelle, meist auf Englisch. Ein Klick öffnet den
Artikel in einem neuen Tab.

## Mit Buddy und Agenten

Das Cryptoboard bringt drei Werkzeuge mit. Buddy und die anderen Haupt-Agenten bekommen sie automatisch, sobald das
Modul installiert ist.

| Werkzeug | Was es tut |
|---|---|
| `query_crypto_price` | aktueller Kurs von bis zu 25 Coins mit Änderung über 24 Stunden und 7 Tage, Marktkapitalisierung und Volumen, standardmäßig in Euro |
| `query_portfolio` | dein Portfolio: offene Positionen mit Menge und Wert, nicht realisierter und realisierter Gewinn, Gesamtwert in Euro |
| `query_crypto_analysis` | technische Lage eines Coins aus den letzten 90 Tagen: RSI, MACD, Lage zu den Durchschnitten der letzten 20 und 50 Tage, dazu der Fear & Greed Index |

Das kannst du fragen:
- „Was kostet Ethereum gerade?“
- „Wie steht mein Krypto-Portfolio?“
- „Ist Bitcoin laut RSI überkauft?“

Das geht nicht:
- Kaufen, verkaufen oder etwas senden. Es gibt keine Verbindung zu Börsen und keinen Zugriff auf private Schlüssel.
- Trades eintragen, Alarme anlegen, Wallets oder News abfragen. Dafür gibt es keine Werkzeuge.
- Anlageberatung. Die Analyse liefert nur Kennzahlen.

Das Portfolio-Werkzeug sieht nur die Trades der Person, für die der Agent gerade arbeitet.

## Gut zu wissen

- Datenschutz: Watchlist, Trades, Adressen, Alarme und der Alchemy-Schlüssel gehören jeweils dir. Andere
  Nutzer sehen sie nicht. Die gewählte Währung merkt sich dein Browser.
- Vault: Die Seiten des Cryptoboards öffnen sich nur mit entsperrtem Vault. Nach 15 Minuten ohne Nutzung sperrt
  der Vault wieder. Die Werkzeuge für Buddy und Agenten fragen die PIN nicht ab.
- Externe Dienste: Kurse und Charts kommen von CoinGecko, die Marktstimmung von alternative.me, die News von
  CryptoCompare. Wallet-Bestände werden bei öffentlichen Diensten der jeweiligen Blockchain abgefragt, der
  Blockchain-Import läuft über Alchemy und für Tron über Tronscan. Dabei gehen deine Adressen an diese Dienste.
- Kosten: Ohne eigene Schlüssel läuft alles mit den kostenlosen Grenzen der Dienste. Ein Admin kann unter
  **Globale Einstellungen** in der Gruppe „Krypto“ optional einen „CoinGecko API-Key“ (mehr Abfragen) und einen
  „CryptoCompare API-Key“ (News) eintragen.
- Aktualität: Kurse werden bis zu eine Minute zwischengespeichert, Charts und News bis zu fünf Minuten.
- Wallets: Auf Base liest das Cryptoboard nur ETH und USDC, auf Ethereum nur ETH, USDT und USDC. Auf Tron
  erscheinen alle Token, auf Bitcoin der BTC-Bestand. Ist eine Adresse nicht abrufbar, steht dort
  **Kein Guthaben / nicht abrufbar**.
- Rechenregeln: Ein **Eingang** ohne Preis zählt mit Einstand 0, beim späteren Verkauf also voll als Gewinn.
  Verkaufst du mehr, als eingetragen ist, rechnet das Cryptoboard den Rest ebenfalls mit Einstand 0 und zeigt
  keinen negativen Bestand.
- Grenzen: bis zu 5000 Trades, 100 Adressen und 200 Alarme je Person. Eine CSV-Datei darf bis zu 2 MB und 5000
  Zeilen haben.
- Alarme melden sich nur im Cryptoboard. Willst du eine Mail oder Chat-Nachricht, baust du im Butler einen Ablauf
  mit dem Auslöser „Krypto-Kurs“ und der Bedingung „Kurs-Schwelle gekreuzt“ (Schwelle in Euro).
- Haushaltsbuch: Ist das Modul Haushaltsbuch installiert, kann es deine Cryptoboard-Adressen, deren Bestände,
  den Wert deines Portfolios, deine Trades und die aus der Blockchain gebuchten Kartenzahlungen und Tausche
  lesen. Wie das geht, steht in der Hilfe zum Haushaltsbuch.
- Typische Meldungen beim Blockchain-Import:
  - „Kein Alchemy-Key hinterlegt.“ – erst den Schlüssel im Kasten unten auf der Seite speichern.
  - „Der Key ist für dieses Netz nicht freigegeben …“ – in deiner Alchemy-App „Base Mainnet“ bzw.
    „Ethereum Mainnet“ einschalten.
  - „Der On-Chain-Import ist auf diesem Server abgeschaltet.“ – der Betreiber hat den Import für die ganze
    Installation ausgeschaltet.
  - „Ledger voll“ – die Grenze von 5000 Trades ist erreicht.

*Stand: Cryptoboard 1.9.2, 22.11.2026*
