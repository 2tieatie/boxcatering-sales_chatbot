(function () {
    function isActive(path) {
        try {
            return window.location.pathname === path;
        } catch {
            return false;
        }
    }

    function renderNav(container) {
        if (!container) return;

        const links = {
            dashboard: { href: '/dashboard', label: (window.I18N && I18N.t) ? I18N.t('nav.dashboard') : 'Dashboard' },
            chatbotTest: { href: '/chatbot-test', label: (window.I18N && I18N.t) ? I18N.t('nav.chatbotTest') : 'Chatbot Test' },
        };

        const workingWithCustomers = [
            { href: '/conversation-history', label: (window.I18N && I18N.t) ? I18N.t('nav.conversations') : 'Conversations' },
            { href: '/customers', label: (window.I18N && I18N.t) ? I18N.t('nav.customers') : 'Customers' },
            { href: '/order-history', label: (window.I18N && I18N.t) ? I18N.t('nav.orders') : 'Orders' },
        ];

        const generalSettings = [
            { href: '/settings', label: (window.I18N && I18N.t) ? I18N.t('nav.settings') : 'Settings' },
            { href: '/chatbot-settings', label: (window.I18N && I18N.t) ? I18N.t('nav.chatbotSettings') : 'Chatbot Settings' },
            { href: '/user-management', label: (window.I18N && I18N.t) ? I18N.t('nav.users') : 'Users' },
        ];

        const nav = document.createElement('div');
        nav.className = 'nav-links';

        const dash = document.createElement('a');
        dash.href = links.dashboard.href;
        dash.className = 'nav-link' + (isActive(links.dashboard.href) ? ' active' : '');
        dash.textContent = links.dashboard.label;
        nav.appendChild(dash);

        const test = document.createElement('a');
        test.href = links.chatbotTest.href;
        test.className = 'nav-link' + (isActive(links.chatbotTest.href) ? ' active' : '');
        test.textContent = links.chatbotTest.label;
        nav.appendChild(test);

        function createDropdown(title, items) {
            const dd = document.createElement('div');
            dd.className = 'dropdown';

            const toggle = document.createElement('a');
            toggle.href = '#';
            toggle.className = 'nav-link dropdown-toggle';
            toggle.textContent = title;
            toggle.addEventListener('click', function (e) {
                e.preventDefault();
                dd.classList.toggle('open');
            });

            const menu = document.createElement('div');
            menu.className = 'dropdown-menu';

            items.forEach(item => {
                const a = document.createElement('a');
                a.href = item.href;
                const active = isActive(item.href);
                a.className = 'dropdown-item' + (active ? ' active' : '');
                a.textContent = item.label;
                menu.appendChild(a);
            });

            dd.appendChild(toggle);
            dd.appendChild(menu);
            return dd;
        }

        nav.appendChild(createDropdown('Working with Customers', workingWithCustomers));
        nav.appendChild(createDropdown('General Settings', generalSettings));

        // Replace existing nav or append if none
        container.innerHTML = '';
        container.appendChild(nav);
    }

    function ensureHeader() {
        const header = document.querySelector('.header');
        if (!header) return;

        // Ensure title exists
        let title = header.querySelector('h1');
        if (!title) {
            title = document.createElement('h1');
            title.textContent = (window.I18N && I18N.t) ? I18N.t('app.title') : 'Box Catering Chatbot';
            header.prepend(title);
        }

        // Nav container
        let navContainer = header.querySelector('.nav-links') || header.querySelector('#nav');
        if (!navContainer) {
            navContainer = document.createElement('div');
            header.insertBefore(navContainer, header.lastElementChild);
        }

        renderNav(navContainer);

        // Ensure user-info exists
        let userInfo = header.querySelector('.user-info');
        if (!userInfo) {
            userInfo = document.createElement('div');
            userInfo.className = 'user-info';
            const avatar = document.createElement('div');
            avatar.className = 'user-avatar';
            avatar.id = 'user-avatar';
            avatar.textContent = 'U';
            const name = document.createElement('span');
            name.id = 'username';
            name.textContent = (window.I18N && I18N.t) ? I18N.t('user.label') : 'User';
            const btn = document.createElement('button');
            btn.className = 'logout-btn';
            btn.textContent = (window.I18N && I18N.t) ? I18N.t('auth.logout') : 'Logout';
            btn.onclick = function () { try { localStorage.removeItem('access_token'); } catch { } window.location.href = '/login'; };
            userInfo.appendChild(avatar);
            userInfo.appendChild(name);
            userInfo.appendChild(btn);
            header.appendChild(userInfo);
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', ensureHeader);
    } else {
        ensureHeader();
    }
})();


