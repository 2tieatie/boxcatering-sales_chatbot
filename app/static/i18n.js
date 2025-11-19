(function () {
  const DEFAULT_LANG = "uk";
  let currentLang = null;
  let dict = {};

  const scriptTag = Array.from(document.getElementsByTagName("script")).find(
    (s) => s.src.includes("i18n.js"),
  );
  const srcLink = scriptTag.getAttribute("src");
  const homeLink = srcLink.includes("http")
    ? srcLink.split("//")[0] + "//" + srcLink.split("//")[1].split("/")[0]
    : "";
  // console.log(homeLink);

  function normalizeLang(lang) {
    if (!lang) return DEFAULT_LANG;
    const l = String(lang).toLowerCase();
    if (l === "ua" || l.startsWith("ua-")) return "uk";
    if (l === "uk-ua") return "uk";
    return l.slice(0, 2);
  }

  function detectLanguage() {
    try {
      const stored = localStorage.getItem("ui_language");
      if (stored) return normalizeLang(stored);
    } catch {}
    try {
      const navLang =
        navigator.language || navigator.userLanguage || DEFAULT_LANG;
      return normalizeLang(navLang);
    } catch {}
    return DEFAULT_LANG;
  }

  async function load(lang) {
    const target = normalizeLang(lang) || detectLanguage();
    currentLang = target;
    try {
      const res = await fetch(homeLink + `/static/locales/${target}.json`, {
        cache: "no-store",
      });
      dict = res.ok ? await res.json() : {};
    } catch {
      dict = {};
    }
    translatePage();
    try {
      const evt = new CustomEvent("i18n:languageChanged", {
        detail: { lang: currentLang },
      });
      document.dispatchEvent(evt);
    } catch {}
  }

  function t(key, vars) {
    let txt = (dict && dict[key]) || key;
    if (vars && typeof vars === "object") {
      for (const k in vars) {
        if (Object.prototype.hasOwnProperty.call(vars, k)) {
          txt = txt.replace(new RegExp(`{${k}}`, "g"), String(vars[k]));
        }
      }
    }
    return txt;
  }

  function translatePage() {
    try {
      document.querySelectorAll("[data-i18n]").forEach(function (el) {
        const key = el.getAttribute("data-i18n");
        el.textContent = t(key);
      });
    } catch {}
  }

  async function setLanguage(lang) {
    const canon = normalizeLang(lang);
    try {
      localStorage.setItem("ui_language", canon);
    } catch {}
    await load(canon);
  }

  if (!window.I18N || !window.I18N.setLanguage) {
    window.I18N = {
      t,
      load,
      setLanguage,
      get lang() {
        return currentLang || DEFAULT_LANG;
      },
    };
    // Fire and forget default load
    load().catch(() => {});
  }
})();
