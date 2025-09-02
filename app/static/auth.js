// Lightweight client-side auth helper: handles JWT expiry and 401/403 redirects
// - Auto-redirects to /login if token missing/expired
// - Schedules redirect exactly at token expiry
// - Wraps fetch to catch 401/403 and redirect

(function () {
    const LOGIN_PATH = '/login';
    const TOKEN_KEY = 'access_token';

    let expiryTimerId = null;

    function getToken() {
        try {
            return localStorage.getItem(TOKEN_KEY) || null;
        } catch {
            return null;
        }
    }

    function parseJwtExp(token) {
        try {
            const parts = token.split('.');
            if (parts.length !== 3) return null;
            const payload = JSON.parse(atob(parts[1]));
            const exp = payload && payload.exp;
            return (typeof exp === 'number') ? exp : null; // seconds since epoch
        } catch {
            return null;
        }
    }

    function redirectToLogin() {
        try { localStorage.removeItem(TOKEN_KEY); } catch { }
        if (window.location.pathname !== LOGIN_PATH) {
            window.location.href = LOGIN_PATH;
        }
    }

    function scheduleExpiryRedirect(token) {
        if (expiryTimerId) {
            clearTimeout(expiryTimerId);
            expiryTimerId = null;
        }
        const exp = parseJwtExp(token);
        if (!exp) return; // no exp -> do nothing
        const nowMs = Date.now();
        const expMs = exp * 1000;
        const delay = Math.max(0, expMs - nowMs);
        // Cap very long timeouts to avoid browser limits, refresh schedule if needed
        const MAX_DELAY = 0x7FFFFFFF; // ~24.8 days
        const schedule = (ms) => {
            expiryTimerId = setTimeout(() => {
                // On timer fire, re-check token/exp to avoid stale redirect
                const current = getToken();
                if (!current) return redirectToLogin();
                const currentExp = parseJwtExp(current);
                if (!currentExp) return redirectToLogin();
                const remaining = currentExp * 1000 - Date.now();
                if (remaining <= 0) {
                    redirectToLogin();
                } else {
                    schedule(remaining);
                }
            }, Math.min(ms, MAX_DELAY));
        };
        schedule(delay);
    }

    function ensureTokenValidOrRedirect() {
        const token = getToken();
        if (!token) {
            redirectToLogin();
            return null;
        }
        const exp = parseJwtExp(token);
        if (!exp || exp * 1000 <= Date.now()) {
            redirectToLogin();
            return null;
        }
        scheduleExpiryRedirect(token);
        return token;
    }

    // Wrap window.fetch once per page to catch 401/403
    (function wrapFetchOnce() {
        if (window.__authFetchWrapped) return;
        window.__authFetchWrapped = true;
        const originalFetch = window.fetch.bind(window);
        window.fetch = async function (input, init) {
            const response = await originalFetch(input, init);
            if (response && (response.status === 401 || response.status === 403)) {
                redirectToLogin();
            }
            return response;
        };
    })();

    // Public helpers
    window.Auth = {
        getToken,
        ensureTokenValidOrRedirect,
    };

    // Kick off on load except on the login page
    if (window.location.pathname !== LOGIN_PATH) {
        ensureTokenValidOrRedirect();
    }
})();


