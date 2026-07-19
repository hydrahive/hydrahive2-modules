(() => {
  "use strict";

  const STATE_KEY = "paybackBridgeStateV1";
  const IMPORT_PATH = "/api/modules/haushaltsbuch/loyalty/payback/bridge/import";
  const { STATE_TTL_MS, emptyState, mergeCapture, usefulRecordCount } =
    globalThis.PaybackBridgeState;


  const elements = {
    form: document.querySelector("#settings-form"),
    origin: document.querySelector("#origin"),
    pairingCode: document.querySelector("#pairing-code"),
    capture: document.querySelector("#capture"),
    send: document.querySelector("#send"),
    clear: document.querySelector("#clear"),
    status: document.querySelector("#status"),
    warning: document.querySelector("#warning"),
    lastPage: document.querySelector("#last-page"),
    counts: {
      balance: document.querySelector("#balance-count"),
      expirations: document.querySelector("#expiration-count"),
      activities: document.querySelector("#activity-count"),
      coupons: document.querySelector("#coupon-count"),
      partners: document.querySelector("#partner-count"),
      pages: document.querySelector("#page-count"),
    },
  };

  let state = emptyState();
  let saveTimer = null;

  function render() {
    const payload = state.payload;
    elements.origin.value = state.origin || "";
    elements.pairingCode.value = state.pairing_code || "";
    elements.counts.balance.textContent = payload.balance ? "1" : "0";
    elements.counts.expirations.textContent = String(payload.expirations.length);
    elements.counts.activities.textContent = String(payload.activities.length);
    elements.counts.coupons.textContent = String(payload.coupons.length);
    elements.counts.partners.textContent = String(payload.partners.length);
    elements.counts.pages.textContent = String(state.pages.length);
    const latest = state.pages[state.pages.length - 1];
    elements.lastPage.textContent = latest ? `Zuletzt: ${latest.title || latest.url}` : "Noch keine PAYBACK-Seite erfasst.";
    const unknownDom = state.warnings.includes("unknown_dom_version");
    elements.warning.hidden = !unknownDom;
    elements.warning.textContent = unknownDom
      ? "Auf mindestens einer Seite wurden keine bekannten sichtbaren Daten erkannt. PAYBACK könnte die Seite geändert haben; es wurden keine Werte geschätzt."
      : "";
  }

  function setStatus(message, isError = false) {
    elements.status.textContent = message;
    elements.status.classList.toggle("error", isError);
  }

  function setBusy(busy) {
    elements.capture.disabled = busy;
    elements.send.disabled = busy;
    elements.clear.disabled = busy;
  }

  async function persist() {
    state.updated_at = new Date().toISOString();
    await chrome.storage.session.set({ [STATE_KEY]: state });
  }

  function updateSettingsFromForm() {
    state.origin = elements.origin.value.trim();
    state.pairing_code = elements.pairingCode.value.trim();
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => {
      persist().catch(() => setStatus("Lokales Speichern fehlgeschlagen.", true));
    }, 250);
  }

  function normalizedOrigin(raw) {
    let url;
    try {
      url = new URL(raw);
    } catch (_error) {
      throw new Error("Bitte eine gültige HydraHive-Origin eingeben.");
    }
    const loopback = ["localhost", "127.0.0.1"].includes(url.hostname);
    if ((url.protocol !== "https:" && !(url.protocol === "http:" && loopback)) || url.username || url.password || url.origin === "null") {
      throw new Error("Die HydraHive-Origin muss HTTPS verwenden (HTTP ist nur lokal erlaubt).");
    }
    if ((url.pathname && url.pathname !== "/") || url.search || url.hash) {
      throw new Error("Bitte nur die Origin ohne Pfad, Query oder Fragment eingeben.");
    }
    return url.origin;
  }

  function validPairingCode(value) {
    return /^[A-Za-z0-9_-]{43,128}$/.test(value);
  }

  async function activePaybackTab() {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tab || !tab.id || !tab.url || !tab.url.startsWith("https://www.payback.de/")) {
      throw new Error("Bitte eine PAYBACK-Seite unter https://www.payback.de/ öffnen.");
    }
    return tab;
  }

  async function captureCurrentPage() {
    setBusy(true);
    setStatus("Sichtbare Daten werden lokal erfasst …");
    try {
      const tab = await activePaybackTab();
      const response = await chrome.tabs.sendMessage(tab.id, { type: "PAYBACK_CAPTURE_VISIBLE" });
      if (!response?.ok || !response.capture) throw new Error("Die Seite konnte nicht gelesen werden. Bitte PAYBACK neu laden und erneut versuchen.");
      state = mergeCapture(state, response.capture);
      await persist();
      render();
      const count = usefulRecordCount(response.capture.payload);
      setStatus(count ? `${count} Datensätze/Beobachtungen auf dieser Seite erkannt und kumuliert.` : "Keine bekannten Daten erkannt; Warnung wurde gespeichert.", !count);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Erfassung fehlgeschlagen.", true);
    } finally {
      setBusy(false);
    }
  }

  function requestOriginPermission(origin) {
    return chrome.permissions.request({ origins: [`${origin}/*`] });
  }

  async function sendImport() {
    updateSettingsFromForm();
    setBusy(true);
    try {
      const origin = normalizedOrigin(state.origin);
      if (!validPairingCode(state.pairing_code)) throw new Error("Der Einmalcode ist ungültig oder unvollständig.");
      if (!usefulRecordCount(state.payload)) throw new Error("Vor dem Import muss mindestens eine PAYBACK-Seite mit erkannten Daten erfasst werden.");
      const granted = await requestOriginPermission(origin);
      if (!granted) throw new Error("Die Hostberechtigung für diese HydraHive-Origin wurde nicht erteilt.");

      state.origin = origin;
      await persist();
      setStatus("Import wird sicher an HydraHive gesendet …");
      const body = { pairing_code: state.pairing_code, ...state.payload };
      const response = await fetch(`${origin}${IMPORT_PATH}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        cache: "no-store",
        credentials: "omit",
        redirect: "error",
        referrerPolicy: "no-referrer",
      });
      if (!response.ok) throw new Error("HydraHive hat den Import abgelehnt. Code, Ablaufzeit und Origin prüfen.");

      await chrome.permissions.remove({ origins: [`${origin}/*`] }).catch(() => false);
      await chrome.storage.session.remove(STATE_KEY);
      state = emptyState();
      render();
      setStatus("Import erfolgreich. Lokale Daten und Einmalcode wurden gelöscht.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Import fehlgeschlagen.", true);
    } finally {
      setBusy(false);
    }
  }

  async function clearLocalData() {
    clearTimeout(saveTimer);
    await chrome.storage.session.remove(STATE_KEY);
    state = emptyState();
    render();
    setStatus("Lokale Daten und Einmalcode wurden gelöscht.");
  }

  async function initialize() {
    try {
      const stored = await chrome.storage.session.get(STATE_KEY);
      const candidate = stored[STATE_KEY];
      const updatedAt = candidate?.updated_at ? Date.parse(candidate.updated_at) : 0;
      if (candidate?.payload && Array.isArray(candidate.pages) && Date.now() - updatedAt <= STATE_TTL_MS) {
        state = { ...emptyState(), ...candidate };
      } else if (candidate) {
        await chrome.storage.session.remove(STATE_KEY);
        setStatus("Abgelaufene lokale PAYBACK-Daten wurden automatisch gelöscht.");
      }
      render();
    } catch (_error) {
      setStatus("Lokaler Zustand konnte nicht geladen werden.", true);
    }
  }

  elements.origin.addEventListener("input", updateSettingsFromForm);
  elements.pairingCode.addEventListener("input", updateSettingsFromForm);
  elements.capture.addEventListener("click", captureCurrentPage);
  elements.send.addEventListener("click", sendImport);
  elements.clear.addEventListener("click", () => clearLocalData().catch(() => setStatus("Löschen fehlgeschlagen.", true)));
  initialize();
})();
