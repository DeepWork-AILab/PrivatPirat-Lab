(() => {
  "use strict";

  const EXPECTED_HOST = "connect.deepwork-ailab.com";
  const PATH_RE = /^\/s\/[A-Za-z0-9_-]{16,256}$/;
  const PREFIX = "v1.";

  function normalizeSubscription(value) {
    let result = String(value || "").trim();
    if (result.startsWith("happ://add/")) result = result.slice("happ://add/".length);
    return result;
  }

  function validateSubscription(value) {
    const normalized = normalizeSubscription(value);
    let parsed;
    try {
      parsed = new URL(normalized);
    } catch {
      throw new Error("Ссылка не распознана.");
    }
    if (parsed.protocol !== "https:" || parsed.hostname !== EXPECTED_HOST) {
      throw new Error("Это не subscription PrivatPirat.");
    }
    if (parsed.username || parsed.password || parsed.port || parsed.search || parsed.hash || !PATH_RE.test(parsed.pathname)) {
      throw new Error("Формат subscription не прошёл проверку.");
    }
    return parsed.href;
  }

  function encodePayload(value) {
    const bytes = new TextEncoder().encode(validateSubscription(value));
    let binary = "";
    bytes.forEach((byte) => { binary += String.fromCharCode(byte); });
    return PREFIX + btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/u, "");
  }

  function decodePayload(value) {
    if (!String(value || "").startsWith(PREFIX)) throw new Error("Персональная часть ссылки отсутствует.");
    const body = String(value).slice(PREFIX.length).replace(/-/g, "+").replace(/_/g, "/");
    const padded = body + "=".repeat((4 - body.length % 4) % 4);
    let binary;
    try {
      binary = atob(padded);
    } catch {
      throw new Error("Персональная часть ссылки повреждена.");
    }
    const bytes = Uint8Array.from(binary, (character) => character.charCodeAt(0));
    return validateSubscription(new TextDecoder().decode(bytes));
  }

  function buildLandingUrl(baseUrl, subscription) {
    const base = new URL(baseUrl);
    base.hash = encodePayload(subscription);
    return base.href;
  }

  function showError(message) {
    const error = document.getElementById("error");
    error.textContent = message;
    error.hidden = false;
  }

  function showReady(subscription) {
    document.getElementById("setup").hidden = true;
    document.getElementById("error").hidden = true;
    document.getElementById("open-happ").href = `happ://add/${subscription}`;
    document.getElementById("ready").hidden = false;
  }

  function showSetup() {
    const setup = document.getElementById("setup");
    const input = document.getElementById("subscription");
    const generate = document.getElementById("generate");
    const generatedWrap = document.getElementById("generated-wrap");
    const generated = document.getElementById("generated");
    const copy = document.getElementById("copy");
    const testLink = document.getElementById("test-link");
    document.getElementById("ready").hidden = true;
    setup.hidden = false;

    if (setup.dataset.bound === "true") return;
    setup.dataset.bound = "true";

    generate.addEventListener("click", () => {
      document.getElementById("error").hidden = true;
      try {
        const cleanBase = new URL(window.location.href);
        cleanBase.hash = "";
        cleanBase.search = "";
        const landing = buildLandingUrl(cleanBase.href, input.value);
        generated.value = landing;
        testLink.href = landing;
        generatedWrap.hidden = false;
      } catch (error) {
        generatedWrap.hidden = true;
        showError(error instanceof Error ? error.message : "Не удалось создать ссылку.");
      }
    });

    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(generated.value);
        copy.textContent = "Скопировано";
      } catch {
        generated.focus();
        generated.select();
        showError("Автокопирование недоступно — ссылка выделена.");
      }
    });

    testLink.addEventListener("click", (event) => {
      event.preventDefault();
      try {
        const target = new URL(testLink.href);
        window.history.replaceState(null, "", target.href);
        renderFromLocation();
      } catch {
        showError("Не удалось открыть готовую Landing-ссылку.");
      }
    });
  }

  function renderFromLocation() {
    document.getElementById("ready").hidden = true;
    document.getElementById("setup").hidden = true;
    document.getElementById("error").hidden = true;
    const payload = window.location.hash.slice(1);
    if (!payload) {
      showSetup();
      return;
    }
    try {
      showReady(decodePayload(payload));
    } catch (error) {
      showError(error instanceof Error ? error.message : "Персональная ссылка повреждена.");
    }
  }

  function init() {
    renderFromLocation();
    window.addEventListener("hashchange", renderFromLocation);
  }

  const api = { normalizeSubscription, validateSubscription, encodePayload, decodePayload, buildLandingUrl };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (typeof document !== "undefined") document.addEventListener("DOMContentLoaded", init);
})();
