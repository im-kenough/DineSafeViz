// Quarter page timeline and lazy-loaded months (index.html). A file, not an
// inline script, so the CSP can block inline scripts.
(function () {
    var months = document.querySelectorAll('details.month-box');
    // Month the user just jumped to; re-scrolled to once its content loads,
    // since the browser jumps before the page is tall enough to reach it.
    var pendingJump = null;
    ['wheel', 'touchstart', 'keydown'].forEach(function (type) {
        window.addEventListener(type, function () { pendingJump = null; }, { passive: true });
    });

    // Fetch a collapsed month's day boxes the first time it is opened.
    months.forEach(function (box) {
        box.addEventListener('toggle', function () {
            var src = box.dataset.src;
            if (!box.open || !src) return;
            delete box.dataset.src;
            var body = box.querySelector('.month-body');
            fetch(src).then(function (resp) {
                if (!resp.ok) throw new Error(resp.status);
                return resp.text();
            }).then(function (html) {
                body.innerHTML = html;
                if (pendingJump === box) {
                    pendingJump = null;
                    box.scrollIntoView();
                }
            }).catch(function () {
                box.dataset.src = src;
                body.innerHTML = '<p class="no-data">Could not load. <a href="' + src + '">Open this month</a></p>';
            });
        });
    });

    // Timeline month links open their month before the browser jumps to it.
    var links = document.querySelectorAll('.month-link');
    links.forEach(function (link) {
        link.addEventListener('click', function () {
            var box = document.querySelector(link.getAttribute('href'));
            if (box.dataset.src) pendingJump = box;
            box.open = true;
        });
    });

    // One toggle: expands all unless every month is already open.
    var toggle = document.getElementById('toggle-all');
    var toggleLabel = toggle.querySelector('.long');
    var toggleIcon = toggle.querySelector('.toggle-icon');
    function allOpen() {
        return Array.prototype.every.call(months, function (box) { return box.open; });
    }
    function syncToggle() {
        var open = allOpen();
        var label = open ? 'Collapse all' : 'Expand all';
        toggle.setAttribute('aria-label', label);
        toggleLabel.textContent = label;
        toggleIcon.textContent = open ? '⊟' : '⊞';
    }
    toggle.addEventListener('click', function () {
        var open = !allOpen();
        months.forEach(function (box) { box.open = open; });
    });
    months.forEach(function (box) { box.addEventListener('toggle', syncToggle); });

    // Highlight the month currently under the sticky bar. The line matches
    // the month's scroll-margin-top, where timeline jumps land.
    var ticking = false;
    var edge = parseFloat(getComputedStyle(months[0]).scrollMarginTop) + 1;
    function markCurrent() {
        ticking = false;
        var current = months[0];
        months.forEach(function (box) {
            if (box.getBoundingClientRect().top <= edge) current = box;
        });
        links.forEach(function (link) {
            var on = link.getAttribute('href') === '#' + current.id;
            link.classList.toggle('current', on);
            if (on) link.setAttribute('aria-current', 'location');
            else link.removeAttribute('aria-current');
        });
    }
    window.addEventListener('scroll', function () {
        if (!ticking) { ticking = true; requestAnimationFrame(markCurrent); }
    }, { passive: true });
    markCurrent();
}());
