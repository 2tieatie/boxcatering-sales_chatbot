(function () {
  function tOrFallback(key, fallback) {
    try {
      const i18n = window.I18N;
      if (i18n && typeof i18n.t === "function") {
        const txt = i18n.t(key);
        return txt && txt !== key ? txt : fallback;
      }
    } catch {}
    return fallback;
  }

  function isActive(path) {
    try {
      return window.location.pathname === path;
    } catch {
      return false;
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureHeader);
  } else {
    ensureHeader();
  }

  function renderNav(container) {
    if (!container) return;

    const links = {
      dashboard: {
        href: "/dashboard",
        key: "nav.dashboard",
        label: tOrFallback("nav.dashboard", "Dashboard"),
      },
      chatbotTest: {
        href: "/chatbot-test",
        key: "nav.chatbotTest",
        label: tOrFallback("nav.chatbotTest", "Chatbot Test"),
      },
    };

    const workingWithCustomers = [
      {
        href: "/conversation-history",
        key: "nav.conversations",
        label: tOrFallback("nav.conversations", "Conversations"),
      },
      {
        href: "/customers",
        key: "nav.customers",
        label: tOrFallback("nav.customers", "Customers"),
      },
      {
        href: "/order-history",
        key: "nav.orders",
        label: tOrFallback("nav.orders", "Orders"),
      },
      {
        href: "/assortment",
        key: "nav.assortment",
        label: tOrFallback("nav.assortment", "Assortment"),
      },
    ];

    const generalSettings = [
      {
        href: "/settings",
        key: "nav.settings",
        label: tOrFallback("nav.settings", "Settings"),
      },
      {
        href: "/chatbot-settings",
        key: "nav.chatbotSettings",
        label: tOrFallback("nav.chatbotSettings", "Chatbot Settings"),
      },
      {
        href: "/user-management",
        key: "nav.users",
        label: tOrFallback("nav.users", "Users"),
      },
    ];

    // Get current user role for access control
    let currentUserRole = null;
    try {
      const token = localStorage.getItem("access_token");
      if (token) {
        // Try to get role from a stored user info or make a quick API call
        const storedUserInfo = localStorage.getItem("user_info");
        if (storedUserInfo) {
          const userInfo = JSON.parse(storedUserInfo);
          currentUserRole = userInfo.role;
        }
      }
    } catch (e) {
      // Ignore errors, will fall back to showing all navigation
    }

    const nav = document.createElement("nav");
    nav.className = "nav-links";

    const dash = document.createElement("a");
    dash.href = links.dashboard.href;
    dash.className =
      "nav-link" + (isActive(links.dashboard.href) ? " active" : "");
    dash.setAttribute("data-i18n", links.dashboard.key);
    dash.textContent = tOrFallback(links.dashboard.key, links.dashboard.label);
    nav.appendChild(dash);

    const test = document.createElement("a");
    test.href = links.chatbotTest.href;
    test.className =
      "nav-link" + (isActive(links.chatbotTest.href) ? " active" : "");
    test.setAttribute("data-i18n", links.chatbotTest.key);
    test.textContent = tOrFallback(
      links.chatbotTest.key,
      links.chatbotTest.label,
    );
    nav.appendChild(test);

    function createDropdown(titleKey, fallbackTitle, items) {
      const dd = document.createElement("div");
      dd.className = "dropdown";

      const toggle = document.createElement("a");
      toggle.href = "#";
      toggle.className = "nav-link dropdown-toggle";
      if (titleKey) {
        toggle.setAttribute("data-i18n", titleKey);
        toggle.textContent = tOrFallback(
          titleKey,
          fallbackTitle || titleKey,
        );
      } else {
        toggle.textContent = fallbackTitle || "";
      }
      toggle.addEventListener("click", function (e) {
        e.preventDefault();
        dd.classList.toggle("open");
      });

      const menu = document.createElement("div");
      menu.className = "dropdown-menu";

      items.forEach((item) => {
        const a = document.createElement("a");
        a.href = item.href;
        const active = isActive(item.href);
        a.className = "dropdown-item" + (active ? " active" : "");
        if (item.key) {
          a.setAttribute("data-i18n", item.key);
          a.textContent = tOrFallback(item.key, item.label);
        } else {
          a.textContent = item.label;
        }
        menu.appendChild(a);
      });

      dd.appendChild(toggle);
      dd.appendChild(menu);
      return dd;
    }

    nav.appendChild(
      createDropdown(
        "nav.group.workingWithCustomers",
        "Working with Customers",
        workingWithCustomers,
      ),
    );

    // Only show General Settings dropdown for non-MANAGER users
    if (currentUserRole !== "manager") {
      nav.appendChild(
        createDropdown(
          "nav.group.generalSettings",
          "General Settings",
          generalSettings,
        ),
      );
    }

    // Replace existing nav or append if none
    container.innerHTML = "";
    container.appendChild(nav);
  }

  function ensureLangToggle(userInfoContainer) {
    if (!userInfoContainer) return;

    let langToggle = userInfoContainer.querySelector(".lang-toggle");
    if (!langToggle) {
      langToggle = document.createElement("div");
      langToggle.className = "lang-toggle";

      const uaBtn = document.createElement("button");
      uaBtn.type = "button";
      uaBtn.className = "lang-btn";
      uaBtn.textContent = "UA";
      uaBtn.title = "Українська";

      const enBtn = document.createElement("button");
      enBtn.type = "button";
      enBtn.className = "lang-btn";
      enBtn.textContent = "EN";
      enBtn.title = "English";

      async function switchTo(lang) {
        try {
          const i18n = window.I18N;
          if (i18n && typeof i18n.setLanguage === "function") {
            await i18n.setLanguage(lang);
          }
        } catch {}

        // Persist preference to backend when possible
        try {
          const token = localStorage.getItem("access_token");
          if (token) {
            const meRes = await fetch("/auth/me", {
              headers: { Authorization: `Bearer ${token}` },
            }).catch(() => null);

            if (meRes && meRes.ok) {
              const me = await meRes.json();
              await fetch(`/users/${me.id}`, {
                method: "PUT",
                headers: {
                  Authorization: `Bearer ${token}`,
                  "Content-Type": "application/json",
                },
                body: JSON.stringify({ preferred_language: lang }),
              }).catch(() => {});
            }
          }
        } catch {}

        updateActive();
      }

      uaBtn.addEventListener("click", function () {
        switchTo("uk");
      });

      enBtn.addEventListener("click", function () {
        switchTo("en");
      });

      langToggle.appendChild(uaBtn);
      langToggle.appendChild(enBtn);
      userInfoContainer.appendChild(langToggle);
    }

    function updateActive() {
      const i18n = window.I18N;
      const current = i18n && i18n.lang ? i18n.lang : "uk";
      const ua = langToggle.querySelector(".lang-btn:nth-child(1)");
      const en = langToggle.querySelector(".lang-btn:nth-child(2)");
      if (ua && en) {
        ua.classList.remove("active");
        en.classList.remove("active");
        if (current === "en") {
          en.classList.add("active");
        } else {
          ua.classList.add("active");
        }
      }
    }

    updateActive();
    try {
      document.addEventListener("i18n:languageChanged", function () {
        updateActive();
      });
    } catch {}
    try {
      if (window.__i18nReady && typeof window.__i18nReady.then === "function") {
        window.__i18nReady.then(function () {
          updateActive();
        });
      }
    } catch {}
  }

  function ensureHeader() {
    const header = document.querySelector(".header");
    if (!header) return;

    // Ensure title exists
    let title = header.querySelector("h1");
    if (!title) {
      title = document.createElement("h1");
      title.setAttribute("data-i18n", "app.title");
      title.textContent = tOrFallback("app.title", "Box Catering Chatbot");
      header.prepend(title);
    }

    // Nav container
    let navContainer =
      header.querySelector(".nav-links") || header.querySelector("#nav");
    if (!navContainer) {
      navContainer = document.createElement("div");
      header.insertBefore(navContainer, header.lastElementChild);
    }

    renderNav(navContainer);
    try {
      if (window.__i18nReady && typeof window.__i18nReady.then === "function") {
        window.__i18nReady.then(function () {
          renderNav(navContainer);
        });
      }
    } catch {}

    // User info block
    let userInfo = header.querySelector(".user-info");
    if (!userInfo) {
      userInfo = document.createElement("div");
      userInfo.className = "user-info";
      const avatar = document.createElement("div");
      avatar.className = "user-avatar";
      avatar.id = "user-avatar";
      avatar.textContent = "U";
      const name = document.createElement("span");
      name.id = "username";
      name.setAttribute("data-i18n", "user.label");
      name.textContent = tOrFallback("user.label", "User");
      const btn = document.createElement("button");
      btn.className = "logout-btn";
      btn.setAttribute("data-i18n", "auth.logout");
      btn.textContent = tOrFallback("auth.logout", "Logout");
      btn.onclick = function () {
        try {
          localStorage.removeItem("access_token");
        } catch {}
        window.location.href = "/login";
      };
      userInfo.appendChild(avatar);
      userInfo.appendChild(name);
      userInfo.appendChild(btn);
      header.appendChild(userInfo);
    }

    try {
      const targetUserInfo = header.querySelector(".user-info");
      if (targetUserInfo) {
        ensureLangToggle(targetUserInfo);
      }
    } catch {}

    // Populate current user name/avatar if authenticated
    try {
      const token = localStorage.getItem("access_token");
      if (!token) return;

      fetch("/auth/me", {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      })
        .then((res) => {
          if (!res.ok) throw new Error("Failed to load user info");
          return res.json();
        })
        .then((me) => {
          try {
            const avatarEl = document.getElementById("user-avatar");
            const nameEl = document.getElementById("username");
            if (avatarEl && me && me.email) {
              avatarEl.textContent = (me.email[0] || "U").toUpperCase();
            }
            if (nameEl && me && me.email) {
              nameEl.textContent = me.email;
            }
            localStorage.setItem("user_info", JSON.stringify(me));
          } catch (e) {
            // Ignore localStorage errors
          }
        })
        .catch(function () {
          /* ignore */
        });
    } catch {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", ensureHeader);
  } else {
    ensureHeader();
  }
})();
