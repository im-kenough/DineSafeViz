// Nav dropdown (base.html): moved out of the page so the CSP can block inline scripts.
(function () {
    // <details> handles open/close and keyboard; close it on outside click or Escape.
    var dropdown = document.querySelector('details.dropdown');
    if (!dropdown) return;
    document.addEventListener('click', function (e) {
        if (!dropdown.contains(e.target)) dropdown.open = false;
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' && dropdown.open) {
            dropdown.open = false;
            dropdown.querySelector('summary').focus();
        }
    });
}());
