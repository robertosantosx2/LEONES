// search opens with Ctrl K, Cmd K or / from anywhere, and closes with Esc, the close
// button, a click outside the panel or the search button again (searcher.js does Esc)
(function () {
    var toggle = document.getElementById('search-toggle');
    var wrapper = document.getElementById('search-wrapper');
    var searchbar = document.getElementById('searchbar');
    var close = document.getElementById('search-close');
    if (!toggle || !wrapper || !searchbar) {
        return;
    }

    function isOpen() {
        return !wrapper.classList.contains('hidden');
    }

    function hide() {
        if (isOpen()) {
            toggle.click();
        }
    }

    if (/Mac|iPhone|iPad/.test(navigator.platform)) {
        toggle.querySelector('kbd').textContent = '⌘ K';
    }

    document.addEventListener('keydown', function (e) {
        var typing = /^(input|select|textarea)$/i.test(e.target.nodeName) || e.target.isContentEditable;
        var commandK = (e.ctrlKey || e.metaKey) && !e.altKey && e.key.toLowerCase() === 'k';
        var slash = e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && !typing;
        if (!commandK && !slash) {
            return;
        }
        e.preventDefault();
        if (isOpen()) {
            searchbar.focus();
            searchbar.select();
        } else {
            toggle.click();
        }
    });

    if (close) {
        close.addEventListener('click', hide);
    }

    document.addEventListener('click', function (e) {
        if (isOpen() && !wrapper.contains(e.target) && !toggle.contains(e.target)) {
            hide();
        }
    });
})();
