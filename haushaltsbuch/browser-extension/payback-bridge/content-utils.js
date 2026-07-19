(() => {
  "use strict";

  const SELECTOR_VERSION = "payback-visible-v1";
  const LIMITS = { activities: 2000, coupons: 1000, expirations: 100, partners: 500 };
  const MONTHS = {
    januar: 1, februar: 2, maerz: 3, märz: 3, april: 4, mai: 5, juni: 6,
    juli: 7, august: 8, september: 9, oktober: 10, november: 11, dezember: 12,
  };

  function cleanText(value, maxLength = 4000) {
    const text = String(value || "").replace(/\s+/g, " ").trim();
    return text ? text.slice(0, maxLength) : null;
  }

  function visible(element) {
    if (!(element instanceof Element)) return false;
    let current = element;
    while (current instanceof Element) {
      const style = getComputedStyle(current);
      if (style.display === "none" || style.visibility === "hidden" || Number(style.opacity) === 0) return false;
      const root = current.getRootNode();
      current = current.parentElement || (root instanceof ShadowRoot ? root.host : null);
    }
    const rect = element.getBoundingClientRect();
    return rect.width > 0 && rect.height > 0;
  }

  function visibleText(element, maxLength = 4000) {
    return visible(element) ? cleanText(element.innerText || element.textContent, maxLength) : null;
  }

  function rootsIncludingOpenShadowDom() {
    const roots = [document];
    for (let index = 0; index < roots.length; index += 1) {
      const root = roots[index];
      for (const element of root.querySelectorAll("*")) {
        if (element.shadowRoot) roots.push(element.shadowRoot);
      }
    }
    return roots;
  }

  function selectVisible(roots, selectors) {
    const found = new Set();
    for (const root of roots) {
      for (const selector of selectors) {
        for (const element of root.querySelectorAll(selector)) {
          if (visible(element)) found.add(element);
        }
      }
    }
    return [...found];
  }

  function pad(number) {
    return String(number).padStart(2, "0");
  }

  function validIsoDate(year, month, day) {
    const date = new Date(Date.UTC(year, month - 1, day));
    if (date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day) return null;
    return `${year}-${pad(month)}-${pad(day)}`;
  }

  function parseDate(value) {
    const text = cleanText(value, 200);
    if (!text) return null;
    let match = text.match(/\b(20\d{2})-(\d{1,2})-(\d{1,2})\b/);
    if (match) return validIsoDate(Number(match[1]), Number(match[2]), Number(match[3]));
    match = text.match(/\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b/);
    if (match) {
      let year = Number(match[3]);
      if (year < 100) year += 2000;
      return validIsoDate(year, Number(match[2]), Number(match[1]));
    }
    match = text.toLocaleLowerCase("de-DE").match(/\b(\d{1,2})\.?\s+(januar|februar|märz|maerz|april|mai|juni|juli|august|september|oktober|november|dezember)\s+(20\d{2})\b/);
    return match ? validIsoDate(Number(match[3]), MONTHS[match[2]], Number(match[1])) : null;
  }

  function allDates(value) {
    const text = cleanText(value, 4000) || "";
    const matches = text.match(/(?:\b20\d{2}-\d{1,2}-\d{1,2}\b)|(?:\b\d{1,2}[./-]\d{1,2}[./-]\d{2,4}\b)|(?:\b\d{1,2}\.?\s+(?:Januar|Februar|März|Maerz|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)\s+20\d{2}\b)/gi) || [];
    return matches.map(parseDate).filter(Boolean);
  }

  function parseInteger(raw) {
    if (!raw) return null;
    const normalized = raw.replace(/[.\s\u00a0]/g, "");
    const number = Number.parseInt(normalized, 10);
    return Number.isSafeInteger(number) ? number : null;
  }

  function parsePoints(value, requireSign = false) {
    const text = cleanText(value, 4000) || "";
    const patterns = requireSign
      ? [/(?:^|\s)([+-]\s*[\d.\s]+)\s*(?:°P|Punkte?n?|P)(?:\s|$)/i]
      : [/(?:Punktestand|Punkte(?:stand|konto)?|verfügbar(?:e Punkte)?)[^\d]{0,30}([\d.\s]+)\s*(?:°P|Punkte?n?|P)?/i, /([\d.\s]+)\s*(?:°P|Punkte?n?)\b/i];
    for (const pattern of patterns) {
      const match = text.match(pattern);
      if (!match) continue;
      const sign = match[1].includes("-") ? -1 : 1;
      const parsed = parseInteger(match[1].replace(/[+-]/g, ""));
      if (parsed !== null) return parsed * sign;
    }
    return null;
  }

  function parseMoney(value) {
    const text = cleanText(value, 4000) || "";
    const pattern = /(?:(?:€|EUR)\s*(\d{1,9}(?:[.\s]\d{3})*(?:,\d{2})|\d{1,9}[.,]\d{2})|(\d{1,9}(?:[.\s]\d{3})*(?:,\d{2})|\d{1,9}[.,]\d{2})\s*(?:€|EUR)(?!\w))/gi;
    const matches = [...text.matchAll(pattern)];
    if (matches.length !== 1) return null;
    const raw = matches[0][1] || matches[0][2];
    let amount = raw.replace(/[\s.]/g, "").replace(",", ".");
    if (!raw.includes(",") && raw.match(/\.\d{2}$/)) amount = raw;
    const minor = Math.round(Number(amount) * 100);
    return Number.isSafeInteger(minor) && minor >= 0 ? { purchase_amount_minor: minor, purchase_currency: "EUR" } : null;
  }

  function stableHash(value) {
    let hash = 2166136261;
    for (const character of value) {
      hash ^= character.codePointAt(0);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0).toString(36);
  }

  function safeProviderId(value, prefix) {
    const text = cleanText(value, 256);
    if (text && /^[A-Za-z0-9._:-]+$/.test(text)) return text;
    return `${prefix}:${stableHash(text || prefix)}`;
  }

  function dataId(element, names, prefix, fallback) {
    for (const name of names) {
      const value = element.getAttribute(name);
      if (value) return safeProviderId(value, prefix);
    }
    return safeProviderId(fallback, prefix);
  }

  function childText(element, selectors, maxLength = 500) {
    for (const selector of selectors) {
      const child = element.querySelector(selector);
      const text = child && visibleText(child, maxLength);
      if (text) return text;
    }
    return null;
  }

  function partnerName(element, fullText) {
    return childText(element, [
      "[data-testid*='partner' i]", "[class*='partner' i]", "[data-partner-name]",
      "[class*='merchant' i]", "[class*='company' i]", "img[alt]",
    ], 240) || cleanText(element.getAttribute("data-partner-name"), 240) || (() => {
      const match = fullText.match(/(?:bei|von|Partner)\s+([\p{L}\d&'. -]{2,80}?)(?=\s+[+-]?\d|\s+am\s+|$)/iu);
      return match ? cleanText(match[1], 240) : null;
    })();
  }

  function partnerRecord(name) {
    if (!name) return null;
    return { provider_partner_id: safeProviderId(name.toLocaleLowerCase("de-DE"), "partner"), name, active: true };
  }

  function dedupe(items, keyFunction) {
    const byKey = new Map();
    for (const item of items) byKey.set(keyFunction(item), item);
    return [...byKey.values()];
  }

  function leafCandidates(candidates) {
    return candidates.filter(candidate => !candidates.some(other => (
      other !== candidate && candidate.contains(other)
    )));
  }

  globalThis.PaybackBridgeContent = {
    SELECTOR_VERSION, LIMITS, cleanText, visible, visibleText,
    rootsIncludingOpenShadowDom, selectVisible,
    parseDate, allDates, parseInteger, parsePoints, parseMoney, dataId, childText,
    partnerName, partnerRecord, dedupe, leafCandidates,
  };
})();
