# Hydra-Labor – Bauplan Etappe L1 (Labor ohne GitHub)

> Grundlage: `SPEC.md` (freigegeben 30.10.), Kern K1 (`docs/specs/projekt-container-ausfuehrung.md`, gemergt #669).
> Ziel von L1: Ein Admin richtet mit dem Assistenten ein Labor ein. Danach arbeitet der Labor-Agent nur im Container,
> kommt nicht an den Server oder ins Heimnetz, und „Zurücksetzen“ bringt den Container auf „frisch“.
> GitHub (Fork, Einreichen, Fehler melden) kommt in L2.

## Befunde vorab (gemessen 30.10., hydratest, incus 6.0)

- **Netzsperre über ein eigenes Netz mit Bridge-ACL** funktioniert: eigenes incus-Netz (NAT) mit `security.acls`
  am **Netz** (nicht am NIC – das kennt incus 6.0 für Bridges nicht). Gemessen mit einem frischen Container:
  Gateway des eigenen Netzes, `hhnat0`-Gateway, Server-IP und Heimnetz-Router **zu**; 1.1.1.1:443, github.com **offen**;
  DNS geht.
- Ohne Sperre war aus dem Container die HydraHive-Oberfläche des Servers über 443 erreichbar (K1-Probe 6).
- Ein ACL an einem bestehenden Netz wirkt erst für neu verbundene Container (am laufenden NIC nicht sofort).
  → Das Modul legt Netz + ACL **vor** dem Container an.

## Bausteine

1. **Netz `hhlabor0`** (eigenes, nur fürs Labor): `ipv4.address=10.77.0.1/24`, `ipv4.nat=true`,
   `ipv6.address=none`, `security.acls=hhlabor-acl`.
   - Liegt die Adresse schon im Heimnetz des Nutzers? Das Modul wählt aus `10.77.0.0/24`, `10.78.0.0/24`,
     `172.31.77.0/24` das erste Netz, das nicht in `ip route` vorkommt.
2. **ACL `hhlabor-acl`**:
   - egress `reject` nach `10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16, 100.64.0.0/10, 169.254.0.0/16,
     127.0.0.0/8, fc00::/7, fe80::/10` (auch die eigene Gateway-IP liegt darin).
   - egress `allow` sonst. DNS geht über dnsmasq des Netzes – das ist nicht über das ACL gesperrt (gemessen).
   - ingress: nichts erlauben.
   - **Probe nach dem Anlegen** (Pflicht, sonst Abbruch): aus dem Container `10.x.0.1:443`, Server-IP:443 und
     Standard-Gateway des Servers:80 müssen „zu“ sein, `github.com` muss auflösbar sein.
3. **Container `hh-labor`** über die vorhandene Container-Verwaltung des Kerns (`containers/`), nicht direkt incus:
   - Bild: Ubuntu wie der Server (`images:ubuntu/<version>`), unprivilegiert, `security.nesting=true`
     (wie Kern-Standard), Grenzen 2 CPU / 4 GB RAM / 20 GB (einstellbar im Assistenten).
   - NIC an `hhlabor0`, kein `br0`.
   - Nutzer `labor` (UID 1000), `/work` gehört ihm, `/home/labor`.
   - Einrichtung im Container (als root, einmalig): `git`, `python3-venv`, `python3-pip`, `nodejs`/`npm`, `build-essential`,
     `ripgrep`. Klon von `hydrahive/hydrahive2.0` und `hydrahive/hydrahive2-modules` **ohne Zugangsdaten** nach
     `/work/hydrahive2` bzw. `/work/hydrahive2-modules` (öffentlich, https). Python-venv für die Kern-Tests,
     `npm ci` im Frontend. Fortschritt in Schritten.
   - Danach **Schnappschuss `frisch`**.
4. **Projekt „Hydra-Labor“** über die Kern-API, dann `execution.set_container(pid, "hh-labor")`.
5. **Labor-Agent** als Projekt-Agent: Werkzeuge = K1-Allowlist ohne `fetch_url` (Labor braucht es nicht), Prompt
   aus `hydralabor/agent/PROMPT.md`, Skills `test`, `debugging`, `code-review` und `labor-review` (Kurzfassung hh-review),
   Modell aus dem Assistenten. Danach `set_managed(aid, "hydralabor")`.

## Assistent (Seite „Hydra-Labor“, nur Admin)

Ein Zustand je Server in `module_hydralabor_state` (eine Zeile): Schritt, Fehlercode, Namen von Netz/Container/Projekt/
Agent, Zeitstempel. Jeder Schritt ist **wiederholbar** (prüft, ob schon erledigt) und **abbrechbar**.

| Schritt | Knopf | macht | grün wenn |
|---|---|---|---|
| 1 Voraussetzungen | „Prüfen“ | incus da, Version ≥ 6.0, Speicher ≥ 15 GB frei im Pool, RAM ≥ 4 GB frei, K1 im Kern vorhanden | alles ok |
| 2 Modell | Auswahl | Liste der Chat-Modelle des Servers | eines gewählt |
| 3 Labor anlegen | „Labor anlegen“ | Netz+ACL+Probe, Container, Einrichtung, Schnappschuss, Projekt, Agent | alles ok, Netzprobe grün |
| 4 Fertig | „Zum Labor-Chat“ | Einführung, Beispiele | – |

Lange Schritte (Einrichtung ~5–15 min) laufen im Hintergrund als Auftrag; die Seite fragt alle 3 s den Stand ab.

## Labor-Seite (nach dem Einrichten)

- Stand: Container läuft/aus, belegter Platz, Netzsperre aktiv (letzte Probe mit Zeit).
- Knöpfe: „Starten“/„Stoppen“, **„Testlauf“** (Kern-Tests im Container, Ergebnis-Zusammenfassung),
  **„Netz prüfen“** (Probe aus Baustein 2), **„Zurücksetzen“** (eigener Dialog → Schnappschuss `frisch` wiederherstellen),
  **„Labor entfernen“** (eigener Dialog mit Eingabe „LABOR“ → Agent, Projekt, Container, Netz, ACL weg).
- Kein Terminal, keine incus-Begriffe in der Oberfläche.

## Sicherheit

- Alle incus-Aufrufe mit festen Argumentlisten, Namen fest im Modul (`hh-labor`, `hhlabor0`, `hhlabor-acl`).
- Das Modul ruft incus über den Kern (Container-Verwaltung bzw. `incus_client._run`), nie über eine Shell.
- Der Labor-Agent hat keine Möglichkeit, das Netz oder den Container zu ändern (kein incus im Container, keine
  Kern-Werkzeuge).
- „Labor entfernen“ löscht nur, was im Zustand als vom Modul angelegt steht.

## Tests

- Rot zuerst. incus als Attrappe (Aufrufe mitschreiben).
- Netzwahl: belegte Bereiche werden übersprungen; alle belegt → klarer Fehler.
- ACL: genau die Regeln oben; Reihenfolge Netz → ACL → Probe → Container.
- Probe: wenn ein gesperrtes Ziel erreichbar ist → Abbruch mit `labor_net_open`, Container wird wieder entfernt.
- Schritte idempotent (zweimal „Labor anlegen“ legt nichts doppelt an).
- Zurücksetzen nur auf `frisch`, nur für `hh-labor`.
- Entfernen löscht nur Eigenes.
- Agent: managed_by hydralabor, Werkzeuge = Allowlist-Teilmenge, Projekt = Container-Ausführung.
- Mutanten, Gegenprobe, volle Reihe; **echt auf hydratest**: Assistent komplett, Netzprobe, 12 Ausbruchsproben aus K1
  jetzt mit Netzsperre (443 muss zu sein), Testlauf, Zurücksetzen, Entfernen; E2E 4 Breiten.

## Offen für Till

1. Grenzen Standard 2 CPU / 4 GB RAM / 20 GB ok?
2. Heimnetz-Sperre gilt auch für Tailscale (100.64/10) – ok? (Vorschlag: ja.)
