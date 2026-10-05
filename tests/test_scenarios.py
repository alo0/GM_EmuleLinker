"""Level 2: scenarios on the served pages, with real keyboard shortcuts and caught alerts.

The references in the comments (SF-x, A-x) point to SPECIFICATIONS.md. The sending
itself is tested in test_sending.py, against fake ed2k clients.
"""

# Settings for the remote eMule method: its URLs show the category that is sent
EMULE = {'ed2kDlMethod': 'emule', 'emuleUrl': 'http://127.0.0.1:4711/',
         'emulePwd': 'secret', 'emuleCat': '*default=0;'}

NAMES = {'example1.mp3', 'example2.avi', 'Documentary Planet Earth 4K.mp4',
         'Été à Paris (Café).mp3', 'Conférence Téléphonique (v2.0).mkv',
         'François & Marie [Résumé].docx', 'Ópera Española (Colección).flac',
         'Bücher über Geräte (édition).pdf', 'Guide Réseau été 2024.pdf'}

ROWS = "document.querySelectorAll('#divBody a.ed2k').length"
SELECTED_CAT = ("(function(){var s=document.getElementById('cat');"
                "return [s.options[s.selectedIndex].text, s.value]})()")
SENT_CATS = ("[].map.call(document.querySelectorAll('#divBody a.ed2k'), function (a) {"
             "var m = a.getAttribute('href').match(/[?&]cat=([^&]*)/); return m ? m[1] : null; })")


def with_emule(**changes):
    return dict(EMULE, **changes)


def test_detection(t):
    """SF-1: the 9 valid links of test_sample.html, the 2 invalid ones ignored."""
    t.load(settings=EMULE)
    t.eq(t.dialogs, [], 'no alert')
    t.eq(t.js('eLinks.length'), 9, 'links detected')
    t.eq(set(t.js('eFiles')), NAMES, 'file names, decoded')
    t.eq(t.js(ROWS), 9, 'rows in the popup')
    t.check(t.traced('ignoring malformed ed2k link: ed2k://xxxxxxxx'), 'malformed link ignored (A-1)')
    t.check(t.traced('ignoring malformed ed2k link: ed2k://|server|'), 'server link ignored')


def test_no_link_page(t):
    """SF-1.12: no popup without ed2k links; a relative link "ed2k-guide.html" is not one."""
    t.load('__nolinks', settings=EMULE)
    t.eq(t.js('eLinks.length'), 0, 'no link detected')
    t.eq(t.js("!!document.getElementById('theDiv')"), False, 'no popup')


def test_first_run_opens_settings(t):
    """SF-8.2: on the very first run the settings dialog opens by itself."""
    t.load(emule_config=None)
    t.check(t.settings_open(), 'settings dialog open')
    t.eq(t.gm('emule_config'), 1, 'first run recorded')


def test_shortcut_settings(t):
    """SF-9: Ctrl+Alt+S opens the settings dialog."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened by the shortcut')
    t.close_settings()
    t.check(not t.settings_open(), 'settings dialog closed')


def test_category_empty(t):
    """A-4: an empty Category setting raises one alert, no longer stops the script,
    and the corrected value is stored so that the alert does not come back (SF-8.7)."""
    t.load(settings=with_emule(emuleCat=''))
    t.eq(len(t.dialogs), 1, 'one alert')
    t.check(t.dialogs and 'Category value invalid' in t.dialogs[0], 'it is the category alert', t.dialogs)
    t.check(t.traced('no valid category found'), 'trace of strToCat()')
    t.eq(t.js(ROWS), 9, 'the popup is displayed')
    t.check(t.open_settings(), 'the shortcuts are installed')
    t.close_settings()
    t.eq(t.stored_settings().get('emuleCat'), '*default=0', 'corrected value stored')
    t.dialogs.clear()
    t.reload()
    t.eq(t.dialogs, [], 'no alert on the next page load')


def test_category_without_default(t):
    """SF-6.7: without any *, the first category is the default, displayed and sent."""
    t.load(settings=with_emule(emuleCat='Audio=1;Video=2'))
    t.eq(t.js(SELECTED_CAT), ['Audio', '1'], 'drop-down list on Audio')
    t.eq(set(t.js(SENT_CATS)), {'1'}, 'category sent: Audio')


def test_category_two_defaults(t):
    """SF-6.7: with two *, only the first one is the default."""
    t.load(settings=with_emule(emuleCat='*Audio=1;*Video=2'))
    t.eq(t.js(SELECTED_CAT), ['Audio', '1'], 'drop-down list on Audio')
    t.eq(set(t.js(SENT_CATS)), {'1'}, 'category sent: Audio')


def test_settings_dialog_save(t):
    """SF-8: a value typed in the settings dialog is saved and applied after the reload."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.set_field('emuleCat', 'Video=2;*Audio=1')
    t.save_settings()
    t.eq(t.dialogs, [], 'no alert')
    t.eq(t.stored_settings().get('emuleCat'), 'Video=2;*Audio=1', 'value stored')
    t.eq(t.js(SELECTED_CAT), ['Audio', '1'], 'drop-down list on Audio')


def test_edit_mode(t):
    """SF-4 and SF-5.4: Ctrl+Alt+M shows the links in a text area and back."""
    t.load(settings=EMULE)
    t.keys('m')
    lines = t.js("(function(){var e=document.getElementById('editbox');return e ? e.value.split('\\n') : null})()")
    t.check(lines is not None, 'text area displayed')
    t.eq(len(lines or []), 9, 'one link per line')
    t.eq(t.js("document.getElementById('checkall').disabled"), True, '"check all" disabled')
    t.keys('m')
    t.eq(t.js(ROWS), 9, 'back to the list')
    t.eq(t.js("document.getElementById('checkall').disabled"), False, '"check all" enabled again')


def test_local_method(t):
    """SF-7.7 and SF-7.8 (A-6, A-13): local method, links encoded and every one clicked."""
    t.load(settings={'ed2kDlMethod': 'local'})
    hrefs = t.js("[].map.call(document.querySelectorAll('#divBody a.ed2k'), function (a) "
                 "{ return a.getAttribute('href'); })")
    t.eq(len(hrefs), 9, 'popup links')
    t.check(all(h.startswith('ed2k://%7Cfile%7C') for h in hrefs), 'popup links encoded', hrefs[:1])
    t.check(not any(c in h for h in hrefs for c in '| []#?'), 'no forbidden character left')
    t.eq(t.js("document.getElementById('cat').disabled"), True, 'category list disabled')
    t.catch_anchor_clicks()
    t.keys('a')
    clicked = t.clicked()
    t.eq(len(clicked), 9, 'one click per link')
    t.check(all(h.startswith('ed2k://%7Cfile%7C') for h in clicked), 'clicked links encoded')


def test_url_without_slash_stored(t):
    """SF-8.7: the URL completed with its final / is stored."""
    t.load(settings=with_emule(emuleUrl='http://127.0.0.1:4711'))
    t.eq(t.stored_settings().get('emuleUrl'), 'http://127.0.0.1:4711/', 'corrected URL stored')


def test_empty_password_accepted(t):
    """A-9: the eMule password is optional, eMule accepts a web interface without one:
    no alert, no settings dialog, and the settings are read once (no recursion)."""
    t.load(settings=with_emule(emulePwd=''))
    t.eq(t.dialogs, [], 'no alert')
    t.check(not t.settings_open(), 'settings dialog not opened')
    t.eq(sum('saveConfig() storing the settings' in c for c in t.console), 1, 'settings read once')
    t.eq(t.stored_settings().get('emulePwd'), '', 'empty password kept')


def test_empty_password_with_another_fix(t):
    """SF-8.7: storing a corrected setting leaves the other ones, an empty password included, as they were."""
    t.load(settings=with_emule(emulePwd='', emuleUrl='http://127.0.0.1:4711'))
    t.eq(t.stored_settings().get('emuleUrl'), 'http://127.0.0.1:4711/', 'corrected URL stored')
    t.eq(t.stored_settings().get('emulePwd'), '', 'empty password kept')


def test_default_password_empty(t):
    """A-9: with nothing stored (a new installation), the password is empty, not "something"."""
    t.load()
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_field_emulePwd').value"), '', 'empty password by default')


# ---- opening and closing the popup (A-5) ----------------------------------------------
# [popups displayed, rows of the list, edit boxes]
POPUP = ("[document.querySelectorAll('#theDiv').length,"
         " document.querySelectorAll('#divBody a.ed2k').length,"
         " document.querySelectorAll('#editbox').length]")


def test_open_when_already_open(t):
    """SF-2.8 (A-5): Ctrl+Alt+O on an open popup does not add a second one."""
    t.load(settings=EMULE)
    t.keys('o')
    t.eq(t.js(POPUP), [1, 9, 0], 'one popup, one list')
    t.eq(t.errors, [], 'no JavaScript error')


def test_open_keeps_edit_mode(t):
    """SF-2.8 (A-5): Ctrl+Alt+O in edit mode leaves the edit box as it is."""
    t.load(settings=EMULE, popup_mode=2)
    t.keys('o')
    t.eq(t.js(POPUP), [1, 0, 1], 'one popup, still in edit mode')
    t.eq(t.gm('popup_mode'), 2, 'edit mode still stored')


def test_closed_popup_stays_closed(t):
    """SF-10.2: a popup closed on a page is not displayed on the next page with ed2k links."""
    t.load(settings=EMULE, popup_mode=0)
    t.eq(t.js(POPUP), [0, 0, 0], 'no popup, not even its toolbars')
    t.keys('o')
    t.eq(t.js(POPUP), [1, 9, 0], 'Ctrl+Alt+O opens it with its list')
    t.eq(t.gm('popup_mode'), 1, 'open state stored')


def test_close_then_open(t):
    """SF-9: Ctrl+Alt+C closes the popup, Ctrl+Alt+O opens it again, once."""
    t.load(settings=EMULE)
    t.keys('c')
    t.eq(t.js(POPUP), [0, 0, 0], 'closed')
    t.eq(t.gm('popup_mode'), 0, 'closed state stored')
    t.keys('o')
    t.keys('o')
    t.eq(t.js(POPUP), [1, 9, 0], 'opened once, even with two Ctrl+Alt+O')
    t.eq(t.errors, [], 'no JavaScript error')


def test_toggle_with_ctrl_alt_x(t):
    """SF-9: Ctrl+Alt+X opens and closes the popup in turn, never duplicating it,
    starting from a popup closed on a previous page (where it used to be duplicated)."""
    t.load(settings=EMULE, popup_mode=0)
    t.eq(t.js(POPUP), [0, 0, 0], 'closed at load')
    for expected, mode in (([1, 9, 0], 1), ([0, 0, 0], 0), ([1, 9, 0], 1), ([0, 0, 0], 0)):
        t.keys('x')
        t.eq((t.js(POPUP), t.gm('popup_mode')), (expected, mode), f'after Ctrl+Alt+X: {expected}')
    t.eq(t.errors, [], 'no JavaScript error')


def test_shortcuts_without_links(t):
    """SF-1.12: on a page without ed2k links, no shortcut opens a popup or raises an error."""
    for key in 'ocmx':
        t.load('__nolinks', settings=EMULE)
        t.keys(key)
        t.eq(t.js(POPUP), [0, 0, 0], f'Ctrl+Alt+{key.upper()}: no popup')
        t.eq(t.errors, [], f'Ctrl+Alt+{key.upper()}: no JavaScript error')
        if key == 'm':
            t.eq(t.gm('popup_mode'), 1, 'Ctrl+Alt+M: stored mode unchanged')


def test_debug_traces(t):
    """A-10: the debug traces are off on a new installation, and the menu entry
    "Toggle debug traces" switches them on and off, for the next pages too."""
    t.load(debug=None)
    t.eq([c for c in t.console if 'saveConfig()' in c], [], 'no trace on a new installation')
    t.menu('d')
    t.check(t.dialogs and 'debug traces on' in t.dialogs[-1], 'menu: traces switched on', t.dialogs)
    t.eq(t.gm('debug_mode'), 1, 'setting stored')
    t.console.clear()
    t.reload()
    t.check(t.traced('saveConfig() storing the settings'), 'traces shown on the next page')
    t.menu('d')
    t.check(t.dialogs and 'debug traces off' in t.dialogs[-1], 'menu: traces switched off', t.dialogs)
    t.console.clear()
    t.reload()
    t.eq([c for c in t.console if 'saveConfig()' in c], [], 'no trace any more on the next page')


def test_menu_entries(t):
    """SF-9: the userscript manager menu entries, called the way Tampermonkey calls them."""
    t.load(settings=EMULE)
    t.menu('c')
    t.eq(t.js(POPUP), [0, 0, 0], 'menu "Close Popup" closes it')
    try:
        t.menu('o')
        t.eq(t.js(POPUP), [1, 9, 0], 'menu "Open Popup" opens it, without reloading the page')
    except RuntimeError as e:
        t.check(False, 'menu "Open Popup" works', str(e).splitlines()[0])
    t.menu('m')
    t.eq(t.js(POPUP), [1, 0, 1], 'menu "Change mode" switches to edit mode')
    t.menu('s')
    t.check(t.settings_open(), 'menu "Settings" opens the settings dialog')
    t.eq(t.errors, [], 'no JavaScript error')


# ---- a huge number of links (A-8) -----------------------------------------------------
def many_links(t, count):
    """Serve a page with that many valid ed2k links, at /__many."""
    h = 'ABCDEF1234567890ABCDEF1234567890'
    t.serve('/__many', '<!doctype html><meta charset="utf-8">' + ''.join(
        f'<a href="ed2k://|file|a-long-file-name-to-fill-the-popup-number-{i:05}.mp3|1048576|{h}|/">{i}</a> '
        for i in range(count)))


def test_many_links_normal_mode(t):
    """SF-4.5 (A-8): with 1,000 links, the list of the popup is complete and its end reachable."""
    many_links(t, 1000)
    t.load('__many')
    t.eq(t.dialogs, [], 'no alert')
    state = t.js("""(function(){
        var b = document.getElementById('divBody'), a = document.querySelectorAll('#divBody a.ed2k');
        var names = [].map.call(a, function (x) { return x.textContent; });
        b.scrollTop = b.scrollHeight;
        var last = a[a.length - 1].getBoundingClientRect(), list = b.getBoundingClientRect(),
            popup = document.getElementById('theDiv').getBoundingClientRect();
        return [a.length, names.join('|') == eFiles.join('|'),
                last.bottom <= Math.min(list.bottom, popup.bottom) + 1];
    })()""")
    t.eq(state, [1000, True, True], '1,000 rows, every name identical, last row visible once the list scrolled down')


# [top toolbar visible, bottom toolbar visible, the popup scrolls, the list scrolls]
TOOLBARS = """(function(){
    var d = document.getElementById('theDiv'), b = document.getElementById('divBody'), r = d.getBoundingClientRect();
    var bars = d.querySelectorAll(':scope > .toolbar');
    function visible(el) { var x = el.getBoundingClientRect(); return x.top >= r.top - 1 && x.bottom <= r.bottom + 1; }
    return [visible(bars[0]), visible(bars[bars.length - 1]),
            d.scrollHeight > d.clientHeight + 1, b.scrollHeight > b.clientHeight + 1];
})()"""


def test_toolbars_stay_visible(t):
    """SF-2.9 (A-15): with many links only the list scrolls, both toolbars stay visible."""
    many_links(t, 1000)
    t.load('__many')
    t.eq(t.js(TOOLBARS), [True, True, False, True], 'at load: both toolbars visible, only the list scrolls')
    t.check(t.js("document.getElementById('theDiv').getBoundingClientRect().height") <= 800 + 4,
            'the maximum height of the popup (800 px by default) is kept')
    t.js("var b = document.getElementById('divBody'); b.scrollTop = b.scrollHeight")
    t.eq(t.js(TOOLBARS), [True, True, False, True], 'list scrolled to the end: both toolbars still visible')


def test_toolbars_few_links(t):
    """SF-2.9: with few links nothing scrolls, and each toolbar stays on one line."""
    t.load()
    t.eq(t.js(TOOLBARS), [True, True, False, False], 'both toolbars visible, no scrollbar')
    t.eq(t.js("[].map.call(document.querySelectorAll('#theDiv > .toolbar'), function (bar) {"
              "var h = bar.children; return Math.abs(h[0].getBoundingClientRect().top - h[1].getBoundingClientRect().top) < 2; })"),
         [True, True], 'the two halves of each toolbar on one line')


def test_many_links_edit_mode(t):
    """SF-4.5 (A-8): with 1,000 links (about 108,000 characters), the edit box holds the whole
    list and has no maximum length: the user can still type in it."""
    many_links(t, 1000)
    t.load('__many', popup_mode=2)
    t.eq(t.dialogs, [], 'no alert')
    t.check(t.js("document.getElementById('editbox').value === eLinks.join('\\n')"),
            'whole list, identical', t.js("document.getElementById('editbox').value.length"))
    t.eq(t.js("document.getElementById('editbox').maxLength"), -1, 'no maximum length')
    t.js("var e = document.getElementById('editbox'); e.focus(); e.setSelectionRange(e.value.length, e.value.length)")
    before = t.js("document.getElementById('editbox').value.length")
    t.cdp.call('Input.insertText', {'text': 'x'})
    t.cdp.pump(0.2)
    t.eq(t.js("document.getElementById('editbox').value.length"), before + 1, 'a character typed at the end is kept')
    t.eq(t.js(TOOLBARS)[:2], [True, True], 'both toolbars visible')


def test_old_maxlength_setting_ignored(t):
    """A-8: a MaxLength value stored by a previous version is ignored, without any alert."""
    t.load(settings={'editMaxLength': 10000}, popup_mode=2)
    t.eq(t.dialogs, [], 'no alert')
    t.eq(t.js("document.getElementById('editbox').maxLength"), -1, 'no maximum length on the edit box')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("!!document.getElementById('GM_config_field_editMaxLength')"), False, 'no MaxLength field any more')
