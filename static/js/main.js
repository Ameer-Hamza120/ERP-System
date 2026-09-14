(function () {
    'use strict';

    // Must be set before the browser performs default scroll restoration.
    if ('scrollRestoration' in window.history) {
        window.history.scrollRestoration = 'manual';
    }

    document.addEventListener('DOMContentLoaded', function () {
        // Auto-hide alerts after 5 seconds
        setTimeout(function() {
            document.querySelectorAll('.alert').forEach(function(alert) {
                alert.style.transition = 'opacity 0.5s';
                alert.style.opacity = '0';
                setTimeout(function() {
                    alert.remove();
                }, 500);
            });
        }, 5000);

        // Confirmation for delete forms
        document.querySelectorAll('form[data-confirm]').forEach(function (form) {
            form.addEventListener('submit', function (event) {
                const message = form.getAttribute('data-confirm') || 'Are you sure?';
                if (!confirm(message)) {
                    event.preventDefault();
                }
            });
        });

        // Mobile sidebar toggle
        const menuToggle = document.getElementById('menuToggle');
        const sidebar = document.getElementById('sidebar');
        const sidebarOverlay = document.getElementById('sidebarOverlay');
        const sidebarClose = document.getElementById('sidebarClose');

        if (menuToggle && sidebar && sidebarOverlay) {
            function openSidebar() {
                sidebar.classList.add('open');
                sidebarOverlay.classList.add('show');
                document.body.style.overflow = 'hidden';
            }

            function closeSidebar() {
                sidebar.classList.remove('open');
                sidebarOverlay.classList.remove('show');
                document.body.style.overflow = '';
            }

            menuToggle.addEventListener('click', openSidebar);

            if (sidebarClose) {
                sidebarClose.addEventListener('click', closeSidebar);
            }

            sidebarOverlay.addEventListener('click', closeSidebar);
        }
    });

    // ── Scroll preservation ──────────────────────────────────────────

    var PAGE_SCROLL_KEY = 'erpPageScrollPos';
    var SIDEBAR_SCROLL_KEY = 'erpSidebarScrollPos';

    function saveScroll() {
        var path = window.location.pathname || '/';
        if (path === '/login/' || path === '/logout/') return;

        try {
            sessionStorage.setItem(
                PAGE_SCROLL_KEY,
                String(window.scrollY || 0)
            );

            var sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sessionStorage.setItem(
                    SIDEBAR_SCROLL_KEY,
                    String(sidebar.scrollTop || 0)
                );
            }
        } catch (e) {
            // sessionStorage may be unavailable (private browsing, etc.)
        }
    }

    function restoreScroll() {
        try {
            var pagePos = sessionStorage.getItem(PAGE_SCROLL_KEY);
            if (pagePos !== null) {
                sessionStorage.removeItem(PAGE_SCROLL_KEY);

                var pageTarget = parseInt(pagePos, 10);
                if (!Number.isNaN(pageTarget) && pageTarget > 0) {
                    window.scrollTo(0, pageTarget);
                }
            }

            var sidebarPos = sessionStorage.getItem(SIDEBAR_SCROLL_KEY);
            if (sidebarPos === null) return;
            sessionStorage.removeItem(SIDEBAR_SCROLL_KEY);

            var sidebarTarget = parseInt(sidebarPos, 10);
            if (Number.isNaN(sidebarTarget) || sidebarTarget < 0) return;

            var attempts = 0;
            function restoreSidebar() {
                var sidebar = document.getElementById('sidebar');
                if (!sidebar) return;

                sidebar.scrollTop = sidebarTarget;
                attempts++;

                // Re-apply until the sidebar layout is ready.
                if (
                    Math.abs(sidebar.scrollTop - sidebarTarget) > 1 &&
                    attempts < 60
                ) {
                    requestAnimationFrame(restoreSidebar);
                }
            }
            restoreSidebar();
        } catch (e) {
            // sessionStorage may be unavailable (private browsing, etc.)
        }
    }

    // Save on any navigation away (anchors, form submissions, bfcache).
    window.addEventListener('pagehide', saveScroll);

    // Also save on anchor clicks, which fire before pagehide on some browsers.
    document.addEventListener('click', function (e) {
        var link = e.target.closest('a[href]');
        if (!link) return;
        var href = link.getAttribute('href') || '';
        if (href.startsWith('#') || /^https?:\/\//i.test(href) || href.startsWith('mailto:') || href.startsWith('tel:') || href.startsWith('javascript:')) return;
        saveScroll();
    });

    // Restore after the page is fully painted (pageshow fires after load).
    window.addEventListener('pageshow', function (e) {
        if (!e.persisted) {
            restoreScroll();
        }
    });
})();