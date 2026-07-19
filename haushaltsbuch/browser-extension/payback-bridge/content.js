(() => {
  "use strict";

  const {
    LIMITS, cleanText, visibleText, rootsIncludingOpenShadowDom, selectVisible,
    parseDate, allDates, parseInteger, parsePoints, parseMoney, dataId, childText,
    partnerName, partnerRecord, dedupe,
  } = globalThis.PaybackBridgeContent;
  function extractBalance(roots, observedAt) {
    const candidates = selectVisible(roots, [
      "[data-testid*='balance' i]", "[data-testid*='point-balance' i]", "[data-test*='balance' i]",
      "[class*='point-balance' i]", "[class*='points-balance' i]", "[aria-label*='Punktestand' i]",
    ]);
    for (const element of candidates) {
      const points = parsePoints(visibleText(element));
      if (points !== null && points >= 0) return { observed_at: observedAt, available_points: points };
    }
    for (const root of roots) {
      const text = root === document ? visibleText(document.body, 100000) : visibleText(root.host, 100000);
      const match = text && text.match(/(?:Punktestand|verfügbare Punkte|Punktekonto)[^\d]{0,40}([\d.\s]+)\s*(?:°P|Punkte?n?)/i);
      const points = match && parseInteger(match[1]);
      if (points !== null && points >= 0) return { observed_at: observedAt, available_points: points };
    }
    return null;
  }

  function extractExpirations(roots) {
    const records = [];
    const candidates = selectVisible(roots, [
      "[data-testid*='expir' i]", "[data-test*='expir' i]", "[class*='expir' i]",
      "[class*='verfall' i]", "[aria-label*='verfall' i]",
    ]);
    for (const element of candidates) {
      const text = visibleText(element);
      if (!text || !/(verfall|verfallen|expire)/i.test(text)) continue;
      const expiration_date = parseDate(text);
      const pointsMatch = text.match(/([\d.\s]+)\s*(?:°P|Punkte?n?)/i);
      const points = pointsMatch && parseInteger(pointsMatch[1]);
      if (expiration_date && points && points > 0) records.push({ expiration_date, points, status: /bereits|abgelaufen/i.test(text) ? "expired" : "scheduled" });
    }
    return dedupe(records, item => `${item.expiration_date}:${item.points}:${item.status}`).slice(0, LIMITS.expirations);
  }

  function activityType(points, text) {
    if (/(storn|rückbuch|reversal)/i.test(text)) return "reversal";
    if (/(verfall|verfallen|expired)/i.test(text)) return "expire";
    if (/(einlös|eingelöst|redeem)/i.test(text)) return "redeem";
    return points > 0 ? "earn" : points < 0 ? "redeem" : "adjustment";
  }

  function extractActivities(roots) {
    const activities = [];
    const partners = [];
    const candidates = selectVisible(roots, [
      "[data-testid*='transaction' i]", "[data-testid*='activity' i]", "[data-test*='transaction' i]",
      "[class*='transaction-item' i]", "[class*='activity-item' i]", "li[class*='transaction' i]",
      "article[class*='transaction' i]", "[role='row'][class*='transaction' i]",
    ]);
    for (const element of candidates) {
      const text = visibleText(element, 4000);
      const activity_date = parseDate(text);
      const points_delta = parsePoints(text, true);
      if (!text || !activity_date || points_delta === null) continue;
      const partner = partnerRecord(partnerName(element, text));
      if (partner) partners.push(partner);
      const description = childText(element, ["[data-testid*='description' i]", "[class*='description' i]", "[class*='title' i]"], 2000) || text;
      const provider_activity_id = dataId(element, ["data-activity-id", "data-transaction-id", "data-id"], "activity", `${activity_date}|${points_delta}|${partner?.name || ""}|${description}`);
      const record = {
        provider_activity_id,
        activity_type: activityType(points_delta, text),
        activity_date,
        points_delta,
        original_description: cleanText(description, 2000),
      };
      if (partner) record.partner_provider_id = partner.provider_partner_id;
      const money = parseMoney(text);
      if (money) Object.assign(record, money);
      activities.push(record);
    }
    return {
      activities: dedupe(activities, item => item.provider_activity_id).slice(0, LIMITS.activities),
      partners,
    };
  }

  function couponStatus(text) {
    if (/(eingelöst|redeemed)/i.test(text)) return "redeemed";
    if (/(abgelaufen|expired)/i.test(text)) return "expired";
    if (/(aktiviert|active coupon)/i.test(text)) return "activated";
    if (/(nicht verfügbar|unavailable)/i.test(text)) return "unavailable";
    return "available";
  }

  function extractCoupons(roots, observedAt) {
    const coupons = [];
    const partners = [];
    const candidates = selectVisible(roots, [
      "[data-testid*='coupon' i]", "[data-test*='coupon' i]", "[data-coupon-id]",
      "article[class*='coupon' i]", "li[class*='coupon' i]", "[class*='coupon-card' i]",
      "[class*='coupon-tile' i]",
    ]);
    for (const element of candidates) {
      if ([...candidates].some(other => other !== element && other.contains(element))) continue;
      const text = visibleText(element, 8000);
      if (!text || !/(coupon|punkte|fach|°P|gültig)/i.test(text)) continue;
      const title = childText(element, ["[data-testid*='title' i]", "h1", "h2", "h3", "h4", "[class*='title' i]"], 500) || cleanText(text, 500);
      if (!title) continue;
      const partner = partnerRecord(partnerName(element, text));
      if (partner) partners.push(partner);
      const dates = allDates(text);
      const multiplierMatch = text.match(/(?:^|\s)(\d+(?:[,.]\d+)?)\s*(?:fach|x)\b/i);
      const bonusMatch = text.match(/(?:^|\s)(\d[\d.\s]*)\s*(?:Extra-|Bonus)?Punkte?n?\b/i);
      const condition = childText(element, ["[data-testid*='condition' i]", "[class*='condition' i]", "[class*='terms' i]", "small"], 4000);
      const record = {
        provider_coupon_id: dataId(element, ["data-coupon-id", "data-id", "id"], "coupon", `${partner?.name || ""}|${title}|${dates.join("|")}`),
        title,
        description: cleanText(text, 4000),
        activation_status: couponStatus(text),
        provider_updated_at: observedAt,
      };
      if (partner) record.partner_provider_id = partner.provider_partner_id;
      if (dates[0]) record.valid_from = dates.length > 1 ? dates[0] : undefined;
      if (dates[0]) record.valid_until = dates.length > 1 ? dates[dates.length - 1] : dates[0];
      if (multiplierMatch) record.multiplier = multiplierMatch[1].replace(",", ".");
      const bonus_points = bonusMatch && parseInteger(bonusMatch[1]);
      if (bonus_points !== null && bonus_points >= 0) record.bonus_points = bonus_points;
      if (condition) record.condition_text = condition;
      for (const key of Object.keys(record)) if (record[key] === undefined) delete record[key];
      coupons.push(record);
    }
    return {
      coupons: dedupe(coupons, item => item.provider_coupon_id).slice(0, LIMITS.coupons),
      partners,
    };
  }

  function captureVisiblePaybackData() {
    const observedAt = new Date().toISOString();
    const roots = rootsIncludingOpenShadowDom();
    const activityResult = extractActivities(roots);
    const couponResult = extractCoupons(roots, observedAt);
    const partners = dedupe([...activityResult.partners, ...couponResult.partners], item => item.provider_partner_id).slice(0, LIMITS.partners);
    const payload = {
      captured_at: observedAt,
      balance: extractBalance(roots, observedAt),
      expirations: extractExpirations(roots),
      partners,
      activities: activityResult.activities,
      coupons: couponResult.coupons,
    };
    const usefulCount = (payload.balance ? 1 : 0) + payload.expirations.length + payload.partners.length + payload.activities.length + payload.coupons.length;
    return {
      selector_version: SELECTOR_VERSION,
      page: { url: `${location.origin}${location.pathname}`, title: cleanText(document.title, 300), captured_at: observedAt },
      payload,
      warnings: usefulCount === 0 ? ["unknown_dom_version"] : [],
    };
  }

  chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
    if (!message || message.type !== "PAYBACK_CAPTURE_VISIBLE") return false;
    try {
      sendResponse({ ok: true, capture: captureVisiblePaybackData() });
    } catch (_error) {
      sendResponse({ ok: false, error: "capture_failed" });
    }
    return false;
  });
})();
