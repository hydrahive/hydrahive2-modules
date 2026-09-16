# Plan: UDP NAT Contact Rewrite für Gate 2

## Ziel

Gate 2 registriert Baresip über einen stabilen UDP-Socket und kündigt nach einer
authentischen Registrar-Antwort das von `Via received`/`rport` beobachtete NAT-Tupel
als SIP-Contact an. Eingehende INVITEs können dadurch den bereits bestehenden
UniFi-Conntrack-Flow nutzen, ohne Portfreigabe oder SIP ALG.

## Dateien

- `telephony/patches/libre-rport-contact.patch` — opt-in Lernen und Verwenden des
  `received`/`rport`-Contacts in libre 4.11 samt Upstream-Unit-Test.
- `telephony/patches/baresip-rport-contact.patch` — neuer Account-Modus
  `sipnat=received`, Übergabe an libre und externe Dialog-Contacts samt Unit-Test.
- `telephony/spike/prepare-runtime.sh` — gepinnte Patches in der isolierten Sidecar-
  Buildumgebung anwenden und die betroffenen Upstream-Tests ausführen.
- `telephony/spike/config.py` — Gate 2 auf UDP, stabilen Port 5060 und
  `sipnat=received` umstellen.
- `telephony/tests/test_spike_config.py` — sichere Gate-2-Konfiguration prüfen.
- `telephony/tests/test_nat_contact_patches.py` — Patch-Pinning, Opt-in-Verhalten und
  Buildintegration als Repository-Vertrag prüfen.
- `telephony/spike/README.md`, `telephony/SPEC-INCOMING-CALL-GATE.md`,
  `telephony/GATEWAY-CONTRACT.md` — Verhalten, Grenzen und Rückfalloption
  dokumentieren.

## Implementierungsreihenfolge

### Task 1: Harness-Vertrag auf UDP-NAT umstellen

- [x] Tests für UDP, festen Listener, `sipnat=received` und fehlendes Outbound schreiben.
- [x] Tests rot ausführen.
- [x] Minimale Konfigurationsänderung implementieren.
- [x] Tests grün ausführen.

### Task 2: Gepinnte libre-Erweiterung

- [x] Upstream-Test ergänzen: Modus ist opt-in, UDP lernt Via-`received`/`rport`, ein
      Folgeregister verwendet den gelernten Contact, TCP bleibt unverändert.
- [x] Test vor Implementierung rot ausführen.
- [x] `sipreg_enable_rport_contact` und `sipreg_contact_addr` implementieren.
- [x] Upstream-Test grün ausführen und Patch exportieren.

### Task 3: Gepinnte Baresip-Erweiterung

- [x] Account-Test für `sipnat=received` ergänzen.
- [x] Test vor Implementierung rot ausführen.
- [x] Modus validieren, libre aktivieren und gelernten Contact für SIP-Dialogantworten
      verwenden.
- [x] Upstream-Test grün ausführen und Patch exportieren.

### Task 4: Reproduzierbarer Sidecar-Build

- [x] Repository-Vertragstest für exakt zwei Patches und deren Anwendung ergänzen.
- [x] Patches vor dem Build in die Incus-Instanz kopieren.
- [x] Patches ausschließlich auf die gepinnten SHAs anwenden.
- [x] Betroffene Upstream-Tests im Build ausführen.
- [x] Gesamten Sidecar-Build lokal verifizieren.

### Task 5: Dokumentation und echter Gate-2-Test

- [x] Dokumentation von TCP/RFC-5626 auf UDP/Contact-Rewrite aktualisieren.
- [x] Telephony-Modultests und die gepinnten Upstream-Selftests ausführen.
- [x] Sidecar neu erstellen/synchronisieren.
- [ ] Gate 2 gegen die echte FRITZ!Box ausführen; Nutzer löst einen Anruf aus.
- [ ] Bei Erfolg keine Firewalländerung vornehmen; bei ausbleibendem INVITE auf die
      dokumentierte statische Route als separaten Folgeschritt wechseln.

## Akzeptanzkriterien

- [x] Contact-Rewrite ist ausschließlich mit `sipnat=received` aktiv.
- [x] Nur finale UDP-Antworten mit gültigem `received` und numerischem `rport` werden
      gelernt.
- [x] Der gelernte Wert wird nicht als Zieladresse verwendet, sondern nur angekündigt.
- [x] Gate 2 bindet SIP stabil an UDP 5060 und öffnet keinen Management-Port außerhalb
      von Loopback.
- [x] Gepinnte Quellstände und Patches bauen reproduzierbar.
- [x] Keine Zugangsdaten oder rohen SIP-Payloads werden persistiert oder protokolliert.
- [ ] Der echte Test liefert `incoming_answered` oder einen klaren, geheimnisfreien
      Fehlerstatus.

## Nicht in diesem Plan

- UniFi-Portfreigaben, SIP ALG oder breite Firewallregeln.
- Produktiver Telephony-Backendbetrieb.
- Empfangsrichtung für Audio; Gate 2 bleibt bei sendonly-Ton.
- Automatische Routerkonfiguration.
