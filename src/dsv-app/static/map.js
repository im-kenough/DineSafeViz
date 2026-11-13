// Builds the Leaflet map from the #map-data JSON block (templates/_map.html).
// Search: every pin, opening on all of Toronto; a pin's popup is its result
// card. Restaurant page (data-single): one pin at zoom 16, no popup.
(function () {
    'use strict';
    var box = document.getElementById('map');
    var data = document.getElementById('map-data');
    if (!box || !data || !window.L) return;
    var pins = JSON.parse(data.textContent);
    if (!pins.length) return;

    var TORONTO = [[43.58, -79.64], [43.86, -79.11]];
    // Pin colours are the card-border colours from style.css.
    var css = getComputedStyle(document.documentElement);
    var colours = {
        'status-closed': css.getPropertyValue('--dinesafe-red').trim(),
        'status-conditional': css.getPropertyValue('--dinesafe-yellow').trim(),
        'status-pass': css.getPropertyValue('--dinesafe-green').trim()
    };
    var single = box.hasAttribute('data-single');

    function el(tag, className, text) {
        var node = document.createElement(tag);
        if (className) node.className = className;
        if (text) node.textContent = text;
        return node;
    }

    // The popup: a compact search result card linking to the restaurant page.
    function card(p) {
        var a = el('a', 'result-card map-popup ' + p.cls);
        a.href = p.url;
        var place = el('span', 'result-place');
        place.appendChild(el('strong', '', p.name));
        place.appendChild(el('span', '', p.addr));
        var latest = el('span', 'result-latest');
        latest.appendChild(el('strong', 'status-badge', (p.status || '').toUpperCase()));
        latest.appendChild(el('span', '', 'Last inspected ' + p.last));
        a.appendChild(place);
        a.appendChild(latest);
        return a;
    }

    // Unhide first so Leaflet can measure the container.
    box.hidden = false;
    var map = L.map(box, { preferCanvas: true });
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        referrerPolicy: 'strict-origin-when-cross-origin',
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);

    pins.forEach(function (p) {
        var marker = L.circleMarker([p.lat, p.lng], {
            radius: 7,
            weight: 2,
            color: '#0e1016',
            fillColor: colours[p.cls] || '#83899d',
            fillOpacity: 0.9
        }).addTo(map);
        // Auto-pan keeps an opened popup clear of the 44px zoom buttons (style.css).
        if (!single) marker.bindPopup(function () { return card(p); }, { autoPanPaddingTopLeft: [60, 10] });
    });

    if (single) map.setView([pins[0].lat, pins[0].lng], 16);
    else map.fitBounds(TORONTO);
}());
