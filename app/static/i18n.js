(function () {
    const DEFAULT_LANG = 'uk';
    let currentLang = null;
    let dict = {};

    function detectLanguage() {
        try {
            const stored = localStorage.getItem('ui_language');
            if (stored) return stored;
        } catch { }
        try {
            const navLang = (navigator.language || navigator.userLanguage || DEFAULT_LANG).slice(0, 2);
            return navLang;
        } catch { }
        return DEFAULT_LANG;
    }

    async function load(lang) {
        const target = lang || detectLanguage();
        currentLang = target;
        try {
            const res = await fetch(`/static/locales/${target}.json`, { cache: 'no-store' });
            dict = res.ok ? await res.json() : {};
        } catch {
            dict = {};
        }
        translatePage();
    }

    function t(key, vars) {
        let txt = (dict && dict[key]) || key;
        if (vars && typeof vars === 'object') {
            for (const k in vars) {
                if (Object.prototype.hasOwnProperty.call(vars, k)) {
                    txt = txt.replace(new RegExp(`{${k}}`, 'g'), String(vars[k]));
                }
            }
        }
        return txt;
    }

    function translatePage() {
        try {
            document.querySelectorAll('[data-i18n]').forEach(function (el) {
                const key = el.getAttribute('data-i18n');
                el.textContent = t(key);
            });
        } catch { }
    }

    async function setLanguage(lang) {
        try { localStorage.setItem('ui_language', lang); } catch { }
        await load(lang);
    }

    if (!window.I18N) {
        window.I18N = { t, load, setLanguage, get lang() { return currentLang || DEFAULT_LANG; } };
        // Fire and forget default load
        load().catch(() => { });
    }
})();


