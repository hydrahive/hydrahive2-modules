(() => {
  "use strict";

  const STATE_TTL_MS = 15 * 60 * 1000;
  const LIMITS = { expirations: 100, partners: 500, activities: 2000, coupons: 1000, pages: 30 };

  function emptyPayload() {
    return { captured_at: new Date().toISOString(), balance: null, expirations: [], partners: [], activities: [], coupons: [] };
  }

  function emptyState() {
    return {
      origin: "",
      pairing_code: "",
      payload: emptyPayload(),
      pages: [],
      warnings: [],
      updated_at: new Date().toISOString(),
    };
  }

  function dedupe(items, keyFunction, limit) {
    const byKey = new Map();
    for (const item of items) byKey.set(keyFunction(item), item);
    return [...byKey.values()].slice(-limit);
  }

  function mergeCapture(current, capture) {
    const incoming = capture.payload || emptyPayload();
    const payload = {
      captured_at: incoming.captured_at || new Date().toISOString(),
      balance: incoming.balance || current.payload.balance || null,
      expirations: dedupe([...current.payload.expirations, ...(incoming.expirations || [])], item => `${item.expiration_date}|${item.points}|${item.status}`, LIMITS.expirations),
      partners: dedupe([...current.payload.partners, ...(incoming.partners || [])], item => item.provider_partner_id, LIMITS.partners),
      activities: dedupe([...current.payload.activities, ...(incoming.activities || [])], item => item.provider_activity_id || `${item.activity_date}|${item.points_delta}|${item.partner_provider_id || ""}|${item.original_description || ""}`, LIMITS.activities),
      coupons: dedupe([...current.payload.coupons, ...(incoming.coupons || [])], item => item.provider_coupon_id || `${item.title}|${item.partner_provider_id || ""}|${item.valid_until || ""}`, LIMITS.coupons),
    };
    return {
      ...current,
      payload,
      pages: dedupe([...current.pages, capture.page], page => page.url, LIMITS.pages),
      warnings: dedupe([...current.warnings, ...(capture.warnings || [])], warning => warning, 20),
    };
  }

  function usefulRecordCount(payload) {
    return (payload.balance ? 1 : 0) + payload.expirations.length + payload.partners.length + payload.activities.length + payload.coupons.length;
  }

  globalThis.PaybackBridgeState = {
    STATE_TTL_MS, emptyState, mergeCapture, usefulRecordCount,
  };
})();
