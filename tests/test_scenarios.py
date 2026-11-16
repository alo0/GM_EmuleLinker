"""Level 2: scenarios on the served pages, with real keyboard shortcuts and caught alerts.

The references in the comments (SF-x, L-x, §) point to SPECIFICATIONS.md. The sending
itself is tested in test_sending.py, against fake ed2k clients.
"""
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Settings for the remote eMule method: its URLs show the category that is sent
EMULE = {'ed2kDlMethod': 'emule', 'emuleUrl': 'http://127.0.0.1:4711/',
         'emulePwd': 'secret', 'emuleCat': '*default=0;'}

NAMES = {'example1.cbz', 'example2.avi', 'Documentary Planet Earth 4K.mp4',
         'Été à Paris (Café).mp3', 'Conférence Téléphonique (v2.0).mkv',
         'François & Marie [Résumé].docx', 'Ópera Española (Colección).flac',
         'Bücher über Geräte (édition).pdf', 'Guide Réseau été 2024.emulecollection'}

ROWS = "document.querySelectorAll('#divBody a.ed2k').length"
SELECTED_CAT = ("(function(){var s=document.getElementById('cat');"
                "return [s.options[s.selectedIndex].text, s.value]})()")
# the category that a sending carries, read from memory (SF-6.6)
SENT_CATS = "[getSelectedCat()]"


def with_emule(**changes):
    return dict(EMULE, **changes)


def test_detection(t):
    """SF-1: the 9 valid links of test_sample.html, the 2 invalid ones ignored. The page starts
    with the malformed link: the detection goes on after it (SF-1.7)."""
    t.load(settings=EMULE)
    t.eq(t.js("[].filter.call(document.querySelectorAll('a[href^=\"ed2k\"]'), function (a) {"
              "return !a.closest('#theDiv'); })[0].getAttribute('href')"), 'ed2k://xxxxxxxx',
         'the first ed2k link of the page is the malformed one')
    t.eq(t.js('eFiles[0]'), 'example1.cbz', 'the first file of the popup: the valid link that follows it')
    t.eq(t.dialogs, [], 'no alert')
    t.eq(t.js('eLinks.length'), 9, 'links detected')
    t.eq(set(t.js('eFiles')), NAMES, 'file names, decoded')
    t.eq(t.js(ROWS), 9, 'rows in the popup')
    t.check(t.traced('ignoring malformed ed2k link: ed2k://xxxxxxxx'), 'malformed link ignored (SF-1.7)')
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
    """SF-6.5: an empty Category setting is told in the band, in orange until closed (an alert of the browser up to 0.14),
    no longer stops the script, and the corrected value is stored so that the message does not come back (SF-8.7)."""
    t.load(settings=with_emule(emuleCat=''))
    t.eq(t.dialogs, [], 'no alert')
    t.eq([t.js("(document.querySelector('#emlStatus .emlStatusText') || {}).textContent"), t.js("(document.getElementById('emlStatus') || {}).className")],
         ['No valid category: the default value (*default=0) is used instead.', 'doubt'], 'told in the band, in orange')
    t.pump(9)
    t.check(t.js("!!document.getElementById('emlStatus')"), 'it stays until closed')
    t.check(t.traced('no valid category found'), 'trace of strToCat()')
    t.eq(t.js(ROWS), 9, 'the popup is displayed')
    t.check(t.open_settings(), 'the shortcuts are installed')
    t.close_settings()
    t.eq(t.stored_settings().get('emuleCat'), '*default=0', 'corrected value stored')
    t.reload()
    t.eq(t.js("!!document.getElementById('emlStatus')"), False, 'no message on the next page load')


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


def script_version():
    with open(os.path.join(ROOT, 'GM_EmuleLinker.user.js'), encoding='utf-8') as f:
        return re.search(r'^// @version\s+(\S+)', f.read(), re.M).group(1)


def field(name):
    return f"document.getElementById('GM_config_field_{name}')"


def test_settings_dialog_look(t):
    """SF-8.1, SF-8.3, SF-8.8 and SF-8.11: title with the version, on the light blue of the toolbars
    of the popup (SF-2.5), the help of a field shown under it when it has the focus, masked password,
    backdrop, Escape to close."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_header').firstChild.textContent"),
         f'Emule Linker {script_version()} — Settings', 'title with the version')
    t.eq(t.js("getComputedStyle(document.getElementById('GM_config_header')).backgroundColor"),
         t.js("getComputedStyle(document.getElementById('emlTop')).backgroundColor"), 'title on the color of the toolbars')
    t.eq(t.js("getComputedStyle(document.getElementById('GM_config_header')).backgroundColor"), 'rgb(232, 241, 251)', 'light blue')
    tooltips = "document.querySelectorAll('#GM_config .config_var[title]').length"
    t.eq(t.js("document.querySelectorAll('#GM_config .config_var .help').length"), 21,
         'a help for each field (User included, 0.12; Links checked by default, 0.13; Language, Default popup view, Theme and Size, Toolbars (0.15), '
         'Show a message when the popup is closed, Show the category list, Show the server list, '
         'Popup position and Popup scrolling in place of Popup Position, 0.14; Keyboard shortcuts, 0.15)')
    t.eq(t.js(tooltips), 21, 'helps hidden: each one is the tooltip of its row')
    shown = ("[].filter.call(document.querySelectorAll('#GM_config .help'), function (h) {"
             "return getComputedStyle(h).display != 'none'; }).length")
    help_btn = "document.getElementById('GM_config_helpBtn').title"
    t.eq([t.js(shown), t.js(help_btn)], [0, 'Display inline help'], 'helps hidden at first')
    t.js(f"{field('emuleCat')}.focus()")
    t.eq(t.js(shown), 0, 'nothing shown on focus: the fields do not move')
    t.click('#GM_config_helpBtn')
    t.eq([t.js(shown), t.js(help_btn)], [21, 'Hide inline help'], 'Help button: every help shown')
    t.eq(t.js(tooltips), 0, 'helps shown: no tooltip repeating them')
    # the field, or the field and its Import button (Category, with eMule and aMule 3.x)
    edges = ("(function(n){var f=(document.querySelector('#GM_config_'+n+'_var .catbox')||"
             "document.getElementById('GM_config_field_'+n)).getBoundingClientRect(),"
             "h=document.querySelector('#GM_config_'+n+'_var .help').getBoundingClientRect();"
             "return [Math.abs(f.left-h.left)<0.5, Math.abs(f.right-h.right)<0.5];})")       # within half a pixel
    t.eq([t.js(f"{edges}('emuleUrl')"), t.js(f"{edges}('emuleCat')")], [[True, True], [True, True]],
         'Server URL, and Category with its Import button, as wide as their help')
    t.eq(t.js("(function(){var p=document.getElementById('GM_config_field_emulePwd').getBoundingClientRect(),"
              "b=document.querySelector('#GM_config .pwdbox').lastElementChild.getBoundingClientRect(),"
              "h=document.querySelector('#GM_config_emulePwd_var .help').getBoundingClientRect();"
              "return [Math.abs(p.left-h.left)<0.5, Math.abs(b.right-h.right)<0.5];})()"),
         [True, True], 'Password and its buttons (Show, Test) as wide as their help')
    t.close_settings()
    t.check(t.open_settings(), 'settings dialog opened again')
    t.eq(t.js(shown), 21, 'the choice is kept at the next opening')
    t.click('#GM_config_helpBtn')
    t.eq([t.js(shown), t.js(help_btn), t.gm('settings_help'), t.js(tooltips)], [0, 'Display inline help', 0, 21],
         'Help button again: hidden, stored, tooltips back')
    t.eq([t.js(f"{field(n)}.size") for n in ('emuleUrl', 'emuleCat', 'popupRows', 'editRow')],
         [32, 40, 6, 4], 'fields sized to their content')
    t.eq([t.js("document.getElementById('GM_config_emuleUrl_field_label').textContent"),
          t.js("document.getElementById('GM_config_emulePwd_field_label').textContent")],
         ['Server URL', 'Password'], 'labels of the fields shared by every client')
    t.eq(t.js(f"{field('emulePwd')}.type"), 'password', 'password masked')
    t.js("document.querySelector('#GM_config .reveal').click()")
    t.eq([t.js(f"{field('emulePwd')}.type"), t.js("document.querySelector('#GM_config .reveal').textContent")],
         ['text', 'Hide'], 'Show button: password shown')
    t.check(t.js("!!document.getElementById('GM_config_backdrop')"), 'backdrop behind the dialog')
    t.press('Escape')
    t.check(not t.settings_open(), 'Escape closes the dialog')
    t.check(t.js("!document.getElementById('GM_config_backdrop')"), 'backdrop removed')
    t.eq(t.stored_settings(), EMULE, 'nothing saved')


def test_settings_dialog_width_border_links(t):
    """SF-2.5, SF-8.1 and SF-8.15: the popup and the dialog have a steel blue border; the dialog is
    half of the window wide, between 640 and 960 px; links to report a problem and to the repository
    are at its bottom, opening in a new tab."""
    steel = 'rgb(43, 92, 138)'
    width = "Math.round(document.getElementById('GM_config').getBoundingClientRect().width)"
    t.load(settings=EMULE)
    t.eq(t.js("getComputedStyle(document.getElementById('theDiv')).borderTopColor"), steel, 'popup: steel blue border')
    try:
        for screen, expected in ((1366, 683), (1920, 960), (2560, 960)):
            t.set_viewport(screen, 900)
            t.check(t.open_settings(), f'settings dialog opened ({screen} px)')
            # the border is 2 px on each side
            t.eq(t.js(width) - 4, expected, f'{screen} px wide window: a dialog {expected} px wide')
            t.close_settings()
    finally:
        t.clear_viewport()
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("getComputedStyle(document.getElementById('GM_config')).borderTopColor"), steel, 'dialog: steel blue border')
    links = t.js("[].map.call(document.querySelectorAll('#GM_config .footer a'), function (a) {"
                 "return [a.textContent, a.href, a.target, a.rel]; })")
    t.eq(links, [['Report a problem ↗', 'https://github.com/alo0/GM_EmuleLinker/issues', '_blank', 'noopener noreferrer'],
                 ['Emule Linker on GitHub ↗', 'https://github.com/alo0/GM_EmuleLinker', '_blank', 'noopener noreferrer']],
         'links to the issues and to the repository, in a new tab')


def test_page_text_styles_kept_out(t):
    """SF-2.6 and SF-8.1: the popup and the settings dialog are built inside the page, but do not take
    its text styles: on a page that centers its text (some forums), with capitals, spacing, indent and
    italics, their text stays as designed."""
    t.serve('/__styled', '<!doctype html><meta charset="utf-8"><title>styled page</title>'
            '<style>body, div, td, span, label { text-align: center; text-transform: uppercase; letter-spacing: 3px;'
            ' word-spacing: 9px; text-indent: 30px; font-style: italic; line-height: 3; }</style>'
            '<div><a href="ed2k://|file|a.mp3|1048576|ABCDEF1234567890ABCDEF1234567890|/">a.mp3</a></div>')
    style = ("(function(sels){return sels.map(function(s){var e=document.querySelector(s);if(!e)return s+': missing';"
             "var c=getComputedStyle(e);return [s,c.textAlign,c.textTransform,c.letterSpacing,c.wordSpacing,c.textIndent,"
             "c.fontStyle].join(' ');});})")
    normal = 'none normal 0px 0px normal'
    t.load('__styled', settings=dict(EMULE, ed2kDlMethod='amuleapi'))
    t.js("showStatus('1 link(s) added to aMule', true)")
    t.eq(t.js(style + "(['#divBody td', '#emlStatus', '#theDiv .toolbar', '#theDiv .emlCount'])"),
         [f'{s} left {normal}' for s in ('#divBody td', '#emlStatus', '#theDiv .toolbar', '#theDiv .emlCount')],
         'popup: aligned to the left, no style of the page')
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_helpBtn')
    # the address of a server (that of Local, "nothing to configure", is in italics on purpose)
    parts = ['#GM_config .help', '#GM_config .srow label', '#GM_config .srow + .srow .sum', '#GM_config .sadd',
             '#GM_config .section_desc']
    t.eq(t.js(style + f"({parts!r})"), [f'{s} left {normal}' for s in parts], 'dialog: aligned to the left, no style of the page')
    t.eq([t.js("getComputedStyle(document.querySelector('#GM_config .field_label')).textAlign"),
          t.js("getComputedStyle(document.getElementById('GM_config_saveBtn')).textAlign"),
          t.js("getComputedStyle(document.querySelector('#GM_config .help')).lineHeight")],
         ['right', 'center', 'normal'], 'labels to the right, buttons centered, normal line height')


def test_settings_dialog_in_low_window(t):
    """SF-8.13: the dialog is anchored at the top of the window and never higher than it, even
    when the window is made lower once it is open: it scrolls inside, down to its Save button.
    Once closed, resizing the window does not show it again."""
    box = ("(function(){var b=document.getElementById('GM_config').getBoundingClientRect();"
           "return [Math.round(b.top), Math.round(b.bottom), innerHeight];})()")
    save_visible = ("(function(){var r=document.getElementById('GM_config_saveBtn').getBoundingClientRect();"
                    "return r.top >= 0 && r.bottom <= innerHeight;})()")
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    try:
        t.set_viewport(1200, 400)
        t.js("window.dispatchEvent(new Event('resize'))")
        t.pump(0.2)
        top, bottom, height = t.js(box)
        t.eq(top, 10, 'anchored at the top of the window')
        t.check(bottom <= height, 'its bottom inside the window', [top, bottom, height])
        t.js("var d = document.getElementById('GM_config'); d.scrollTop = d.scrollHeight")
        t.check(t.js(save_visible), 'scrolled down inside: the Save button is reachable')
        t.close_settings()
        t.js("window.dispatchEvent(new Event('resize'))")
        t.pump(0.2)
        t.eq(t.js("getComputedStyle(document.getElementById('GM_config')).display"), 'none',
             'closed: a resize does not show it again')
        t.eq(t.errors, [], 'no error on resize')
    finally:
        t.clear_viewport()


# the list of the servers of the settings dialog: [id, checked, name, method, address]
SERVER_ROWS = ("[].map.call(document.querySelectorAll('#GM_config_servers .srow'), function (r) {"
               "return [r.getAttribute('data-server'), r.querySelector('input').checked, r.querySelector('label').textContent,"
               "r.querySelector('.method').textContent, r.querySelector('.sum').textContent]; })")
SHOWN_FIELDS = ("['serverName','serverMethod','emuleUrl','emuleUser','emulePwd','emuleCat'].filter(function (id) {"
                "var r = document.getElementById('GM_config_' + id + '_var'); return r.offsetParent != null; })")
EDITED = ("(function(){var f=document.getElementById('GM_config_server_fields');"
          "return f.style.display == 'none' ? null : f.previousElementSibling.getAttribute('data-server');})()")
ERRORS = ("[].map.call(document.querySelectorAll('#GM_config .error'), function (e) {"
          "return e.parentNode.id.replace('GM_config_', '').replace('_var', '') + ': ' + e.textContent; })")


def server_ids(t, name):
    return [r[0] for r in t.js(SERVER_ROWS) if r[2] == name]


def click_server(t, name, what='radio'):
    """Click the radio button, Edit or Delete of the server with this name, as the user does."""
    sid = server_ids(t, name)[0]
    selector = {'radio': f'#GM_config_server_radio_{sid}', 'edit': f'#GM_config_server_{sid} .edit',
                'delete': f'#GM_config_server_{sid} .del'}[what]
    t.click(selector)


def set_server(t, name=None, method=None, **values):
    """Type the settings of the server being edited."""
    if name is not None:
        t.set_field('serverName', name)
    if method is not None:
        t.js(f"var s = {field('serverMethod')}; s.value = '{method}'; s.dispatchEvent(new Event('change'))")
    for key, value in values.items():
        t.set_field(key, value)


def stored_servers(t):
    raw = t.gm('servers')
    return {'active': None, 'list': []} if raw is None else json.loads(raw)


def test_settings_servers_list(t):
    """SF-8.9 and SF-8.14: the servers are a list, after a fixed Local row; the settings of the
    older versions become a server; under the server being edited, only the fields of its method."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    rows = t.js(SERVER_ROWS)
    t.eq([r[1:] for r in rows], [[False, 'Local', 'your system default', 'nothing to configure'],
                                 [True, 'eMule (web)', 'eMule (web)', 'http://127.0.0.1:4711/']],
         'Local, and the settings of before as a checked server named after its method')
    t.eq(t.js(EDITED), rows[1][0], 'its settings displayed under it')
    expected = {'emule': ['serverName', 'serverMethod', 'emuleUrl', 'emulePwd', 'emuleCat'],
                'amuleapi': ['serverName', 'serverMethod', 'emuleUrl', 'emulePwd', 'emuleCat'],
                'amule': ['serverName', 'serverMethod', 'emuleUrl', 'emulePwd', 'emuleCat'],
                'mldonkey': ['serverName', 'serverMethod', 'emuleUrl', 'emuleUser', 'emulePwd'],
                'custom': ['serverName', 'serverMethod', 'emuleUrl', 'emuleCat']}
    for method in ('emule', 'amuleapi', 'amule', 'mldonkey', 'custom'):
        set_server(t, method=method)
        t.eq(t.js(SHOWN_FIELDS), expected[method], f'{method}: the fields it uses')
    t.eq(t.js(f"[].map.call({field('serverMethod')}.options, function (o) {{ return o.textContent; }})"),
         ['eMule (web)', 'aMule 3.x (amuleapi)', 'aMule 2.x (amuleweb)', 'MLDonkey (web)', 'Custom (post to your own server)'],
         'the methods of a server: every one but Local')
    t.click('#GM_config_server_radio_local')
    t.eq([t.js(EDITED), t.js(SHOWN_FIELDS)], [None, []], 'Local checked: no field')
    # a long method name does not run over the address: cut by "...", whole in its tooltip
    badge = ("(function(){var r=document.querySelectorAll('#GM_config_servers .srow')[1];"
             "var b=r.querySelector('.method'), u=r.querySelector('.sum');"
             "return [b.getBoundingClientRect().right <= u.getBoundingClientRect().left, b.title];})()")
    t.eq(t.js(badge), [True, 'Custom (post to your own server)'], 'Custom badge within its column, whole name as tooltip')


def test_settings_two_servers_same_method(t):
    """SF-8.14: several servers of the same method, each one with its own settings; Save stores all
    of them, and GM_config the method and settings of the checked one, which the script then uses."""
    t.load(settings={'ed2kDlMethod': 'amuleapi', 'emuleUrl': 'http://192.168.1.10:4711/', 'emulePwd': 'nas-password',
                     'emuleCat': '*default=0;BD=1'})
    t.check(t.open_settings(), 'settings dialog opened')
    set_server(t, name='aMule NAS')
    t.click('#GM_config_addServer')
    t.eq([t.js(EDITED) == server_ids(t, 'New server')[0], t.js(f"{field('serverName')}.value")], [True, 'New server'],
         '+ Add a server: a new server displayed')
    t.eq([t.js(f"{field(n)}.value") for n in ('emuleUrl', 'emulePwd', 'emuleCat')],
         ['http://127.0.0.1:4711/', '', '*default=0;'], 'with the default settings')
    set_server(t, name='aMule seedbox', method='amuleapi', emuleUrl='https://seedbox.example.org:4711/', emulePwd='box-password')
    click_server(t, 'aMule NAS', 'edit')
    t.eq([t.js(f"{field(n)}.value") for n in ('serverName', 'emuleUrl', 'emulePwd')],
         ['aMule NAS', 'http://192.168.1.10:4711/', 'nas-password'], 'the NAS keeps its own settings')
    t.eq([[r[2], r[3], r[4]] for r in t.js(SERVER_ROWS)[1:]],
         [['aMule NAS', 'aMule 3.x (amuleapi)', 'http://192.168.1.10:4711/'],
          ['aMule seedbox', 'aMule 3.x (amuleapi)', 'https://seedbox.example.org:4711/']], 'two aMule 3.x servers listed')
    click_server(t, 'aMule seedbox')
    t.save_settings()
    stored = t.stored_settings()
    t.eq([stored.get(k) for k in ('ed2kDlMethod', 'emuleUrl', 'emulePwd')],
         ['amuleapi', 'https://seedbox.example.org:4711/', 'box-password'], 'GM_config: the checked server')
    kept = stored_servers(t)
    t.eq([srv['name'] for srv in kept['list']], ['aMule NAS', 'aMule seedbox'], 'both servers stored')
    t.eq([srv['name'] for srv in kept['list'] if srv['id'] == kept['active']], ['aMule seedbox'], 'the checked one')
    t.eq(t.js('emuleUrl'), 'https://seedbox.example.org:4711/', 'after the reload, the script uses the seedbox')


def test_settings_edit_without_choosing(t):
    """SF-8.14: Edit displays the settings of a server without checking it; Close forgets every change."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_addServer')
    set_server(t, name='My server', method='custom', emuleUrl='https://example.org/ed2k')
    t.close_settings()
    t.eq([t.gm('servers'), t.stored_settings()], [None, EMULE], 'Close: nothing stored')
    t.check(t.open_settings(), 'settings dialog opened again')
    t.click('#GM_config_addServer')
    set_server(t, name='My server', method='custom', emuleUrl='https://example.org/ed2k')
    click_server(t, 'eMule (web)', 'edit')
    t.eq([r[2] for r in t.js(SERVER_ROWS) if r[1]], ['eMule (web)'], 'eMule still checked')
    t.save_settings()
    t.eq(t.stored_settings().get('ed2kDlMethod'), 'emule', 'Save: eMule still the method used')
    t.eq([srv['name'] for srv in stored_servers(t)['list']], ['eMule (web)', 'My server'], 'My server stored')


def test_settings_server_names_and_category(t):
    """SF-8.14: a server needs a name, different from the others, and a valid category list: until
    then, it stays displayed, with the error under the field."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_addServer')
    set_server(t, name='')
    t.click('#GM_config_server_radio_local')
    t.eq(t.js(ERRORS), ['serverName: A name is required'], 'name required')
    set_server(t, name='EMULE (web)')
    t.click('#GM_config_addServer')
    t.eq(t.js(ERRORS), ['serverName: Another server already has this name'], 'names different (whatever the case)')
    set_server(t, name='Other', emuleCat=';;')
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(0.3)
    t.check(t.settings_open() and any(e.startswith('emuleCat:') for e in t.js(ERRORS)), 'category refused, nothing saved', t.js(ERRORS))
    t.eq(t.gm('servers'), None, 'nothing stored')


def test_settings_delete_server(t):
    """SF-8.14: Delete removes a server at once; a notice with an Undo button takes its place in the
    list, where the user clicked; the next action in the list removes it. Deleting the checked
    server checks Local."""
    notice = "(document.getElementById('GM_config_notice') || {}).textContent"
    # what is around the notice: [the row before it, the row or block after it]
    around = ("(function(){var n=document.getElementById('GM_config_notice'); if (!n) return null;"
              "var b=n.previousElementSibling, a=n.nextElementSibling;"
              "var name=function(e){ if (!e) return null; if (e.classList.contains('srow')) return e.querySelector('label').textContent;"
              "return e.className; }; return [n.parentNode.id, name(b), name(a)];})()")
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    for name in ('aMule NAS', 'aMule seedbox'):
        t.click('#GM_config_addServer')
        set_server(t, name=name)
    click_server(t, 'aMule NAS', 'delete')
    t.eq([r[2] for r in t.js(SERVER_ROWS)], ['Local', 'eMule (web)', 'aMule seedbox'], 'aMule NAS removed')
    t.check((t.js(notice) or '').startswith('Server "aMule NAS" deleted, not saved yet.'), 'notice', t.js(notice))
    t.eq(t.js(around), ['GM_config_servers', 'eMule (web)', 'aMule seedbox'], 'the notice in its place, in the list')
    t.click('#GM_config_undoBtn')
    t.eq([r[2] for r in t.js(SERVER_ROWS)], ['Local', 'eMule (web)', 'aMule NAS', 'aMule seedbox'], 'Undo: back in its place')
    t.eq(t.js(notice), None, 'Undo: no notice')
    click_server(t, 'aMule seedbox', 'delete')
    t.eq(t.js(around)[2], 'sadd', 'the last server: the notice before "+ Add a server"')
    click_server(t, 'aMule NAS', 'edit')
    t.eq(t.js(notice), None, 'the next action in the list removes the notice')
    click_server(t, 'eMule (web)', 'delete')
    t.eq([[r[2], r[1]] for r in t.js(SERVER_ROWS)], [['Local', True], ['aMule NAS', False]], 'the checked server deleted: Local checked')
    t.save_settings()
    t.eq([t.stored_settings().get('ed2kDlMethod'), [srv['name'] for srv in stored_servers(t)['list']]],
         ['local', ['aMule NAS']], 'Save: Local, aMule NAS kept')


def test_settings_undo_button(t):
    """SF-8.14: the Undo button of a notice has the style of the Show button, and is always on the
    right of the notice; in the list of the servers, on the right edge of the fields and of their
    buttons (Show, Test)."""
    undo = ("(function(){var u=document.getElementById('GM_config_undoBtn'), s=document.querySelector('#GM_config .reveal'),"
            "last=document.querySelector('#GM_config .pwdbox').lastElementChild;"
            "var n=u.parentNode, cu=getComputedStyle(u), cs=getComputedStyle(s), cn=getComputedStyle(n);"
            "return {style: [cu.fontSize, cu.padding, cs.fontSize, cs.padding],"
            "end: Math.round(n.getBoundingClientRect().right - parseFloat(cn.paddingRight) - u.getBoundingClientRect().right),"
            "show: Math.round(last.getBoundingClientRect().right - u.getBoundingClientRect().right)};})()")
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    for name in ('aMule NAS', 'aMule seedbox'):
        t.click('#GM_config_addServer')
        set_server(t, name=name)
    click_server(t, 'aMule NAS', 'edit')
    click_server(t, 'aMule seedbox', 'delete')
    r = t.js(undo)
    t.eq(r['style'], ['11px', '2px 8px'] * 2, 'Undo of a deleted server: the style of Show')
    t.eq([r['end'], r['show']], [0, 0], 'on the right of its notice, under the buttons of the password')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    r = t.js(undo)
    t.eq(r['style'], ['11px', '2px 8px'] * 2, 'Undo of Reset: the style of Show')
    t.eq(r['end'], 0, 'on the right of its notice')


def test_settings_reset_and_undo(t):
    """SF-8.12: Reset sets every setting back to its default value in the dialog only: Local is
    checked and every server removed. It highlights what it changed, and can be undone; Save then
    stores it."""
    custom = {'ed2kDlMethod': 'amuleapi', 'emuleUrl': 'http://192.168.1.10:4711/', 'emulePwd': 'secret',
              'emuleCat': '*Video=2;Audio=1', 'popupRows': 20, 'checkFilter': r'/\.cbz$/i'}
    marked = "[].map.call(document.querySelectorAll('#GM_config .config_var.changed'), function (r) { return r.id; })"
    notice = "(document.getElementById('GM_config_notice') || {}).textContent"
    t.load(settings=custom)
    t.check(t.open_settings(), 'settings dialog opened')
    t.check(t.js("!!document.getElementById('GM_config_resetBtn')"), 'Reset button')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq([[r[2], r[1]] for r in t.js(SERVER_ROWS)], [['Local', True]], 'Local checked, no server')
    t.eq([t.js(EDITED), t.js(f"{field('popupRows')}.value"), t.js(f"{field('checkFilter')}.value")], [None, '40', ''],
         'no field displayed, default sizes, no filter')
    t.eq(sorted(t.js(marked)), ['GM_config_checkFilter_var', 'GM_config_ed2kDlMethod_var', 'GM_config_popupRows_var'],
         'servers, height and filter highlighted')
    t.check((t.js(notice) or '').startswith('3 settings set back to their default value'), 'notice', t.js(notice))
    t.eq(t.stored_settings(), custom, 'nothing saved')
    t.js("document.getElementById('GM_config_undoBtn').click()")
    t.eq([[r[2], r[1]] for r in t.js(SERVER_ROWS)], [['Local', False], ['aMule 3.x (amuleapi)', True]], 'Undo: the server back')
    t.eq([t.js(f"{field(n)}.value") for n in ('emuleUrl', 'emulePwd', 'emuleCat', 'popupRows', 'checkFilter')],
         ['http://192.168.1.10:4711/', 'secret', '*Video=2;Audio=1', '20', r'/\.cbz$/i'], 'Undo: its settings back')
    t.eq([t.js(marked), t.js(notice)], [[], None], 'Undo: no highlight, no notice')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.save_settings()
    t.eq([t.stored_settings().get(k) for k in ('ed2kDlMethod', 'emulePwd', 'popupRows', 'checkFilter')], ['local', '', 40, ''],
         'Reset then Save: default values stored')
    t.eq(stored_servers(t)['list'], [], 'no server')


def test_settings_checked_before_saving(t):
    """SF-8.10: a wrong value is shown under its field, without an alert, and nothing is saved;
    once corrected, the settings are saved."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.set_field('emuleCat', ';;')
    t.set_field('popupRows', 'abc')
    t.set_field('popupCols', '30')
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(0.5)
    t.eq(t.dialogs, [], 'no alert')
    t.check(t.settings_open(), 'the dialog stays open')
    t.eq(t.stored_settings(), EMULE, 'nothing saved')
    errors = t.js("[].map.call(document.querySelectorAll('#GM_config .error'), function (e) {"
                  "return e.parentNode.id + ': ' + e.textContent; })")
    t.check(len(errors) == 3, 'three errors shown', errors)
    t.check(all(any(e.startswith(f'GM_config_{n}_var') for e in errors) for n in ('emuleCat', 'popupRows', 'popupCols')),
            'each one under its field', errors)
    t.eq(t.js("document.activeElement.id"), 'GM_config_field_emuleCat', 'focus on the first wrong field')
    t.set_field('emuleCat', '*default=0;Video=2')
    t.set_field('popupRows', '0')
    t.set_field('popupCols', '60')
    t.save_settings()
    t.eq(t.dialogs, [], 'no alert')
    t.eq([t.stored_settings().get(k) for k in ('emuleCat', 'popupRows', 'popupCols')],
         ['*default=0;Video=2', 0, 60], 'saved once corrected')


def test_settings_server_url_checked(t):
    """SF-8.10: the Server URL of every method, custom included, starts with http:// or https://;
    another one is refused by Save, under its field, and nothing is saved."""
    error = "(document.querySelector('#GM_config_emuleUrl_var .error') || {}).textContent"
    expected = 'An address starting with http:// or https:// is expected, e.g. http://127.0.0.1:4711/'
    for method, url in (('emule', '127.0.0.1:4711'), ('custom', 'ftp://example.com/post')):
        t.load(settings=dict(EMULE, ed2kDlMethod=method))
        t.check(t.open_settings(), 'settings dialog opened')
        t.set_field('emuleUrl', url)
        t.js("document.getElementById('GM_config_saveBtn').click()")
        t.pump(0.5)
        t.eq([t.js(error), t.settings_open(), t.stored_settings().get('emuleUrl')],
             [expected, True, EMULE['emuleUrl']], f'{method}, {url}: refused under the field, nothing saved')
    t.set_field('emuleUrl', 'https://example.com/post')
    t.save_settings()
    t.eq(t.stored_settings().get('emuleUrl'), 'https://example.com/post', 'custom, https: saved')


def test_edit_mode(t):
    """SF-4 and SF-5.4: Edit mode shows the links in a text area, Normal mode back to the list."""
    t.load(settings=EMULE)
    t.edit_mode()
    lines = t.js("(function(){var e=document.getElementById('editbox');return e ? e.value.split('\\n') : null})()")
    t.check(lines is not None, 'text area displayed')
    t.eq(len(lines or []), 9, 'one link per line')
    t.eq(t.js("document.getElementById('checkall').disabled"), True, '"check all" disabled')
    t.edit_mode()
    t.eq(t.js(ROWS), 9, 'back to the list')
    t.eq(t.js("document.getElementById('checkall').disabled"), False, '"check all" enabled again')


def test_local_method(t):
    """SF-7.7 and SF-7.8: local method, links encoded and every one clicked."""
    t.load(settings={'ed2kDlMethod': 'local'})
    hrefs = t.js("[].map.call(document.querySelectorAll('#divBody a.ed2k'), function (a) "
                 "{ return a.getAttribute('href'); })")
    t.eq(len(hrefs), 9, 'popup links')
    t.check(all(h.startswith('ed2k://%7Cfile%7C') for h in hrefs), 'popup links encoded', hrefs[:1])
    t.check(not any(c in h for h in hrefs for c in '| []#?'), 'no forbidden character left')
    t.eq(t.js("document.getElementById('cat').disabled"), True, 'category list disabled')
    t.catch_anchor_clicks()
    t.keys('d')
    clicked = t.clicked()
    t.eq(len(clicked), 9, 'one click per link')
    t.check(all(h.startswith('ed2k://%7Cfile%7C') for h in clicked), 'clicked links encoded')


def test_url_without_slash_stored(t):
    """SF-8.7: the URL completed with its final / is stored."""
    t.load(settings=with_emule(emuleUrl='http://127.0.0.1:4711'))
    t.eq(t.stored_settings().get('emuleUrl'), 'http://127.0.0.1:4711/', 'corrected URL stored')


def test_empty_password_accepted(t):
    """SF-8 (emulePwd): the eMule password is optional, eMule accepts a web interface without one:
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
    """SF-8 (emulePwd): with nothing stored (a new installation), the password is empty, not "something"."""
    t.load()
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_field_emulePwd').value"), '', 'empty password by default')


# ---- opening and closing the popup (SF-2.8) ----------------------------------------------
# [popups displayed, rows of the list, edit boxes]
POPUP = ("[document.querySelectorAll('#theDiv').length,"
         " document.querySelectorAll('#divBody a.ed2k').length,"
         " document.querySelectorAll('#editbox').length]")


def test_open_when_already_open(t):
    """SF-2.8: Ctrl+Alt+O on an open popup does not add a second one."""
    t.load(settings=EMULE)
    t.keys('o')
    t.eq(t.js(POPUP), [1, 9, 0], 'one popup, one list')
    t.eq(t.errors, [], 'no JavaScript error')


def test_open_keeps_edit_mode(t):
    """SF-2.8: Ctrl+Alt+O in edit mode leaves the edit box as it is."""
    t.load(settings=EMULE, popup_mode=2)
    t.keys('o')
    t.eq(t.js(POPUP), [1, 0, 1], 'one popup, still in edit mode')
    t.eq(t.js('popupMode'), 2, 'still in edit mode')


def test_default_view_closed(t):
    """SF-10.2: with the default view Closed, no popup on a page with ed2k links, on every page,
    until a shortcut opens it on this page."""
    t.load(settings=EMULE, popup_mode=0)
    t.eq(t.js(POPUP), [0, 0, 0], 'no popup, not even its toolbars')
    t.keys('o')
    t.eq(t.js(POPUP), [1, 9, 0], 'Ctrl+Alt+O opens it with its list')
    t.reload()
    t.eq(t.js(POPUP), [0, 0, 0], 'closed again on the next page')
    t.eq(t.errors, [], 'no JavaScript error')


def test_state_applies_to_the_page(t):
    """SF-10.1: the state of the popup applies to the current page only: closed, or in edit mode,
    the next page opens in the default view (maximized), where it used to stay closed."""
    t.load(settings=EMULE)
    t.close_popup()
    t.eq(t.js(POPUP), [0, 0, 0], 'closed on this page')
    t.reload()
    t.eq(t.js(POPUP), [1, 9, 0], 'open with its list on the next page')
    t.edit_mode()
    t.eq(t.js(POPUP), [1, 0, 1], 'edit mode on this page')
    t.reload()
    t.eq(t.js(POPUP), [1, 9, 0], 'normal mode on the next page')
    t.eq(t.gm('popup_mode'), None, 'nothing stored')
    t.eq(t.errors, [], 'no JavaScript error')


def test_default_view_setting(t):
    """SF-8: the General section, first in the settings dialog, with the Default popup view:
    a drop-down list, Maximized by default, whose help tells how to open the popup when it is
    closed; Closed saved, the next page has no popup."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_section_header_0').textContent"), 'General', 'first section')
    t.eq(t.js("document.getElementById('GM_config_section_header_1').textContent"), 'Servers', 'then the servers')
    t.eq(t.js("document.getElementById('GM_config_popupView_field_label').textContent"), 'Default popup view', 'label')
    t.eq(t.js("Array.prototype.map.call(document.querySelectorAll('#GM_config_field_popupView option'),"
              " function(o){ return [o.value, o.textContent]; })"),
         [['maximized', 'Maximized (default)'], ['minimized', 'Minimized'], ['closed', 'Closed']], 'the three views')
    t.eq(t.js("document.getElementById('GM_config_field_popupView').value"), 'maximized', 'maximized by default')
    help = t.js("document.querySelector('#GM_config_popupView_var .help').textContent")
    for text in ('Ctrl+Alt+O', 'Ctrl+Alt+S', 'Tampermonkey', 'Violentmonkey'):
        t.check(text in help, f'the help tells {text}', help)
    t.js("document.getElementById('GM_config_field_popupView').value = 'closed'")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq(t.stored_settings().get('popupView'), 'closed', 'Closed saved')
    t.eq(t.js(POPUP), [0, 0, 0], 'no popup on the next page')
    t.eq(t.errors, [], 'no JavaScript error')


def test_close_then_open(t):
    """SF-9: the popup closed, Ctrl+Alt+O opens it again, once."""
    t.load(settings=EMULE)
    t.close_popup()
    t.eq(t.js(POPUP), [0, 0, 0], 'closed')
    t.eq(t.js('popupMode'), 0, 'closed state')
    t.keys('o')
    t.keys('o')
    t.eq(t.js(POPUP), [1, 9, 0], 'opened once, even with two Ctrl+Alt+O')
    t.eq(t.errors, [], 'no JavaScript error')


# the view of the popup: closed, minimized (only its top toolbar shown) or maximized
VIEW = ("(function(){var p=document.querySelectorAll('#theDiv');if(p.length!=1)return p.length?'several':'closed';"
        "var b=document.getElementById('divBody'),z=document.getElementById('emlBottom');"
        "var hidden=function(e){return !e||getComputedStyle(e).display=='none';};"
        "if(hidden(b)&&hidden(z))return 'minimized';if(!hidden(b)&&!hidden(z))return 'maximized';return 'mixed';})()")

# [id or class, left, top, width, height] of the controls of a toolbar, in their order
BAR = ("(function(id){return [].filter.call(document.getElementById(id).children,function(e){return !e.classList.contains('emlOff');})"
       ".map(function(e){"
       "var r=e.getBoundingClientRect();return [e.id||e.className,r.left,r.top,r.width,r.height];});})")


def test_toggle_with_ctrl_alt_w(t):
    """SF-9 and SF-10: Ctrl+Alt+W switches the popup maximized, minimized, closed, in turn, never
    duplicating it, starting from a popup closed at load (where it used to be duplicated)."""
    t.load(settings=EMULE, popup_mode=0)
    t.eq(t.js(VIEW), 'closed', 'closed at load')
    for expected in ('maximized', 'minimized', 'closed', 'maximized', 'minimized'):
        t.keys('w')
        t.eq(t.js(VIEW), expected, f'after Ctrl+Alt+W: {expected}')
    t.eq(t.errors, [], 'no JavaScript error')


def test_toolbars(t):
    """SF-2.7: the controls of both toolbars, in the order of the mockup, all 22 px high and
    on one line; the icons at the right of the top one; the category and Download at the right of the
    bottom one; every checkbox of the popup, toolbars and list, in one column, and the file names
    aligned on the counters. EMULE offers two servers, Local and eMule: the server lists are shown (SF-6.11).
    The menu button of a narrow popup (SF-2.13), before the settings, is hidden while every control fits."""
    t.load(settings=EMULE)
    top, bottom = t.js(BAR + "('emlTop')"), t.js(BAR + "('emlBottom')")
    t.eq([c[0] for c in top], ['checkall', 'emlCount', 'srv', 'cat', 'emlAdd', 'emlDrag', 'emlMenuBtn', 'emlIcon emlRight', 'emlHelpBtn',
                               'emlMin', 'emlClose'],
         'top toolbar: box, counter, server, category, Download, (free space, menu), settings, help, minimize, close')
    t.eq([c[3] for c in top if c[0] == 'emlMenuBtn'], [0], 'the menu button hidden: every control fits')
    t.check(all(c[3] >= 23.5 for c in top if c[0] == 'emlDrag'), 'a free space of 24 px at least, to move the popup', top)
    top = [c for c in top if c[0] not in ('emlMenuBtn', 'emlDrag')]
    t.eq([c[0] for c in bottom], ['checkall2', 'emlCount', 'emlEdit', 'emlExport', 'srv2', 'cat2', 'emlAdd'],
         'bottom toolbar: box, counter, Edit mode, Export, server, category, Download')
    t.eq(t.js("[].map.call(document.querySelectorAll('#emlTop button:not(.emlOff)'),function(b){"
              "return (b.getAttribute('data-icon')||b.textContent)+' | '+b.title;})"),
         ['Download | Download the checked links (Ctrl+Alt+D)', 'menu | Menu: the controls that do not fit in the toolbars of a narrow popup',
          'settings | Settings (Ctrl+Alt+S)', 'help | Help (Ctrl+Alt+H)',
          'minimize | Minimize (Ctrl+Alt+W)', 'close | Close'], 'labels (icons) and tooltips of the top toolbar')
    for name, bar in (('top', top), ('bottom', bottom)):
        controls = [c for c in bar if c[0] not in ('checkall', 'checkall2', 'emlCount')]
        t.eq(sorted({round(c[4], 1) for c in controls}), [22], f'{name} toolbar: every control 22 px high')
        t.eq(len({round(c[2], 1) for c in controls}), 1, f'{name} toolbar: on one line')
        box, count = bar[0], bar[1]
        centers = [c[2] + c[4] / 2 for c in (box, count, controls[0])]
        t.check(max(centers) - min(centers) < 1, f'{name} toolbar: box and counter centered on the controls', centers)
    t.eq(t.js("document.querySelectorAll('#theDiv .emlIcon:not(.emlMenu)')[0].getBoundingClientRect().width"), 22, 'square icons')
    right = t.js("(function(){var e=document.getElementById('emlTop');"
                 "return e.getBoundingClientRect().right-parseFloat(getComputedStyle(e).paddingRight);})()")
    t.check(abs(top[-1][1] + top[-1][3] - right) < 0.5, 'close at the right of the top toolbar', (top[-1], right))
    t.check(abs(bottom[-1][1] + bottom[-1][3] - right) < 0.5, 'Download at the right of the bottom toolbar', (bottom[-1], right))
    gaps = [round(b[1] - (a[1] + a[3]), 1) for a, b in zip(top[2:4], top[3:5])][:1]
    t.eq(gaps, [6], 'top toolbar: 6 px between the category and Download')
    boxes = t.js("[].map.call(document.querySelectorAll('#theDiv input.smallcheck'),function(b){return b.getBoundingClientRect().left;})")
    t.check(max(boxes) - min(boxes) < 0.5, 'every checkbox in one column', boxes)
    names = t.js("[].map.call(document.querySelectorAll('#divBody a.ed2k'),function(a){return a.getBoundingClientRect().left;})")
    t.check(max(names) - min(names) < 0.5 and abs(names[0] - top[1][1]) < 0.5, 'file names aligned on the counter',
            (names[0], top[1][1]))
    t.eq(t.errors, [], 'no JavaScript error')


GAPS = """(function(){
  var p=document.getElementById('theDiv').getBoundingClientRect();
  var l=document.getElementById('divBody').getBoundingClientRect();
  var c=document.querySelector('#emlTop .emlAdd').getBoundingClientRect(), c2=document.querySelector('#emlBottom .emlAdd').getBoundingClientRect();
  return [[c.top-(p.top+2), l.top-c.bottom], [c2.top-l.bottom, (p.bottom-2)-c2.bottom]];
})()"""


def test_toolbars_centered(t):
    """SF-2.7: each toolbar is centered between the border of the popup and the line that separates it
    from the list, 5 px above and below its controls; the rows of the list are 17 px high, in both
    browsers; the toolbars have a light blue background, from one side of the frame to the other;
    Download stands out on it, white with a blue border, its text black and not bold."""
    t.load(settings=EMULE)
    (above, below), (above2, below2) = t.js(GAPS)
    t.check(abs(above - below) < 0.5, 'top toolbar centered', (above, below))
    t.check(abs(above2 - below2) < 0.5, 'bottom toolbar centered', (above2, below2))
    t.check(abs(above - 5) < 0.5 and abs(above2 - 5) < 0.5, '5 px above and below the controls', (above, above2))
    rows = t.js("[].map.call(document.querySelectorAll('#divBody tr'),function(r){return r.getBoundingClientRect().height;})")
    t.check(all(abs(r - 17) < 0.25 for r in rows), 'rows of 17 px', rows)
    t.eq(t.js("[].map.call(document.querySelectorAll('#theDiv button.emlAdd'),function(b){var c=getComputedStyle(b);"
              "return [c.borderTopWidth+' '+c.borderTopColor, c.backgroundColor, c.color, c.fontWeight];})"),
         [['2px rgb(0, 117, 255)', 'rgb(255, 255, 255)', 'rgb(0, 0, 0)', '400']] * 2, 'Download: blue border, white, black text, not bold')
    bars = t.js("(function(){var d=document.getElementById('theDiv'),p=d.getBoundingClientRect(),l=p.left+d.clientLeft;"
                "return [].map.call(d.querySelectorAll('.toolbar'),function(b){var r=b.getBoundingClientRect();"
                "return [getComputedStyle(b).backgroundColor, Math.round((r.left-l)*10)/10, Math.round((p.right-d.clientLeft-r.right)*10)/10];});})()")
    t.eq(bars, [['rgb(232, 241, 251)', 0, 0]] * 2, 'toolbars: light blue, from one side of the frame to the other')
    t.eq(t.errors, [], 'no JavaScript error')


def test_page_toolbar_class(t):
    """SF-2.6: a page with its own .toolbar class (margins, border, height, background) does not change
    the toolbars of the popup."""
    t.serve('/__toolbar', '<!doctype html><meta charset="utf-8"><title>toolbar page</title>'
            '<style>.toolbar { margin: 20px; padding: 15px; border: 5px solid red; height: 60px; background: red;'
            ' float: right; width: 50px; box-shadow: 0 0 9px red; }</style>'
            '<div class="toolbar">page</div>'
            '<div><a href="ed2k://|file|a.mp3|1048576|ABCDEF1234567890ABCDEF1234567890|/">a.mp3</a></div>')
    t.load('__toolbar', settings=EMULE)
    t.eq(t.js("(function(){var e=document.getElementById('emlTop'),b=getComputedStyle(e);return [b.marginTop,b.borderTopWidth,"
              "Math.round(e.getBoundingClientRect().height)+'px',b.backgroundColor,b.cssFloat,b.boxShadow];})()"),
         ['0px', '0px', '32px', 'rgb(232, 241, 251)', 'none', 'none'], 'top toolbar: no style of the page')
    t.eq(t.errors, [], 'no JavaScript error')


# a page whose styles used to change the sizes of the popup: big buttons, lists and checkboxes, a small line height
FORUM_STYLES = ('<style>body, td, div { line-height: 0.8; } button, select { padding: 6px 14px; font-size: 15px; line-height: 2;'
                ' height: auto; min-height: 30px; } input[type=checkbox] { width: 20px; height: 20px; margin: 6px; }'
                ' table td { padding: 0; } hr { margin: 12px 0; }</style>')
SIZES = """(function(){
  var h=function(e){return Math.round(e.getBoundingClientRect().height*100)/100;};
  var q=function(s){return [].map.call(document.querySelectorAll(s),h);};
  return {controls: q('#theDiv .toolbar button:not(.emlMenu):not(.emlOff), #theDiv .toolbar select'), boxes: q('#theDiv input.smallcheck'),
          rows: q('#divBody tr'), bars: q('#theDiv .toolbar'),
          fonts: [].map.call(document.querySelectorAll('#theDiv .toolbar button, #theDiv .toolbar select, #theDiv .emlCount'),
                             function(e){return getComputedStyle(e).fontSize;})};
})()"""


def test_sizes_kept_from_the_page(t):
    """SF-2.6: the sizes of the popup are its own, whatever the styles of the page (a forum
    gave bigger buttons and smaller rows): controls of 22 px, font of 12 px, checkboxes of 13 px,
    rows of 17 px, toolbars of 32 px."""
    t.serve('/__forum', '<!doctype html><meta charset="utf-8"><title>forum page</title>' + FORUM_STYLES
            + '<table><tr><td><button>Reply</button> <select><option>Sort</option></select></td></tr></table>'
            + ''.join(f'<div><a href="ed2k://|file|file{i}.cbz|{i}048576|{i}BCDEF1234567890ABCDEF123456789{i}|/">file{i}</a></div>'
                      for i in range(1, 5)))
    for page in ('test_sample.html', '__forum'):
        t.load(page, settings=EMULE)
        s = t.js(SIZES)
        t.check(s['controls'] and all(abs(v - 22) < 0.25 for v in s['controls']), f'{page}: buttons and lists of 22 px', s['controls'])
        t.eq(sorted(set(s['fonts'])), ['12px'], f'{page}: font of 12 px')
        t.check(s['boxes'] and all(abs(v - 13) < 0.25 for v in s['boxes']), f'{page}: checkboxes of 13 px', s['boxes'])
        t.check(s['rows'] and all(abs(v - 17) < 0.25 for v in s['rows']), f'{page}: rows of 17 px', s['rows'])
        t.check(all(abs(v - 32) < 0.25 for v in s['bars']), f'{page}: toolbars of 32 px', s['bars'])
    t.eq(t.errors, [], 'no JavaScript error')


ALIGN = """(function(){
  var d=document.getElementById('theDiv'), p=d.getBoundingClientRect();
  var L=function(s){return [].map.call(document.querySelectorAll(s),function(e){return e.getBoundingClientRect().left;});};
  var R=function(e){return e.getBoundingClientRect().right;};
  var text=function(e){var r=document.createRange();r.selectNodeContents(e);return r.getBoundingClientRect();};
  return {boxes: L('#theDiv input.smallcheck'), counters: L('#theDiv .emlCount'),
          names: [].map.call(document.querySelectorAll('#divBody a.ed2k'),function(a){return text(a).left;}),
          topSelect: L('#emlTop select')[0], editMode: L('#emlBottom button')[0],
          close: R(document.querySelector('#emlTop button:last-child')), download: R(document.querySelector('#emlBottom .emlAdd')),
          sizes: [].map.call(document.querySelectorAll('#divBody tr td:last-child'),function(c){return text(c).right;}),
          innerLeft: p.left+d.clientLeft, innerRight: p.left+d.clientLeft+d.clientWidth};
})()"""


def test_alignments(t):
    """SF-2.11, as in the mockup: the checkboxes in one column; the file names on the counters; the list
    of the top toolbar on Edit mode; close, the bottom Download and the sizes (aligned at the right)
    on one right edge; as much space at the left of the checkboxes as at the right of that edge (9 px)."""
    t.load(settings=EMULE)
    a = t.js(ALIGN)
    near = lambda values, x: all(abs(v - x) < 0.5 for v in values)  # noqa: E731
    t.check(near(a['boxes'], a['boxes'][0]), 'checkboxes in one column', a['boxes'])
    t.check(near(a['counters'] + a['names'], a['counters'][0]), 'file names on the counters', (a['counters'], a['names']))
    t.check(near([a['editMode']], a['topSelect']), 'top list on Edit mode', (a['topSelect'], a['editMode']))
    t.check(near([a['download']] + a['sizes'], a['close']), 'close, Download and the sizes on one right edge',
            (a['close'], a['download'], a['sizes']))
    left, right = a['boxes'][0] - a['innerLeft'], a['innerRight'] - a['close']
    t.check(abs(left - 9) < 0.5 and abs(right - 9) < 0.5, '9 px at the left and at the right', (left, right))
    t.eq(t.errors, [], 'no JavaScript error')


def test_counter_width(t):
    """SF-2.10: the counter is as wide as its widest value on the page (total/total), its digits all of a
    width: checking or unchecking links moves nothing; 6 px between the counter and what follows."""
    links = ''.join(f'<div><a href="ed2k://|file|file{i:02d}.cbz|{i}048576|{i:02d}BCDEF1234567890ABCDEF12345678|/">f</a></div>'
                    for i in range(1, 13))
    t.serve('/__twelve', '<!doctype html><meta charset="utf-8"><title>twelve links</title>' + links)
    t.load('__twelve', settings=EMULE)
    place = "(function(){var c=document.querySelector('#emlTop .emlCount'),r=document.createRange(),n=c.nextElementSibling;" \
            "while (n && n.classList.contains('emlOff')) { n = n.nextElementSibling; } r.selectNodeContents(c);" \
            "return [r.getBoundingClientRect().right, n.getBoundingClientRect().left];})()"
    full, list_left = t.js(place)
    t.check(abs(list_left - full - 6) < 0.5, '6 px after 12/12', (full, list_left))
    for i in range(9):
        t.click(f'#l{i}')
    t.eq(t.js("document.querySelector('#emlTop .emlCount').textContent"), '3/12', '3/12')
    t.check(abs(t.js(place)[1] - list_left) < 0.5, 'the list has not moved', (t.js(place), list_left))
    t.eq(t.errors, [], 'no JavaScript error')


ICONS = """(function(){return [].map.call(document.querySelectorAll('#emlTop button.emlIcon:not(.emlMenu)'),function(b){
  var s=b.querySelector('svg'), r=b.getBoundingClientRect(), i=s?s.getBoundingClientRect():null;
  return [b.getAttribute('data-icon'), i ? Math.abs((i.top+i.bottom)/2-(r.top+r.bottom)/2) : null,
          i ? Math.abs((i.left+i.right)/2-(r.left+r.right)/2) : null, getComputedStyle(b).color];});})()"""


def test_icons(t):
    """SF-2.7: the icons of the top toolbar are drawn (SVG), centered in their buttons whatever the fonts;
    minimize in blue, close in red, settings in dark grey."""
    t.load(settings=EMULE)
    icons = t.js(ICONS)
    t.eq([i[0] for i in icons], ['settings', 'help', 'minimize', 'close'], 'settings, help, minimize, close')
    t.check(all(i[1] is not None and i[1] < 0.5 and i[2] < 0.5 for i in icons), 'every icon centered', icons)
    t.eq([i[3] for i in icons], ['rgb(51, 51, 51)', 'rgb(51, 51, 51)', 'rgb(0, 117, 255)', 'rgb(208, 0, 0)'], 'colors')
    t.click('#emlMin')
    icons = t.js(ICONS)
    t.check(icons[2][0] == 'maximize' and icons[2][1] is not None and icons[2][1] < 0.5, 'maximize, centered', icons[2])
    t.eq(t.errors, [], 'no JavaScript error')


LINES = """(function(){
  var d=document.getElementById('theDiv'), b=document.getElementById('divBody'), p=d.getBoundingClientRect(), r=b.getBoundingClientRect(), s=getComputedStyle(b);
  return {hr: document.querySelectorAll('#theDiv hr').length, top: s.borderTopWidth+' '+s.borderTopStyle, bottom: s.borderBottomWidth+' '+s.borderBottomStyle,
          left: r.left-(p.left+d.clientLeft), right: (p.left+d.clientLeft+d.clientWidth)-r.right};
})()"""


def test_separators(t):
    """SF-2.9: the toolbars are separated from the list by two lines that do not scroll with it, from one
    side of the frame to the other; none in edit mode, where the frame of the edit box separates."""
    many_links(t, 60)
    t.load('__many', settings=EMULE)
    lines = t.js(LINES)
    t.eq([lines['hr'], lines['top'], lines['bottom']], [0, '1px solid', '1px solid'], 'two lines, the borders of the list')
    t.check(abs(lines['left']) < 0.5 and abs(lines['right']) < 0.5, 'from one side of the frame to the other', lines)
    t.js("document.getElementById('divBody').scrollTop=300")
    t.pump(0.2)
    t.eq(t.js(LINES)['top'], '1px solid', 'still there once the list scrolled')
    t.edit_mode()
    lines = t.js(LINES)
    t.eq([lines['hr'], lines['top'], lines['bottom']], [0, '0px none', '0px none'], 'edit mode: no line')
    t.eq(t.errors, [], 'no JavaScript error')


SHADOWS = """(function(){
  var b=document.getElementById('divBody'), r=b.getBoundingClientRect();
  return [].map.call(document.querySelectorAll('#theDiv .emlShadow'),function(e){
    var q=e.getBoundingClientRect(), shown=getComputedStyle(e).display!='none';
    return [e.classList.contains('top')?'top':'bottom', shown,
            shown ? Math.abs(q.left-r.left-b.clientLeft)<0.5 && Math.abs(q.width-b.clientWidth)<0.5 : null,
            shown ? Math.abs((e.classList.contains('top') ? q.top-r.top-b.clientTop : r.top+b.clientTop+b.clientHeight-q.bottom))<0.5 : null];});
})()"""


def scroll_to(t, where):
    t.js("(function(){var b=document.getElementById('divBody');b.scrollTop=%s;})()" % where)
    t.pump(0.3)


def test_scroll_shadows(t):
    """SF-2.9: a shadow on the edge of the list where links are hidden: at the bottom when the list is at
    its top, on both edges in the middle, at the top at its bottom; laid over the list, without its
    scrollbar; none when every link is shown, nor in edit mode."""
    t.load(settings=EMULE)
    t.eq([s[:2] for s in t.js(SHADOWS)], [['top', False], ['bottom', False]], 'every link shown: no shadow')
    many_links(t, 60)
    t.load('__many', settings=EMULE)
    t.eq(t.js(SHADOWS), [['top', False, None, None], ['bottom', True, True, True]], 'at the top: a shadow at the bottom')
    scroll_to(t, 'b.scrollHeight/2-b.clientHeight/2')
    t.eq(t.js(SHADOWS), [['top', True, True, True], ['bottom', True, True, True]], 'in the middle: both')
    scroll_to(t, 'b.scrollHeight')
    t.eq(t.js(SHADOWS), [['top', True, True, True], ['bottom', False, None, None]], 'at the bottom: a shadow at the top')
    t.js("document.getElementById('theDiv').style.height='200px'")
    scroll_to(t, '0')
    t.eq(t.js(SHADOWS)[1][1:], [True, True, True], 'a smaller popup: the bottom shadow follows the list')
    t.edit_mode()
    t.eq(t.js(SHADOWS), [], 'edit mode: no shadow')
    t.eq(t.errors, [], 'no JavaScript error')


def test_counter(t):
    """SF-2.10: the counters tell the links that Download sends: the checked ones out of the links of the
    page, in both toolbars; in edit mode, the links of the text, as typed."""
    counters = "[].map.call(document.querySelectorAll('#theDiv .emlCount'),function(c){return c.textContent;})"
    t.load(settings=EMULE)
    t.eq(t.js(counters), ['9/9', '9/9'], 'every link checked')
    t.click('#l3')
    t.eq(t.js(counters), ['8/9', '8/9'], 'one link unchecked')
    t.edit_mode()
    t.eq(t.js(counters), ['9/9', '9/9'], 'edit mode: the links of the text')
    t.js("var e=document.getElementById('editbox');e.value=e.value.split('\\n').slice(2).join('\\n');"
         "e.dispatchEvent(new Event('input'))")
    t.eq(t.js(counters), ['7/9', '7/9'], 'edit mode: two lines removed')
    t.eq(t.errors, [], 'no JavaScript error')


def test_minimize(t):
    """SF-2.12: the minimize button shows the top toolbar only, at the same width: nothing moves in it;
    the list and the bottom toolbar are only hidden, the checked links kept; maximize shows them again.
    The same with the edit box, its text kept."""
    t.load(settings=EMULE)
    t.click('#l2')
    before = t.js(BAR + "('emlTop')")
    width = t.js("document.getElementById('theDiv').getBoundingClientRect().width")
    t.click('#emlMin')
    t.eq(t.js(VIEW), 'minimized', 'minimized')
    t.eq(t.js("document.getElementById('emlMin').getAttribute('data-icon')+' | '+document.getElementById('emlMin').title"),
         'maximize | Maximize (Ctrl+Alt+W)', 'the button maximizes now')
    after = t.js(BAR + "('emlTop')")
    t.check(all(abs(a[1] - b[1]) < 0.5 and abs(a[2] - b[2]) < 0.5 for a, b in zip(before, after)),
            'nothing moved in the top toolbar', (before, after))
    t.check(abs(t.js("document.getElementById('theDiv').getBoundingClientRect().width") - width) < 0.5, 'same width')
    t.click('#emlMin')
    t.eq(t.js(VIEW), 'maximized', 'maximized again')
    t.eq(t.js("document.getElementById('l2').checked"), False, 'the unchecked link still unchecked')
    t.edit_mode()
    t.js("document.getElementById('editbox').value='ed2k://|file|kept.avi|1|0123456789ABCDEF0123456789ABCDEF|/'")
    t.click('#emlMin')
    t.eq(t.js(VIEW), 'minimized', 'edit mode minimized')
    t.click('#emlMin')
    t.eq(t.js("document.getElementById('editbox').value"), 'ed2k://|file|kept.avi|1|0123456789ABCDEF0123456789ABCDEF|/',
         'the edited text kept')
    t.eq(t.errors, [], 'no JavaScript error')


def test_default_view_minimized(t):
    """SF-10.2 and SF-2.12: with the default view Minimized, the popup opens minimized, its top toolbar
    exactly where it is in a maximized popup; Ctrl+Alt+O maximizes it."""
    t.load(settings=EMULE)
    maximized = t.js(BAR + "('emlTop')")
    t.load(settings=dict(EMULE, popupView='minimized'))
    t.eq(t.js(VIEW), 'minimized', 'minimized at load')
    minimized = t.js(BAR + "('emlTop')")
    t.check(all(abs(a[1] - b[1]) < 0.5 for a, b in zip(maximized, minimized)), 'its top toolbar as in a maximized popup',
            (maximized, minimized))
    t.keys('o')
    t.eq(t.js(VIEW), 'maximized', 'Ctrl+Alt+O maximizes it')
    t.eq(t.errors, [], 'no JavaScript error')


def test_check_all_shortcut(t):
    """SF-9: Ctrl+Alt+A checks or unchecks every link, as the box of the top
    toolbar, and sends nothing; nothing in edit mode, where there is no box to check."""
    checked = "[].filter.call(document.querySelectorAll('#divBody input.smallcheck'),function(b){return b.checked;}).length"
    t.load(settings=EMULE)
    t.keys('a')
    t.eq(t.js(checked), 0, 'Ctrl+Alt+A: every link unchecked')
    t.keys('a')
    t.eq(t.js(checked), 9, 'again: every link checked again')
    t.click('#l0')
    t.keys('a')
    t.eq(t.js(checked), 9, 'Ctrl+Alt+A on a mixed box: every link checked')
    t.eq(t.dialogs, [], 'nothing sent: no alert')
    t.edit_mode()
    t.keys('a')
    t.eq(t.js("document.querySelectorAll('#editbox').length"), 1, 'edit mode: nothing changes')
    t.eq(t.errors, [], 'no JavaScript error')


def test_category_lists(t):
    """SF-6.1: the category lists of both toolbars show the same category, chosen in either one."""
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2;Audio=1'))
    t.js("var s=document.getElementById('cat2');s.value='1';s.dispatchEvent(new Event('change'))")
    t.eq([t.js("document.getElementById('cat').value"), t.js("emuleCat.filter(function(c){return c.select==1;})[0].value")],
         ['1', '1'], 'chosen at the bottom: the top list and the category sent follow')
    t.eq(t.errors, [], 'no JavaScript error')


CAT_LISTS = """[].map.call(document.querySelectorAll('#theDiv select.emlCat'),function(s){
  return [s.id, s.disabled, Math.round(s.getBoundingClientRect().width*10)/10, s.title];})"""
LONG_CATEGORY = 'Documentaries and lectures (French)'


def test_category_list_grayed(t):
    """SF-6.4: the category lists are grayed out when the server has fewer than two categories."""
    t.load(settings=dict(EMULE, emuleCat='*default=0'))
    t.eq([c[:2] for c in t.js(CAT_LISTS)], [['cat', True], ['cat2', True]], 'one category: both lists grayed out')
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2'))
    t.eq([c[:2] for c in t.js(CAT_LISTS)], [['cat', False], ['cat2', False]], 'two categories: both lists enabled')
    t.eq(t.errors, [], 'no JavaScript error')


def test_category_list_width(t):
    """SF-6.1: the category lists are 22 characters wide at most (categoryListMaxWidth): a long name does not
    widen the popup, it is cut, and the tooltip of the lists tells the category chosen, whole. They are
    16 characters wide at least (categoryListMinWidth): short names of another server (SF-6.11) move nothing.
    In characters of the lists, their widths follow the size of the text (SF-2.5)."""
    bounds = "(function (s) { return [parseFloat(s.minWidth), parseFloat(s.maxWidth)]; })(getComputedStyle(document.getElementById('cat')))"
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2'))
    least, most = t.js(bounds)
    short = t.js(CAT_LISTS)
    t.check(all(abs(c[2] - least) < 0.5 for c in short), 'short names: 16 characters', [short, least])
    t.eq(t.js('[categoryListMinWidth, categoryListMaxWidth]'), [16, 22], 'parameters of the script, in characters')
    t.load(settings=dict(EMULE, emuleCat='*Default=0;Audio=1;Documents=4;Software=5'))
    medium = t.js(CAT_LISTS)
    t.check(all(least - 0.5 <= c[2] < most for c in medium), 'medium names: between 16 and 22 characters', medium)
    t.check(all(c[3].startswith('Category: default') for c in short), 'the category chosen in the tooltip', short)
    t.load(settings=dict(EMULE, emuleCat=f'*{LONG_CATEGORY}=3;default=0;Video=2'))
    lists = t.js(CAT_LISTS)
    t.check(all(abs(c[2] - most) < 0.5 for c in lists), 'a long name: 22 characters', [lists, most])
    t.check(all(c[3].startswith('Category: ' + LONG_CATEGORY) for c in lists), 'the whole name in the tooltip', lists)
    t.js("var s=document.getElementById('cat');s.value='2';s.dispatchEvent(new Event('change'))")
    t.check(all(c[3].startswith('Category: Video') for c in t.js(CAT_LISTS)), 'another category chosen: the tooltips follow',
            t.js(CAT_LISTS))
    t.eq(t.errors, [], 'no JavaScript error')


def test_show_category_list_setting(t):
    """SF-2.14 and SF-6.10: the category list shown nowhere (Not shown in both toolbars, not in the menu): the toolbars
    have no category list, Download follows the server list, and the links are sent to the default category of the
    server. Shown in the bottom toolbar only: there only, and the category chosen there is sent."""
    none = dict(EMULE, emuleCat='default=0;*Video=2', tbCategoryTop='none', tbCategoryBottom='none')
    t.load(settings=none)
    t.eq(t.js(CAT_LISTS), [], 'no category list')
    top = t.js(BAR + "('emlTop')")
    t.eq([c[0] for c in top][:4], ['checkall', 'emlCount', 'srv', 'emlAdd'], 'top toolbar: Download after the server list')
    t.eq(t.js('getSelectedCat()'), '2', 'the default category of the server is sent')
    t.load(settings=dict(none, tbCategoryBottom='shown'))
    t.eq(t.js("[getComputedStyle(document.getElementById('cat')).display, getComputedStyle(document.getElementById('cat2')).display]"),
         ['none', 'block'], 'shown in the bottom toolbar only')
    t.js("var s=document.getElementById('cat2'); s.value='0'; s.dispatchEvent(new Event('change'))")
    t.eq(t.js('getSelectedCat()'), '0', 'the category chosen in the bottom toolbar is sent')
    t.eq(t.errors, [], 'no JavaScript error')


# [id, server chosen, servers offered, grayed out, width, tooltip] of the server lists of the popup
SRV_LISTS = """[].map.call(document.querySelectorAll('#theDiv select.emlSrv'),function(s){
  return [s.id, s.options[s.selectedIndex].text, [].map.call(s.options,function(o){return o.text;}), s.disabled,
          Math.round(s.getBoundingClientRect().width*10)/10, s.title];})"""
# [server chosen, categories offered, category chosen, grayed out] of the category lists
CAT_CHOICE = """[].map.call(document.querySelectorAll('#theDiv select.emlCat'),function(s){
  return [s.id, [].map.call(s.options,function(o){return o.text;}), s.options[s.selectedIndex].text, s.disabled];})"""
SERVER_TIP = '\nThe server that receives the links, for this page only'


def two_servers(active='srv2', **second):
    """Servers as the settings dialog stores them: an eMule, then an aMule 3.x, the second one checked."""
    first = {'id': 'srv1', 'name': 'eMule PC', 'method': 'emule', 'emuleUrl': 'http://127.0.0.1:4711/',
             'emuleUser': 'admin', 'emulePwd': 'one', 'emuleCat': '*default=0;Video=2'}
    other = dict({'id': 'srv2', 'name': 'aMule NAS', 'method': 'amuleapi', 'emuleUrl': 'http://127.0.0.1:4712/',
                  'emuleUser': 'admin', 'emulePwd': 'two', 'emuleCat': 'Default=0;*Audio=1;Books=3'}, **second)
    return {'active': active, 'list': [first, other]}


def settings_of(servers):
    """The settings that the settings dialog saves with these servers: the ones of the checked server."""
    active = [s for s in servers['list'] if s['id'] == servers['active']]
    if not active:
        return {'ed2kDlMethod': 'local'}
    return dict({k: active[0][k] for k in ('emuleUrl', 'emuleUser', 'emulePwd', 'emuleCat')},
                ed2kDlMethod=active[0]['method'])


def choose_server(t, list_id, name):
    """Choose a server in a server list of the popup, as the user does."""
    t.js(f"var s=document.getElementById('{list_id}'); s.value=[].filter.call(s.options,function(o){{"
         f"return o.text=={name!r};}})[0].value; s.dispatchEvent(new Event('change'))")
    t.pump(0.2)


def test_server_list(t):
    """SF-6.11: a server list in both toolbars, before the category list, when it offers two choices at
    least, Local included: Local, then the servers in the order of the settings; each page starts on the
    server checked in the settings. 22 characters wide at most (serverListMaxWidth, following the size of
    the text), the tooltip tells the server chosen, whole."""
    t.load()
    t.eq(t.js(SRV_LISTS), [], 'Local only: no server list')
    t.load(settings=EMULE)
    t.eq([s[:4] for s in t.js(SRV_LISTS)], [['srv', 'eMule (web)', ['Local', 'eMule (web)'], False],
                                             ['srv2', 'eMule (web)', ['Local', 'eMule (web)'], False]],
         'the settings of the older versions: Local and a server named after its method, chosen')
    servers = two_servers()
    t.load(settings=settings_of(servers), servers=servers)
    lists = t.js(SRV_LISTS)
    t.eq([s[:4] for s in lists], [['srv', 'aMule NAS', ['Local', 'eMule PC', 'aMule NAS'], False],
                                  ['srv2', 'aMule NAS', ['Local', 'eMule PC', 'aMule NAS'], False]],
         'Local, then the servers in the order of the settings, the checked one chosen')
    t.eq([s[5] for s in lists], ['Server: aMule NAS, aMule 3.x (amuleapi)' + SERVER_TIP] * 2, 'tooltip')
    t.check(all(s[4] < 140 for s in lists), 'short names: the lists keep their width', lists)
    t.eq([c[0] for c in t.js(BAR + "('emlTop')")][:5], ['checkall', 'emlCount', 'srv', 'cat', 'emlAdd'],
         'top toolbar: the server list before the category list')
    t.eq([c[0] for c in t.js(BAR + "('emlBottom')")][:7], ['checkall2', 'emlCount', 'emlEdit', 'emlExport', 'srv2', 'cat2', 'emlAdd'],
         'bottom toolbar: the server list before the category list')
    t.eq(t.js("['srv2','cat2'].map(function(id){return document.getElementById(id).classList.contains('emlRight');})"),
         [True, False], 'bottom toolbar: the server list starts the group at the right')
    t.load(settings=dict(EMULE, showCategories=False), servers=None)
    t.eq([c[0] for c in t.js(BAR + "('emlBottom')")][:6], ['checkall2', 'emlCount', 'emlEdit', 'emlExport', 'srv2', 'emlAdd'],
         'no category list: Download follows the server list')
    servers = two_servers(name='The big network attached storage of the attic')
    t.load(settings=settings_of(servers), servers=servers)
    lists = t.js(SRV_LISTS)
    most = t.js("parseFloat(getComputedStyle(document.getElementById('srv')).maxWidth)")
    t.check(all(abs(s[4] - most) < 0.5 for s in lists), 'a long name: 22 characters', [lists, most])
    t.check(all(s[5].startswith('Server: The big network attached storage of the attic,') for s in lists),
            'the whole name in the tooltip', lists)
    t.eq(t.js('serverListMaxWidth'), 22, 'a parameter of the script, in characters')
    t.keys('w')
    t.eq(t.js("[].map.call(document.querySelectorAll('#theDiv select.emlSrv'),function(s){return [s.id, s.getClientRects().length>0];})"),
         [['srv', True], ['srv2', False]], 'minimized: the server list of the top toolbar')
    t.eq(t.errors, [], 'no JavaScript error')


def test_server_list_choice(t):
    """SF-6.13: the server chosen in the popup receives the links of this page only: both lists show it,
    the category lists offer its categories, from its default one, grayed out as for the server of the
    settings; nothing is stored, the next page starts on the server of the settings again."""
    servers = two_servers()
    settings = settings_of(servers)
    t.load(settings=settings, servers=servers)
    t.eq(t.js(CAT_CHOICE), [['cat', ['Default', 'Audio', 'Books'], 'Audio', False],
                            ['cat2', ['Default', 'Audio', 'Books'], 'Audio', False]], 'the categories of aMule NAS')
    choose_server(t, 'srv', 'eMule PC')
    t.eq([s[1] for s in t.js(SRV_LISTS)], ['eMule PC', 'eMule PC'], 'chosen at the top: both lists show it')
    t.eq([s[5] for s in t.js(SRV_LISTS)], ['Server: eMule PC, eMule (web)' + SERVER_TIP] * 2, 'the tooltips follow')
    t.eq(t.js(CAT_CHOICE), [['cat', ['default', 'Video'], 'default', False],
                            ['cat2', ['default', 'Video'], 'default', False]], 'the categories of eMule PC, its default one')
    t.eq(t.js("[ed2kDlMethod, emuleUrl, emulePwd == 'one', getSelectedCat()]"),
         ['emule', 'http://127.0.0.1:4711/', True, '0'], 'its method and its settings used for sending')
    t.eq(t.js("['srv2','cat2'].map(function(id){return document.getElementById(id).classList.contains('emlRight');})"),
         [True, False], 'the category lists keep their place')
    choose_server(t, 'srv2', 'Local')
    t.eq([s[1] for s in t.js(SRV_LISTS)], ['Local', 'Local'], 'chosen at the bottom: both lists show it')
    t.eq([s[5] for s in t.js(SRV_LISTS)], ['Server: Local (your system default)' + SERVER_TIP] * 2, 'tooltip of Local')
    t.eq([c[3] for c in t.js(CAT_CHOICE)], [True, True], 'Local: the category lists grayed out')
    t.eq(t.js('ed2kDlMethod'), 'local', 'Local used for sending')
    choose_server(t, 'srv', 'aMule NAS')
    t.eq(t.js(CAT_CHOICE)[0], ['cat', ['Default', 'Audio', 'Books'], 'Audio', False],
         'back to aMule NAS: its default category again')
    t.eq([t.gm('servers') and json.loads(t.gm('servers')), t.stored_settings()], [servers, settings], 'nothing stored')
    choose_server(t, 'srv', 'eMule PC')
    t.reload()
    t.eq([s[1] for s in t.js(SRV_LISTS)], ['aMule NAS', 'aMule NAS'], 'next page: the server of the settings again')
    t.eq(t.errors, [], 'no JavaScript error')


def test_server_settings_read_late(t):
    """SF-6.12: the list of the servers is read only on a page with ed2k links, where the popup can show it;
    the settings of the servers that are not checked (their password included) are read only when one is
    chosen in the popup, so that they leave the storage only on an action of the user."""
    servers = two_servers()
    t.load('__nolinks', settings=settings_of(servers), servers=servers)
    t.eq(t.js('pageServers.length'), 0, 'a page without ed2k links: the servers not read')
    t.load(settings=settings_of(servers), servers=servers)
    memory = "JSON.stringify(pageServers)"
    t.eq([t.js('pageServers.map(function(s){return s.name;})'), '"one"' in t.js(memory), '"two"' in t.js(memory)],
         [['Local', 'eMule PC', 'aMule NAS'], False, True],
         'a page with links: the servers listed; the password of the checked one only (aMule NAS)')
    choose_server(t, 'srv', 'eMule PC')
    t.eq([t.js("emulePwd == 'one'"), '"one"' in t.js(memory)], [True, True], 'eMule PC chosen: its settings read, used')
    t.eq(t.errors, [], 'no JavaScript error')


def test_show_server_list_setting(t):
    """SF-2.14 and SF-6.15: the server list shown nowhere (Not shown in both toolbars, not in the menu): the toolbars have
    no server list; shown in the top toolbar only: there only."""
    servers = two_servers()
    t.load(settings=dict(settings_of(servers), tbServerTop='none', tbServerBottom='none'), servers=servers)
    t.eq(t.js(SRV_LISTS), [], 'no server list')
    t.eq([c[0] for c in t.js(BAR + "('emlTop')")][:4], ['checkall', 'emlCount', 'cat', 'emlAdd'], 'top toolbar: as before')
    t.load(settings=dict(settings_of(servers), tbServerBottom='none'), servers=servers)
    t.eq(t.js("[getComputedStyle(document.getElementById('srv')).display, getComputedStyle(document.getElementById('srv2')).display]"),
         ['block', 'none'], 'shown in the top toolbar only')
    t.eq(t.errors, [], 'no JavaScript error')


# [title, text, centered in the window, position] of the message shown when the popup is closed, None without it
MSG = """(function(){var m=document.getElementById('emlMsg'); if (!m) return null; var r=m.getBoundingClientRect();
  var w=document.documentElement.clientWidth, h=document.documentElement.clientHeight;
  return [m.querySelector('.emlMsgTitle').textContent, m.querySelector('.emlMsgText').textContent,
          Math.abs(r.left+r.right-w)<2 && Math.abs(r.top+r.bottom-h)<2, getComputedStyle(m).position];})()"""
# the backdrop behind the message: [its color, what a click on the page at its top left would reach], None without it
MSG_BACKDROP = """(function(b){return b ? [getComputedStyle(b).backgroundColor, document.elementFromPoint(5, 5) === b] : null;})
  (document.getElementById('emlMsgBackdrop'))"""


def test_close_message(t):
    """SF-10.4: closing the popup (its Close button, the menu) shows a box inside the page,
    centered in the window, on a backdrop as the settings dialog, so that it cannot be missed: the page
    cannot be clicked behind it. It tells how to open the popup again; OK, its Close button or Escape
    close it, with its backdrop, and so does the popup opened again. Not with Ctrl+Alt+W, which goes through the views, nor at the load of a
    page whose default view is Closed, nor when no popup was open."""
    t.load(settings=EMULE)
    t.eq(t.js(MSG), None, 'no message while the popup is open')
    t.click('#emlClose')
    msg = t.js(MSG)
    t.check(msg is not None, 'the Close button: a message')
    if msg:
        t.eq(msg[0], 'Emule Linker — Popup closed', 'its title, as the one of the settings dialog')
        t.check(all(w in msg[1] for w in ('Ctrl+Alt+O', 'Ctrl+Alt+W', 'Open Popup', 'Tampermonkey', 'Default popup view')),
                'how to open the popup again, the menu of the userscript manager, the next pages', msg[1])
        t.eq(t.js("[].map.call(document.querySelectorAll('#emlMsg .emlMsgText li'), function (li) { return li.textContent; })"),
             ['press Ctrl+Alt+O, or', 'press Ctrl+Alt+W, or', 'choose Open Popup in the menu of Tampermonkey.'],
             'the ways to open it again, as a list')
        t.eq(t.js("(function(a){return a ? [a.textContent, a.href, a.target] : null;})"
                  "(document.querySelector('#emlMsg .emlMsgText a'))"),
             ['installation guide', t.js('REPOSITORY') + '#how-to-install', '_blank'],
             'to keep the popup closed on some sites: the installation guide, in a new tab')
        t.eq(msg[2:], [True, 'fixed'], 'centered in the window')
        t.eq(t.js("getComputedStyle(document.getElementById('emlMsg')).opacity"), '1', 'opaque, as the settings dialog')
    t.eq(t.js(MSG_BACKDROP), ['rgba(0, 0, 0, 0.35)', True], 'on a backdrop, as the settings dialog: the page cannot be clicked')
    t.eq(t.dialogs, [], 'no alert')
    t.click('#emlMsgOk')
    t.eq([t.js(MSG), t.js(MSG_BACKDROP)], [None, None], 'OK: gone, with its backdrop')
    t.keys('o')
    t.close_popup()
    t.check(t.js(MSG) is not None, 'closed again: a message')
    t.press('Escape')
    t.eq([t.js(MSG), t.js(MSG_BACKDROP)], [None, None], 'Escape: gone, with its backdrop')
    t.keys('o')
    t.close_popup()
    t.check(t.js(MSG) is not None, 'closed once more: a message')
    t.click('#emlMsgClose')
    t.eq(t.js(MSG), None, 'its Close button: gone')
    t.keys('o')
    t.close_popup()
    t.keys('o')
    t.eq([t.js(MSG), t.js(MSG_BACKDROP), t.js(VIEW)], [None, None, 'maximized'], 'the popup opened again: the message gone')
    t.close_popup()
    t.close_popup()
    t.eq(t.js("[document.querySelectorAll('#emlMsg').length, document.querySelectorAll('#emlMsgBackdrop').length]"), [1, 1],
         'closed again, the popup closed: one message')
    t.press('Escape')
    t.keys('o')
    t.keys('w')
    t.keys('w')
    t.eq([t.js(MSG), t.js(VIEW)], [None, 'closed'], 'Ctrl+Alt+W: closed, no message')
    t.eq(t.stored_settings().get('closeMessage'), None, 'nothing stored')
    t.load(settings=dict(EMULE, popupScroll='static'))
    t.click('#emlClose')
    t.eq((t.js(MSG) or [None] * 4)[2:], [True, 'fixed'], 'the popup scrolling with the page: the message centered in the window all the same')
    t.load(settings=EMULE, popup_mode=0)
    t.eq(t.js(MSG), None, 'default view Closed: no message at load')
    t.eq(t.errors, [], 'no JavaScript error')


def test_close_message_dont_display(t):
    """SF-10.5: "Don't display again", checked when the message is closed (OK, its Close button or
    Escape), unchecks the setting at once: no message any more, on this page and the next ones; the
    other settings stay as they were."""
    t.load(settings=EMULE)
    t.click('#emlClose')
    t.click('#emlMsgOff')
    t.click('#emlMsgOk')
    t.eq(t.stored_settings(), dict(EMULE, closeMessage=False), 'stored at once, the other settings as they were')
    t.keys('o')
    t.close_popup()
    t.eq(t.js(MSG), None, 'not displayed again on this page')
    t.reload()
    t.click('#emlClose')
    t.eq(t.js(MSG), None, 'nor on the next ones')
    for close in ('#emlMsgClose', 'Escape'):
        t.load(settings=EMULE)
        t.click('#emlClose')
        t.click('#emlMsgOff')
        if close == 'Escape':
            t.press('Escape')
        else:
            t.click(close)
        t.eq([t.js(MSG), t.stored_settings().get('closeMessage')], [None, False], f'{close}: the box checked, stored too')
    t.eq(t.errors, [], 'no JavaScript error')


def test_close_message_setting(t):
    """SF-8.19 and SF-10.4: the setting "Show a message when the popup is closed" of the General section,
    after the default view, checked by default; unchecked, no message; checked again, the message is back."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_closeMessage_field_label').textContent"),
         'Show a message when the popup is closed', 'label')
    t.eq(t.js("[document.getElementById('GM_config_field_closeMessage').type, document.getElementById('GM_config_field_closeMessage').checked]"),
         ['checkbox', True], 'a checkbox, checked by default')
    t.eq(t.js("document.getElementById('GM_config_popupScroll_var').nextElementSibling.id"), 'GM_config_closeMessage_var',
         'in the Popup section, after Popup scrolling')
    help = t.js("document.querySelector('#GM_config_closeMessage_var .help').textContent")
    t.check('✕ button' in help and "Don't display again" in help, 'the help tells when it is shown, and the box of the message', help)
    t.js("document.getElementById('GM_config_field_closeMessage').checked = false")
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js("[document.getElementById('GM_config_field_closeMessage').checked,"
              " document.getElementById('GM_config_closeMessage_var').classList.contains('changed')]"),
         [True, True], 'Reset: checked again, highlighted')
    t.js("document.getElementById('GM_config_field_closeMessage').checked = false")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq(t.stored_settings().get('closeMessage'), False, 'unchecked, saved')
    t.click('#emlClose')
    t.eq(t.js(MSG), None, 'unchecked: no message')
    t.check(t.open_settings(), 'settings dialog opened again')
    t.js("document.getElementById('GM_config_field_closeMessage').checked = true")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.click('#emlClose')
    t.check(t.js(MSG) is not None, 'checked again: the message is back')
    t.eq(t.errors, [], 'no JavaScript error')


# the help box: None without it
HELP = """(function(){var h=document.getElementById('emlHelp'); if (!h) return null; var r=h.getBoundingClientRect();
  return {title: h.querySelector('.emlHelpTitle').textContent, left: r.left, right: r.right, top: r.top, bottom: r.bottom,
          position: getComputedStyle(h).position, width: document.documentElement.clientWidth,
          height: document.documentElement.clientHeight};})()"""
HELP_ROWS = """[].map.call(document.querySelectorAll('#emlHelp .emlHelpRows tr'), function (tr) {
  return [tr.cells[0].querySelector('svg, input, span') != null, tr.cells[2].textContent];})"""


def test_help(t):
    """SF-11: the help built into the script, from the ? button of the top toolbar (between Settings and
    Minimize), Ctrl+Alt+H or the menu: a box inside the page, titled with the version, which draws each
    control of the toolbars with what it does and its shortcut, and links to the documentation and to
    the issues on GitHub, in a new tab. No backdrop: the popup stays usable. OK, its Close button,
    Escape, the ? button or Ctrl+Alt+H again close it. In a window wide enough for the help beside the popup."""
    t.load(settings=EMULE)
    try:
        t.set_viewport(1366, 768)
        help_box(t)
    finally:
        t.clear_viewport()
    t.load('__nolinks', settings=EMULE)
    t.keys('h')
    t.menu('h')
    t.eq(t.js(HELP), None, 'a page without ed2k links: no help')
    t.eq(t.errors, [], 'no JavaScript error')


def help_box(t):
    button = "(function(b){return b ? [b.getAttribute('data-icon'), b.title] : null;})(document.getElementById('emlHelpBtn'))"
    t.eq(t.js(button), ['help', 'Help (Ctrl+Alt+H)'], 'the ? button, its tooltip')
    t.eq(t.js(HELP), None, 'no help at first')
    t.click('#emlHelpBtn')
    help = t.js(HELP)
    t.check(help is not None, 'the ? button: the help')
    if not help:
        return
    t.eq(help['title'], f'Emule Linker {script_version()} — Help', 'its title, with the version')
    t.eq(t.js("getComputedStyle(document.getElementById('emlHelp')).opacity"), '1', 'opaque, as the settings dialog')
    t.eq(t.js(HELP_ROWS), [[True, s] for s in ('Ctrl+Alt+A', '', '', '', 'Ctrl+Alt+D', '', 'Ctrl+Alt+C', 'Ctrl+Alt+S',
                                                 'Ctrl+Alt+H', 'Ctrl+Alt+W', '', '')],
         'each control of the toolbars drawn, with its shortcut, the menu button of a narrow popup last')
    t.eq(t.js("[].map.call(document.querySelectorAll('#emlHelp .emlHelpRows tr'), function (tr) { return tr.cells[0].textContent; }).slice(2, 4)"),
         ['Server ▾', 'Category ▾'], 'the server and category lists drawn with generic names, not those of a user')
    text = t.js("document.getElementById('emlHelp').textContent")
    t.check(all(w in text for w in ('Tampermonkey', 'Links checked by default', 'Default popup view', 'Ctrl+Alt+O')),
            'the list of the links, the next pages, the menu of the userscript manager', text)
    repo = t.js('REPOSITORY')
    t.eq(t.js("['emlHelpDoc','emlHelpIssues'].map(function(id){var a=document.getElementById(id);"
              "return a ? [a.textContent, a.href, a.target] : null;})"),
         [['Full documentation on GitHub', repo, '_blank'], ['Report a problem', repo + '/issues', '_blank']],
         'the documentation and the issues, in a new tab')
    t.eq(t.js("(function(c){var r=c.getBoundingClientRect();return document.elementFromPoint(r.left+r.width/2,r.top+r.height/2)===c;})"
              "(document.getElementById('checkall'))"), True, 'no backdrop: the popup can be clicked')
    t.click('#checkall')
    t.eq(t.js("document.querySelector('#emlTop .emlCount').textContent"), '0/9', 'the popup used, the help open')
    t.check(t.js(HELP) is not None, 'the help still open')
    t.click('#emlHelpBtn')
    t.eq(t.js(HELP), None, 'the ? button again: gone')
    for open_, close, label in (('keys', 'Escape', 'Escape'), ('menu', '#emlHelpOk', 'OK'), ('keys', '#emlHelpClose', 'its Close button'),
                                ('keys', 'keys', 'Ctrl+Alt+H again')):
        if open_ == 'keys':
            t.keys('h')
        else:
            t.menu('h')
        t.check(t.js(HELP) is not None, f'{"Ctrl+Alt+H" if open_ == "keys" else "menu Help"}: the help')
        if close == 'Escape':
            t.press('Escape')
        elif close == 'keys':
            t.keys('h')
        else:
            t.click(close)
        t.eq(t.js(HELP), None, f'{label}: gone')
    t.eq(t.js("document.querySelectorAll('#emlHelp').length"), 0, 'one help at most')


def test_help_position(t):
    """SF-11: the help is centered in the space at the right of the popup, so that both can be read at
    once; when it does not fit there, or without popup, it is centered in the window. It follows the
    window resized, and stays in it."""
    def middle(h):
        return (h['left'] + h['right']) / 2, (h['top'] + h['bottom']) / 2
    t.load(settings=EMULE)
    try:
        t.set_viewport(1366, 768)
        t.keys('h')
        h = t.js(HELP)
        right = t.js("document.getElementById('theDiv').getBoundingClientRect().right")
        t.eq(h['position'], 'fixed', 'fixed in the window')
        x, y = middle(h)
        t.check(h['left'] >= right and abs(x - (right + h['width']) / 2) < 1, 'centered in the space at the right of the popup',
                (h, right))
        t.check(abs(y - h['height'] / 2) < 1, 'centered in height', h)
        t.set_viewport(800, 600)
        t.js("window.dispatchEvent(new Event('resize'))")
        t.pump(0.2)
        h = t.js(HELP)
        x, y = middle(h)
        t.check(abs(x - h['width'] / 2) < 1, 'a narrow window: centered in the window', h)
        t.check(h['top'] >= 0 and h['bottom'] <= h['height'] and h['left'] >= 0 and h['right'] <= h['width'], 'in the window', h)
        t.set_viewport(1366, 768)
        t.keys('h')
        t.close_popup()
        t.press('Escape')
        t.keys('h')
        h = t.js(HELP)
        x, y = middle(h)
        t.check(abs(x - h['width'] / 2) < 1, 'the popup closed: centered in the window', h)
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_help_drag(t):
    """SF-11: the help is moved by dragging its title bar (a "move" cursor on it), within the window; not
    from its Close button, and without selecting text. Its place is kept for the page: closed and opened
    again, it comes back there, and a smaller window only brings it back into it. The next page places
    it automatically again."""
    def place(h):
        return [round(h['left']), round(h['top'])]
    t.load(settings=EMULE)
    try:
        t.set_viewport(1366, 900)
        t.keys('h')
        t.eq(t.js("[getComputedStyle(document.querySelector('#emlHelp .emlHelpHead')).cursor,"
                  " getComputedStyle(document.getElementById('emlHelpClose')).cursor]"), ['move', 'default'],
             'a "move" cursor on the title bar, not on its Close button')
        auto = t.js(HELP)
        t.drag('#emlHelp .emlHelpTitle', -300, 40)
        moved = t.js(HELP)
        t.eq(place(moved), [round(auto['left']) - 300, round(auto['top']) + 40], 'dragged by its title bar')
        t.eq(t.js('window.getSelection().toString()'), '', 'no text selected')
        t.drag('#emlHelpClose', -200, 0)
        t.eq(place(t.js(HELP)), place(moved), 'not from its Close button')
        t.drag('#emlHelp .emlHelpTitle', 3000, 3000)
        h = t.js(HELP)
        t.check(abs(h['right'] - h['width']) < 1 and abs(h['bottom'] - h['height']) < 1, 'within the window: its bottom right corner', h)
        t.drag('#emlHelp .emlHelpTitle', -3000, -3000)
        t.eq(place(t.js(HELP)), [0, 0], 'within the window: its top left corner')
        t.drag('#emlHelp .emlHelpTitle', 150, 20)
        moved = t.js(HELP)
        t.keys('h')
        t.keys('h')
        t.eq(place(t.js(HELP)), place(moved), 'closed and opened again: at the same place')
        t.set_viewport(900, 600)
        t.js("window.dispatchEvent(new Event('resize'))")
        t.pump(0.2)
        h = t.js(HELP)
        t.check(round(h['left']) <= 150 and round(h['top']) == 20 and h['right'] <= h['width'] + 0.5,
                'a smaller window: brought back into it, not centered again', h)
        t.set_viewport(1366, 900)
        t.reload()
        t.keys('h')
        t.eq(place(t.js(HELP)), place(auto), 'the next page: placed automatically again')
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_settings_header_buttons(t):
    """SF-8.3, SF-8.4: the header of the settings dialog holds, at its right, the [?] button of the inline
    help (an icon, pressed while the helps are shown) and a Close button (an icon), which closes the
    dialog as its Close button, without saving; Save stands out, as Download and OK in the popup."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    header = ("[].map.call(document.getElementById('GM_config_header').children, function (e) {"
              "return [e.id || e.className, e.getAttribute('data-icon'), e.title]; })")
    t.eq(t.js(header), [['GM_config_helpBtn', 'help', 'Display inline help'], ['GM_config_closeIcon', 'close', 'Close (Escape)']],
         'at the right of the title: [?], then the Close icon')
    t.eq(t.js("[!!document.querySelector('#GM_config_helpBtn svg'), !!document.querySelector('#GM_config_closeIcon svg'),"
              " getComputedStyle(document.getElementById('GM_config_closeIcon')).color]"), [True, True, 'rgb(208, 0, 0)'],
         'drawn icons, the Close one in red as in the popup')
    edges = ("(function(){var h=document.getElementById('GM_config_header').getBoundingClientRect(),"
             "c=document.getElementById('GM_config_closeIcon').getBoundingClientRect(),"
             "q=document.getElementById('GM_config_helpBtn').getBoundingClientRect();"
             "return [Math.abs((c.top+c.bottom)-(h.top+h.bottom))<1.5, Math.abs((q.top+q.bottom)-(h.top+h.bottom))<1.5, h.right-c.right > 5];})()")  # its 1 px bottom border
    t.eq(t.js(edges), [True, True, True], 'both centered in the header, the Close icon at its right')
    t.eq(t.js("document.getElementById('GM_config_helpBtn').getAttribute('aria-pressed')"), 'false', 'not pressed')
    t.click('#GM_config_helpBtn')
    t.eq(t.js("[document.getElementById('GM_config_helpBtn').getAttribute('aria-pressed'), document.getElementById('GM_config_helpBtn').title]"),
         ['true', 'Hide inline help'], 'the helps shown: pressed, its tooltip')
    t.click('#GM_config_helpBtn')
    save = "(function(s){return [s.borderTopWidth+' '+s.borderTopStyle+' '+s.borderTopColor, s.backgroundColor];})(getComputedStyle(document.getElementById('GM_config_saveBtn')))"
    t.eq(t.js(save), ['2px solid rgb(0, 117, 255)', 'rgb(255, 255, 255)'], 'Save stands out, as Download and OK')
    t.set_field('popupRows', '20')
    t.click('#GM_config_closeIcon')
    t.check(not t.settings_open(), 'the Close icon closes the dialog')
    t.eq(t.stored_settings(), EMULE, 'nothing saved')
    t.eq(t.errors, [], 'no JavaScript error')


# [data-server, the row grayed out, its radio disabled, its links: [text, disabled, title]] of the rows of the servers
LOCAL_ROWS = ("[].map.call(document.querySelectorAll('#GM_config_servers .srow'), function (r) {"
              "return [r.getAttribute('data-server'), r.classList.contains('off'), r.querySelector('input').disabled,"
              "[].map.call(r.querySelectorAll('.acts button'), function (b) { return [b.textContent, b.disabled, b.title]; })]; })")
LINK_COLOR = "(function(b){return b ? getComputedStyle(b).color : null;})(document.querySelector(SEL))"


def two_settings_servers():
    """eMule PC checked, aMule NAS, as stored by the settings dialog."""
    servers = two_servers(active='srv1')
    return settings_of(servers), servers


def test_settings_disable_local(t):
    """SF-8.20: the row of Local has a Disable link, at the place of the Delete links of the servers and in
    their color, once a server is set; it is grayed out while Local is checked (the server that receives
    the links never changes without the user). Disabled, the row of Local is grayed out, its radio button
    too, and its link becomes Enable, in the color of Edit. Saved with the servers; the popup then neither
    offers nor counts Local."""
    t.load()
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(LOCAL_ROWS), [['local', False, False, []]], 'no server: no Disable link')
    settings, servers = two_settings_servers()
    t.load(settings=dict(settings, ed2kDlMethod='local'), servers=dict(servers, active=None))
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(LOCAL_ROWS)[0], ['local', False, False, [['Disable', True, 'Check another server first']]],
         'Local checked: Disable grayed out, its tooltip')
    t.load(settings=settings, servers=servers)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(LOCAL_ROWS)[0], ['local', False, False, [['Disable', False, 'Leave Local out of the servers that receive the links']]],
         'another server checked: Disable')
    t.eq(t.js(LINK_COLOR.replace('SEL', "'#GM_config_server_local .acts button'")), t.js(LINK_COLOR.replace('SEL', "'.srow .acts button.del'")),
         'in the color of Delete')
    t.click('#GM_config_server_local .acts button')
    t.eq(t.js(LOCAL_ROWS)[0], ['local', True, True, [['Enable', False, 'Offer Local again among the servers that receive the links']]],
         'disabled: the row and its radio button grayed out, Enable')
    t.eq(t.js(LINK_COLOR.replace('SEL', "'#GM_config_server_local .acts button'")), t.js(LINK_COLOR.replace('SEL', "'.srow .acts button.edit'")),
         'Enable in the color of Edit')
    t.check(float(t.js("getComputedStyle(document.querySelector('#GM_config_server_local label')).opacity")) < 1, 'the row grayed out')
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq(json.loads(t.gm('servers')).get('localDisabled'), True, 'saved with the servers')
    t.eq([s[2] for s in t.js(SRV_LISTS)], [['eMule PC', 'aMule NAS']] * 2, 'the popup: no Local in the server lists')
    t.load(settings=EMULE, servers={'active': 'srv1', 'list': [dict(two_servers()['list'][0], name='eMule (web)')], 'localDisabled': True})
    t.eq(t.js(SRV_LISTS), [], 'one server left, Local disabled: one choice, no server list')
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_server_local .acts button')
    t.eq(t.js(LOCAL_ROWS)[0][:3], ['local', False, False], 'Enable: Local offered again')
    t.eq(t.errors, [], 'no JavaScript error')


def test_settings_disable_local_delete(t):
    """SF-8.20: Local disabled, deleting the checked server checks the first one left; deleting the last
    server enables Local again, and checks it. Reset enables it too."""
    settings, servers = two_settings_servers()
    t.load(settings=settings, servers=dict(servers, localDisabled=True))
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(LOCAL_ROWS)[0][:2], ['local', True], 'Local disabled')
    t.click('#GM_config_server_srv1 .acts button.del')
    t.eq([[r[0], r[1]] for r in t.js(SERVER_ROWS)], [['local', False], ['srv2', True]],
         'the checked server deleted: the first one left checked, not Local')
    t.click('#GM_config_server_srv2 .acts button.del')
    t.eq(t.js(LOCAL_ROWS), [['local', False, False, []]], 'the last server deleted: Local enabled again')
    t.eq(t.js(SERVER_ROWS)[0][1], True, 'and checked')
    t.close_settings()
    t.load(settings=settings, servers=dict(servers, localDisabled=True))
    t.check(t.open_settings(), 'settings dialog opened')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js(LOCAL_ROWS), [['local', False, False, []]], 'Reset: Local enabled')
    t.eq(t.errors, [], 'no JavaScript error')


# [left, top, right, bottom] gaps between the popup and the window, its position and its resize
CORNER = """(function(){var p=document.getElementById('theDiv'), r=p.getBoundingClientRect(), s=getComputedStyle(p),
  w=document.documentElement.clientWidth, h=document.documentElement.clientHeight;
  return [Math.round(r.left), Math.round(r.top), Math.round(w-r.right), Math.round(h-r.bottom), s.position, s.resize];})()"""
CORNERS = {'top-left': (0, 1), 'top-right': (2, 1), 'bottom-left': (0, 3), 'bottom-right': (2, 3)}


def test_popup_position(t):
    """SF-2.1, SF-2.4: the setting Popup position puts the popup in a corner of the window: top left
    (default, the place of the popup up to 0.13), top right, bottom left or bottom right; an unknown value
    is read as top left. Only at the top left can it be resized: the handle of the browsers is at its
    bottom right, the popup would grow the other way elsewhere. Minimized, it keeps its corner."""
    for corner, (x, y) in CORNERS.items():
        t.load(settings=dict(EMULE, popupCorner=corner))
        c = t.js(CORNER)
        t.eq([c[x], c[y], c[4], c[5]], [0, 0, 'fixed', 'both' if corner == 'top-left' else 'none'],
             f'{corner}: in its corner, resizable at the top left only')
    t.load(settings=EMULE)
    c = t.js(CORNER)
    t.eq([c[0], c[1]], [0, 0], 'by default: top left')
    t.load(settings=dict(EMULE, popupCorner='middle'))
    c = t.js(CORNER)
    t.eq([c[0], c[1]], [0, 0], 'an unknown value: top left')
    t.load(settings=dict(EMULE, popupCorner='bottom-right'))
    t.keys('w')
    c = t.js(CORNER)
    t.eq([c[2], c[3]], [0, 0], 'minimized: in its corner')
    t.load(settings=dict(EMULE, popupCorner='top-right'))
    try:
        t.set_viewport(1366, 768)
        t.keys('h')
        h = t.js(HELP)
        left = t.js("document.getElementById('theDiv').getBoundingClientRect().left")
        t.check(h['right'] <= left and abs((h['left'] + h['right']) / 2 - left / 2) < 1,
                'the popup at the right: the help centered in the space at its left', (h, left))
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_view_arrows(t):
    """SF-2.12: the arrow of the Minimize / Maximize button points to where the popup goes: at the top of
    the window, Minimize ▲ and Maximize ▼; at the bottom, where the popup folds down to its toolbar, Minimize
    ▼ and Maximize ▲. The help draws them in the same order."""
    # the triangle drawn: its point at the top (up) or at the bottom (down)
    way = "function way(e){var d=e.querySelector('path').getAttribute('d');return d=='M1,9.5 L11,9.5 L6,2.5 Z'?'up':d=='M1,2.5 L11,2.5 L6,9.5 Z'?'down':d;}"
    arrow = "(function(b){" + way + "return [b.getAttribute('data-icon'), way(b)];})(document.getElementById('emlMin'))"
    help = "(function(){" + way + "return [].map.call(document.querySelectorAll('#emlHelp .emlChip.min'), way);})()"
    for corner, normal, minimized in (('top-left', 'up', 'down'), ('top-right', 'up', 'down'),
                                      ('bottom-left', 'down', 'up'), ('bottom-right', 'down', 'up')):
        t.load(settings=dict(EMULE, popupCorner=corner))
        t.eq(t.js(arrow), ['minimize', normal], f'{corner}: Minimize {normal}')
        t.keys('h')
        t.eq(t.js(help), [normal, minimized], f'{corner}: the help draws Minimize, then Maximize')
        t.keys('h')
        t.keys('w')
        t.eq(t.js(arrow), ['maximize', minimized], f'{corner}: minimized, Maximize {minimized}')
        t.keys('o')
        t.eq(t.js(arrow), ['minimize', normal], f'{corner}: maximized again, Minimize {normal}')
    t.eq(t.errors, [], 'no JavaScript error')


def test_popup_scrolling(t):
    """SF-2.2: the setting Popup scrolling: floating (default), the popup stays in view when the page
    scrolls; static, it scrolls with the page, from its corner at the load of the page. At the bottom of
    the window, it always stays in view. An unknown value is read as floating."""
    t.load(settings=EMULE)
    t.js('window.scrollTo(0, 300)')
    t.pump(0.2)
    c = t.js(CORNER)
    t.eq([c[1], c[4]], [0, 'fixed'], 'floating by default: in view when the page scrolls')
    t.load(settings=dict(EMULE, popupScroll='static'))
    t.js('window.scrollTo(0, 300)')
    t.pump(0.2)
    c = t.js(CORNER)
    t.eq([c[1], c[4]], [-300, 'absolute'], 'static: scrolls with the page')
    t.load(settings=dict(EMULE, popupScroll='static', popupCorner='bottom-left'))
    c = t.js(CORNER)
    t.eq([c[0], c[3], c[4]], [0, 0, 'fixed'], 'static at the bottom left: stays in view all the same')
    t.load(settings=dict(EMULE, popupScroll='sideways'))
    t.eq(t.js(CORNER)[4], 'fixed', 'an unknown value: floating')
    t.eq(t.errors, [], 'no JavaScript error')


def test_popup_position_migration(t):
    """SF-8.7: the setting Popup Position of 0.13 (popupPos) becomes Popup scrolling: absolute is static,
    fixed is floating, stored once; Popup position is then top left, the place of the popup up to 0.13.
    Without a stored popupPos, nothing is stored."""
    for old, new, position in (('absolute', 'static', 'absolute'), ('fixed', 'floating', 'fixed')):
        t.load(settings=dict(EMULE, popupPos=old))
        c = t.js(CORNER)
        t.eq([c[0], c[1], c[4]], [0, 0, position], f'popupPos {old}: at the top left, {position}')
        t.eq(t.stored_settings().get('popupScroll'), new, f'popupPos {old}: Popup scrolling {new}, stored')
        t.check(t.open_settings(), 'settings dialog opened')
        t.eq(t.js("[document.getElementById('GM_config_field_popupCorner').value, document.getElementById('GM_config_field_popupScroll').value,"
                  " !!document.getElementById('GM_config_popupPos_var')]"), ['top-left', new, False],
             f'popupPos {old}: shown in the dialog, the former field gone')
    t.load(settings=EMULE)
    t.eq('popupScroll' in t.stored_settings(), False, 'no popupPos: nothing stored')
    t.eq(t.errors, [], 'no JavaScript error')


def test_popup_position_settings(t):
    """SF-8: the settings Popup position and Popup scrolling, in the Popup section, in place of Popup
    Position; Reset sets them back to their default, highlighted; Save stores them. At the bottom of the
    window, Popup scrolling is Stays in view, grayed out."""
    t.load(settings=dict(EMULE, popupCorner='top-right', popupScroll='static'))
    t.check(t.open_settings(), 'settings dialog opened')
    field = ("(function(id){var r=document.getElementById('GM_config_'+id+'_var');"
             "return [r.querySelector('label').textContent, [].map.call(r.querySelectorAll('option'), function(o){return o.value+'='+o.text;}),"
             " r.closest('.section_header_holder').querySelector('.section_header').textContent];})")
    t.eq(t.js(field + "('popupCorner')"), ['Popup position', ['top-left=Top left (default)', 'top-right=Top right',
                                                             'bottom-left=Bottom left', 'bottom-right=Bottom right'], 'Popup'],
         'Popup position: a list of the corners, in the Popup section')
    t.eq(t.js(field + "('popupScroll')"), ['Popup scrolling', ['floating=Stays in view (default)', 'static=Scrolls with the page'], 'Popup'],
         'Popup scrolling: floating or static')
    t.eq(t.js("document.getElementById('GM_config_popupCorner_var').previousElementSibling.id"), 'GM_config_section2_var',
         'first in the Popup section')
    t.eq(t.js("document.getElementById('GM_config_popupCorner_var').nextElementSibling.id"), 'GM_config_popupScroll_var',
         'Popup scrolling after Popup position')
    help = t.js("document.querySelector('#GM_config_popupCorner_var .help').textContent")
    t.check('top left' in help and 'resized' in help, 'the help of Popup position tells where it can be resized', help)
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js("['popupCorner','popupScroll'].map(function(id){return [document.getElementById('GM_config_field_'+id).value,"
              " document.getElementById('GM_config_'+id+'_var').classList.contains('changed')];})"),
         [['top-left', True], ['floating', True]], 'Reset: the defaults, highlighted')
    t.js("var s=document.getElementById('GM_config_field_popupCorner'); s.value='top-right'")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq([t.stored_settings().get('popupCorner'), t.stored_settings().get('popupScroll')], ['top-right', 'floating'], 'saved')
    c = t.js(CORNER)
    t.eq([c[1], c[2]], [0, 0], 'the page reloaded: the popup at the top right')
    scroll = ("[document.getElementById('GM_config_field_popupScroll').value,"
              " document.getElementById('GM_config_field_popupScroll').disabled]")
    corner = "var s=document.getElementById('GM_config_field_popupCorner'); s.value=%r; s.dispatchEvent(new Event('change'))"
    t.load(settings=dict(EMULE, popupCorner='bottom-left', popupScroll='static'))
    t.eq(t.js(CORNER)[4], 'fixed', 'stored static at the bottom left: stays in view')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(scroll), ['floating', True], 'at the bottom: Stays in view, grayed out')
    help = t.js("document.querySelector('#GM_config_popupScroll_var .help').textContent")
    t.check('bottom' in help and 'grayed out' in help, 'its help tells why', help)
    t.js(corner % 'top-left')
    t.eq(t.js(scroll), ['floating', False], 'at the top: it can be chosen again')
    t.js("document.getElementById('GM_config_field_popupScroll').value='static'")
    t.js(corner % 'bottom-right')
    t.eq(t.js(scroll), ['floating', True], 'at the bottom again: Stays in view, grayed out')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js(scroll), ['floating', False], 'Reset: at the top left, it can be chosen')
    t.js("document.getElementById('GM_config_undoBtn').click()")
    t.eq(t.js(scroll), ['floating', True], 'Undo: at the bottom right again, grayed out')
    t.eq(t.errors, [], 'no JavaScript error')


# the labels and the tooltips of the toolbars, of the help, of the message and of the settings dialog
TEXTS_SHOWN = """(function(){var q=function(s){return document.querySelector(s);};
  return {download: q('#emlTop .emlAdd').innerHTML, downloadTitle: q('#emlTop .emlAdd').title,
          edit: q('#emlEdit').innerHTML, close: q('#emlClose').title};})()"""


def test_language_setting(t):
    """SF-12 and SF-8.19: the setting Language, first in the General section: Browser language (default),
    English, Français, each language named in its own language; Reset sets it back to Browser language."""
    t.load(settings=dict(EMULE, language='fr'))
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("[].filter.call(document.querySelectorAll('#GM_config_section_0 .config_var'), function(e){return e.id != 'GM_config_section0_var';})[0].id"), 'GM_config_language_var', 'first in General')
    t.eq(t.js("[].map.call(document.querySelectorAll('#GM_config_field_language option'), function(o){return o.value+'='+o.text;})"),
         ['browser=Langue du navigateur (par défaut)', 'en=English', 'fr=Français'], 'its choices, in French as chosen')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js("[document.getElementById('GM_config_field_language').value,"
              " document.getElementById('GM_config_language_var').classList.contains('changed')]"),
         ['browser', True], 'Reset: Browser language, highlighted')
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("[document.getElementById('GM_config_language_field_label').textContent, document.getElementById('GM_config_field_language').value]"),
         ['Language', 'browser'], 'by default: Browser language')
    help = t.js("document.querySelector('#GM_config_language_var .help').textContent")
    t.check('French' in help and 'English' in help, 'its help tells which language the browser gives', help)
    t.eq(t.errors, [], 'no JavaScript error')


def test_language_french(t):
    """SF-12: in French, the toolbars, their tooltips, the help, the message of the closed popup and the
    settings dialog; the letter of a shortcut underlined only when the label holds it."""
    t.load(settings=EMULE, language='fr-FR')
    shown = t.js(TEXTS_SHOWN)
    t.eq(shown, {'download': 'Télécharger', 'downloadTitle': 'Télécharger les liens cochés (Ctrl+Alt+D)',
                 'edit': 'Mode édition', 'close': 'Fermer'},
         'the toolbars in French; Télécharger has no D: nothing underlined')
    t.keys('h')
    t.eq(t.js("document.querySelector('#emlHelp .emlHelpTitle').textContent"), f'Emule Linker {script_version()} — Aide', 'the help')
    t.eq(t.js("document.querySelector('#emlHelp h4').textContent"), 'Les barres d\'outils', 'its content')
    t.keys('h')
    t.click('#emlClose')
    t.eq(t.js("document.querySelector('#emlMsg .emlMsgTitle').textContent"), 'Emule Linker — Popup fermée', 'the message')
    t.eq(t.js("document.querySelector('#emlMsg label').textContent"), 'Ne plus afficher', 'its box')
    t.press('Escape')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("[document.getElementById('GM_config_header').firstChild.textContent,"
              " document.getElementById('GM_config_saveBtn').textContent, document.getElementById('GM_config_closeBtn').textContent,"
              " document.querySelector('#GM_config_section_header_0').textContent, document.getElementById('GM_config_emuleUrl_field_label').textContent]"),
         [f'Emule Linker {script_version()} — Réglages', 'Enregistrer', 'Fermer', 'Général', 'Adresse du serveur'],
         'the settings dialog, the buttons of GM_config included')
    t.eq(t.errors, [], 'no JavaScript error')


def test_language_choice(t):
    """SF-12: the setting Language wins over the language of the browser; Browser language gives French
    for a browser in French, English for any other language; an unknown stored value is read as Browser
    language (SF-12.2)."""
    for browser, setting, expected in (('fr-FR', 'en', '<u>D</u>ownload'), ('en-US', 'fr', 'Télécharger'),
                                       ('fr', 'browser', 'Télécharger'), ('de-DE', 'browser', '<u>D</u>ownload'),
                                       ('fr-CA', None, 'Télécharger'), ('fr-FR', 'xx', 'Télécharger'),
                                       ('en-US', 'xx', '<u>D</u>ownload')):
        settings = dict(EMULE, **({'language': setting} if setting else {}))
        t.load(settings=settings, language=browser)
        t.eq(t.js(TEXTS_SHOWN)['download'], expected, f'browser {browser}, setting {setting}')
    t.eq(t.errors, [], 'no JavaScript error')


TEXTS_CHECK = r"""(function(){var en=TEXTS.en, fr=TEXTS.fr, keys=function(o){return Object.keys(o).sort();},
  names=function(s){return (s.match(/\{\w+\}/g)||[]).sort().join(',');};
  return {missing: keys(en).filter(function(k){return !(k in fr) && !/^theme\.(?!auto$)/.test(k);}), extra: keys(fr).filter(function(k){return !(k in en);}),
          values: keys(en).filter(function(k){return k in fr && names(en[k]) != names(fr[k]);}),
          marks: keys(en).concat(keys(fr)).filter(function(k){return ((en[k]||'')+'').split('&').length > 2 || ((fr[k]||'')+'').split('&').length > 2;})};})()"""


def test_texts_complete(t):
    """SF-12: every text has its French version, with the same values {name}, except the name of a theme, whose
    French version is optional (SF-13.5); a label marks at most one letter of shortcut (&)."""
    t.load()
    t.eq(t.js(TEXTS_CHECK), {'missing': [], 'extra': [], 'values': [], 'marks': []}, 'the tables complete and consistent')
    t.eq(t.errors, [], 'no JavaScript error')


def test_control_colors(t):
    """SF-2.5: the buttons and the lists of the toolbars are white, with a gray border, whatever the page and
    the browser (a page may give its own colors to the buttons and lists, and the defaults of Chrome and
    Firefox differ); light gray when grayed out; Download keeps its blue border."""
    t.serve('/__gray', '<!doctype html><meta charset="utf-8"><title>gray</title>'
            '<style>button, select { background-color: #d0d0d0; border: 3px dashed #ff0000; color: #333; }</style>'
            '<a href="ed2k://|file|one.cbz|1048576|ABCDEF1234567890ABCDEF1234567890|/">one</a>')
    t.load('__gray', settings=dict(EMULE, emuleCat='*default=0'))
    look = ("[].map.call(document.querySelectorAll('#emlTop select, #emlTop button, #emlBottom select, #emlBottom button'),"
            "function(e){var s=getComputedStyle(e);return [e.id||e.className, s.backgroundColor, s.borderTopWidth+' '+s.borderTopStyle+' '+s.borderTopColor, e.disabled];})")
    for name, background, border, disabled in t.js(look):
        if 'emlAdd' in name:
            t.eq([background, border], ['rgb(255, 255, 255)', '2px solid rgb(0, 117, 255)'], f'{name}: Download, its blue border')
        elif disabled:
            t.eq([background, border], ['rgb(245, 245, 245)', '1px solid rgb(200, 200, 200)'], f'{name}: grayed out, light gray')
        else:
            t.eq([background, border], ['rgb(255, 255, 255)', '1px solid rgb(143, 143, 157)'], f'{name}: white, a gray border')
    t.eq(t.errors, [], 'no JavaScript error')


def test_colors_in_css(t):
    """SF-2.5, SF-7.10, SF-8.1: every color of the popup, of the band of the answers and of the backdrop of
    the settings dialog comes from the CSS of the PARAM block, where the themes change them (SF-13): none
    is set inline by the code. The look is unchanged: the popup white, its text black, its steel blue frame
    of 2 px, 0.97 opaque; the answers in gray, orange, green or red; the page dimmed behind the dialog."""
    t.load(settings=EMULE)
    style = t.js("document.getElementById('theDiv').getAttribute('style')")
    for name in ('background', 'color', 'border', 'opacity'):
        t.check(name not in style, f'popup: no {name} inline', style)
    t.eq(t.js("(function(s){return [s.backgroundColor, s.color, s.borderTopWidth+' '+s.borderTopStyle+' '+s.borderTopColor,"
              " s.opacity];})(getComputedStyle(document.getElementById('theDiv')))"),
         ['rgb(255, 255, 255)', 'rgb(0, 0, 0)', '2px solid rgb(43, 92, 138)', '0.97'], 'popup: its look')
    band = "document.getElementById('emlStatus')"
    for ok, color in (('null', 'rgb(85, 85, 85)'), ("'doubt'", 'rgb(166, 95, 0)'), ('true', 'rgb(0, 102, 0)'), ('false', 'rgb(204, 0, 0)')):
        t.js(f"showStatus('answer', {ok})")
        t.eq([t.js(f'{band}.style.color'), t.js(f'getComputedStyle({band}).color')], ['', color], f'answer ({ok}): its color from the CSS')
    t.open_settings()
    backdrop = "document.getElementById('GM_config_backdrop')"
    t.eq([t.js(f'{backdrop}.style.background'), t.js(f'getComputedStyle({backdrop}).backgroundColor')], ['', 'rgba(0, 0, 0, 0.35)'],
         'backdrop of the settings dialog: its color from the CSS')
    t.eq(t.errors, [], 'no JavaScript error')


THEME_LOOK = """(function(){var s=getComputedStyle(document.getElementById('theDiv'));
  return [s.backgroundColor, s.color, s.colorScheme];})()"""
LIGHT_LOOK = ['rgb(255, 255, 255)', 'rgb(0, 0, 0)', 'light']
WIN11_LOOK = ['rgb(32, 32, 32)', 'rgb(230, 230, 230)', 'dark']
SHIPPED_THEMES = [['light', 'Default light'], ['macos', 'macOS'], ['firefox', 'Firefox light'], ['mono', 'Monochrome light'],
                  ['glass', 'Transparent glass'], ['legacy', 'Legacy'], ['win11', 'Windows 11 dark'], ['chrome', 'Chrome dark'],
                  ['steel', 'Steel blue night'], ['oled', 'OLED black']]
THEME_OPTIONS = "[].map.call(document.querySelectorAll('#GM_config_field_theme option'), function(o){ return [o.value, o.textContent]; })"


def test_theme_setting(t):
    """SF-13: the setting Theme of the General section, after Language: Automatic (default), then every theme of
    the table THEMES, in its order, each one named in English (the ten themes of the script at least);
    Reset puts Automatic back. A theme stored by mistake is read as Automatic."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_language_var').nextElementSibling.id"), 'GM_config_theme_var', 'after Language')
    t.eq(t.js("document.getElementById('GM_config_theme_field_label').textContent"), 'Theme', 'label')
    names = t.js("Object.keys(THEMES)")
    options = t.js(THEME_OPTIONS)
    t.eq(options, [['auto', 'Automatic (default)']] + [[n, t.js(f"TEXTS.en['theme.{n}']")] for n in names],
         'Automatic, then every theme of THEMES, in its order')
    t.eq([x for x in options if x in SHIPPED_THEMES], SHIPPED_THEMES, 'the six light themes, then the four dark ones')
    t.eq([n for n in names if not t.js(f"TEXTS.en['theme.{n}']")], [], 'every theme named in English')
    t.eq(t.js("document.getElementById('GM_config_field_theme').value"), 'auto', 'Automatic by default')
    help = t.js("document.querySelector('#GM_config_theme_var .help').textContent")
    t.check('Windows 11 dark' in help and 'dark mode' in help, 'the help tells what Automatic takes', help)
    t.js("document.getElementById('GM_config_field_theme').value = 'oled'")
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js("[document.getElementById('GM_config_field_theme').value,"
              " document.getElementById('GM_config_theme_var').classList.contains('changed')]"), ['auto', True], 'Reset: Automatic back')
    t.load(settings=dict(EMULE, theme='purple'), dark=True)
    t.eq(t.js(THEME_LOOK), WIN11_LOOK, 'an unknown theme read as Automatic')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_added(t):
    """SF-13.5: a theme added to the table THEMES, and named in the texts, is offered by the setting Theme with
    nothing else to change, after the others (the options of the field, made when the script starts, are asked
    again of themeOptions()); chosen, it colors the popup."""
    t.load(settings=EMULE)
    t.js("THEMES.sepia = Object.assign({}, THEMES.light, { bg: '#f4ecd8' });"
         " TEXTS.en['theme.sepia'] = 'Sepia'; TEXTS.fr['theme.sepia'] = 'Sépia'; 0")
    options = t.js("typeof themeOptions == 'function' ? Object.entries(themeOptions()) : null")
    t.eq(options and options[-1], ['sepia', 'Sepia'], 'the new theme offered, last')
    t.js("theme = 'sepia'; applyTheme(); 0")
    t.eq(t.js("getComputedStyle(document.getElementById('theDiv')).backgroundColor"), 'rgb(244, 236, 216)', 'chosen, it colors the popup')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_untranslated(t):
    """SF-13.5: a theme named in English only is offered in French under its English name; the test of the
    texts accepts it, but not another text missing in French."""
    t.load(settings=dict(EMULE, language='fr'))
    t.js("THEMES.sepia = THEMES.light; TEXTS.en['theme.sepia'] = 'Sepia'; 0")
    t.eq(t.js("Object.entries(themeOptions()).slice(-1)[0]"), ['sepia', 'Sepia'], 'offered in French under its English name')
    t.eq(t.js("Object.entries(themeOptions())[0]"), ['auto', 'Automatique (par défaut)'], 'the other names in French')
    t.eq(t.js(TEXTS_CHECK)['missing'], [], 'the test of the texts accepts it')
    t.js("TEXTS.en.untranslated = 'Untranslated'; 0")
    t.eq(t.js(TEXTS_CHECK)['missing'], ['untranslated'], 'but not another text missing in French')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_help_link(t):
    """SF-13.1, SF-8.3: the help of the setting Theme links to the section Usage of the README, which shows every
    theme, in a new tab, in English and in French; the color of the link is the one of the links of the theme."""
    link = ("(function (a) { return a && [a.textContent, a.href, a.target, a.rel]; })"
            "(document.querySelector('#GM_config_theme_var .help a'))")
    for language, before in (('en', 'Every theme is shown in the '), ('fr', 'Tous les thèmes sont montrés dans le ')):
        t.load(settings=dict(EMULE, language=language))
        t.check(t.open_settings(), f'{language}: settings dialog opened')
        t.eq(t.js(link), ['README', t.js('REPOSITORY') + '#usage', '_blank', 'noopener'], f'{language}: the link to the README, in a new tab')
        help = t.js("document.querySelector('#GM_config_theme_var .help').textContent")
        t.check(help.endswith(before + 'README.'), f'{language}: its sentence, without the address', help)
    t.eq(style(t, '#GM_config_theme_var .help a', 'color'), ['rgb(0, 117, 255)'], 'the color of the links of Default light')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_automatic(t):
    """SF-13: Automatic is the light theme, or Windows 11 dark when Windows or the browser is in dark mode, at the load
    of the page, and at once when the mode changes, the page open."""
    t.load(settings=EMULE)
    t.eq(t.js(THEME_LOOK), LIGHT_LOOK, 'light mode: the light theme')
    t.set_dark(True)
    t.eq(t.js(THEME_LOOK), WIN11_LOOK, 'dark mode: Windows 11 dark, at once')
    t.set_dark(False)
    t.eq(t.js(THEME_LOOK), LIGHT_LOOK, 'light mode again: the light theme, at once')
    t.load(settings=EMULE, dark=True)
    t.eq(t.js(THEME_LOOK), WIN11_LOOK, 'dark mode at the load of the page: Windows 11 dark')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_fixed(t):
    """SF-13: a theme chosen in the settings stays whatever the mode of the system. Its colors reach every
    screen of the script, the popup, its band, its message, its help and the settings dialog, and never the page."""
    for name, background in (('light', 'rgb(255, 255, 255)'), ('win11', 'rgb(32, 32, 32)'), ('chrome', 'rgb(32, 33, 36)'),
                             ('steel', 'rgb(23, 32, 43)'), ('oled', 'rgb(0, 0, 0)')):
        for dark in (False, True):
            t.load(settings=dict(EMULE, theme=name), dark=dark)
            t.eq(t.js(THEME_LOOK)[0], background, f'{name}, {"dark" if dark else "light"} mode: its background')
    t.load(settings=dict(EMULE, theme='win11'))
    page = "[getComputedStyle(document.body).backgroundColor, getComputedStyle(document.documentElement).getPropertyValue('--eml-bg')]"
    t.eq(t.js(page)[1], '', 'the page: no variable of the theme')
    t.js("showStatus('answer', true)")
    t.eq(t.js("getComputedStyle(document.getElementById('emlStatus')).backgroundColor"), 'rgb(29, 58, 38)', 'the band of the answers')
    t.click('#emlHelpBtn')
    t.eq(t.js("getComputedStyle(document.getElementById('emlHelp')).backgroundColor"), 'rgb(32, 32, 32)', 'the help')
    t.press('Escape')
    t.click('#emlClose')
    t.eq(t.js("getComputedStyle(document.getElementById('emlMsg')).backgroundColor"), 'rgb(32, 32, 32)', 'the message of the closed popup')
    t.press('Escape')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("[getComputedStyle(document.getElementById('GM_config')).backgroundColor,"
              " getComputedStyle(document.getElementById('GM_config')).colorScheme]"), ['rgb(32, 32, 32)', 'dark'], 'the settings dialog')
    t.eq(t.errors, [], 'no JavaScript error')


FIRST_FONT = "(function(e){return e ? getComputedStyle(e).fontFamily.split(',')[0].replace(/[\"']/g, '').trim() : null;})"


def test_theme_font(t):
    """SF-13.3: the screens of the script have the font of their theme, never the one of the page: a page that
    gives its own font to every element changes neither the popup, its buttons, its list, its band, its help,
    its message nor the settings dialog; the edit box and the filter keep a monospace font."""
    t.serve('/__font', '<!doctype html><meta charset="utf-8"><title>font</title>'
            '<style>body, div, span, a, td, button, select, label, input, textarea, b, li { font-family: "Comic Sans MS", cursive; }</style>'
            '<a href="ed2k://|file|one.cbz|1048576|ABCDEF1234567890ABCDEF1234567890|/">one</a>'
            '<a href="ed2k://|file|two.cbz|2048576|BBCDEF1234567890ABCDEF1234567890|/">two</a>')
    for name, font in (('light', 'Segoe UI'), ('win11', 'Segoe UI Variable Text'), ('chrome', 'system-ui')):
        t.load('__font', settings=dict(EMULE, theme=name))
        for selector in ('#theDiv', '#emlTop .emlAdd', '#emlTop select', '#divBody a', '#emlTop .emlCount'):
            t.eq(t.js(f"{FIRST_FONT}(document.querySelector('{selector}'))"), font, f'{name}: {selector}')
        t.js("showStatus('answer', true)")
        t.eq(t.js(f"{FIRST_FONT}(document.querySelector('#emlStatus .emlStatusText'))"), font, f'{name}: the band of the answers')
    t.load('__font', settings=dict(EMULE, theme='light'))
    t.click('#emlHelpBtn')
    t.eq(t.js(f"{FIRST_FONT}(document.querySelector('#emlHelp td:nth-child(2)'))"), 'Segoe UI', 'the help')
    t.press('Escape')
    t.click('#emlClose')
    t.eq(t.js(f"{FIRST_FONT}(document.querySelector('#emlMsg .emlMsgText'))"), 'Segoe UI', 'the message of the closed popup')
    t.press('Escape')
    t.keys('o')
    t.edit_mode()
    t.eq(t.js(f"{FIRST_FONT}(document.querySelector('#theDiv textarea'))"), 'Consolas', 'the edit box: monospace')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(f"{FIRST_FONT}(document.querySelector('#GM_config .field_label'))"), 'Segoe UI', 'the settings dialog')
    t.eq(t.js(f"{FIRST_FONT}(document.getElementById('GM_config_field_checkFilter'))"), 'Consolas', 'the filter: monospace')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_shape_icons(t):
    """SF-13.3: the radius of the buttons and lists of the theme (3 px, 4 px for Windows 11 dark, a pill for Chrome
    dark, square for OLED black), and its set of icons, solid or outline; Automatic draws the icons already shown
    again in the set of the theme it takes when the mode changes."""
    radius = "getComputedStyle(document.querySelector('#emlTop .emlAdd')).borderTopLeftRadius"
    fill = "document.querySelector('#emlTop [data-icon=settings] svg path').getAttribute('fill')"
    for name, expected, icons in (('light', '3px', 'currentColor'), ('win11', '4px', 'none'), ('chrome', '11px', 'none'),
                                  ('steel', '3px', 'currentColor'), ('oled', '0px', 'currentColor')):
        t.load(settings=dict(EMULE, theme=name))
        t.eq([t.js(radius), t.js(fill)], [expected, icons], f'{name}: its radius and its icons')
    t.load(settings=EMULE)
    t.eq(t.js(fill), 'currentColor', 'Automatic, light mode: solid icons')
    t.set_dark(True)
    t.eq([t.js(fill), t.js("document.querySelectorAll('#theDiv svg[data-eml-icon]').length >= 4")], ['none', True],
         'dark mode: the icons of the popup drawn again, outline')
    t.eq(t.js("document.getElementById('emlMin').getAttribute('data-icon')"), 'minimize', 'the buttons keep their name')
    t.set_dark(False)
    t.eq(t.js(fill), 'currentColor', 'light mode again: solid icons')
    t.eq(t.errors, [], 'no JavaScript error')


STYLE = """(function (sel, props) { var e = document.querySelector(sel); if (!e) { return null; }
  var s = getComputedStyle(e); return props.map(function (p) { return s.getPropertyValue(p); }); })"""


# the optional values of a theme (SF-13.4), and a theme without them: OLED black, its optional values removed
OPTIONAL_VALUES = ['frameRadius', 'opacity', 'blur', 'editBg', 'editText', 'iconBtnBg', 'iconBtnLine', 'iconBtnRadius', 'iconBtnSize',
                   'iconBtnHover', 'iconBtnActive', 'iconSize', 'minColor', 'maxColor', 'closeColor', 'closeHoverBg', 'closeActiveBg',
                   'closeHoverColor', 'glyph', 'primaryLine', 'primaryBorder', 'primaryHoverText', 'primaryActive', 'primaryActiveRing',
                   'ctlActive', 'ctlHoverLine', 'ctlActiveLine']
PLAIN = (f"THEMES.plain = Object.assign({{}}, THEMES.oled); {json.dumps(OPTIONAL_VALUES)}.forEach(function (k) {{ delete THEMES.plain[k]; }});"
         " theme = 'plain'; applyTheme(); 0")


def style(t, selector, *props):
    """The computed values of CSS properties of an element (None when it is missing)."""
    return t.js(f"{STYLE}({json.dumps(selector)}, {json.dumps(list(props))})")


def test_theme_frames(t):
    """SF-13.4: the optional values of the frames: a theme without them keeps square frames, the popup at 97 %, no
    blur, the edit box and the fields of the settings in the colors of the fields of the browser; Default light keeps
    them white and rounds every frame by 4 px as the settings; Windows 11 dark gives the edit box and the fields of
    the settings the gray of its toolbars; Transparent glass makes the popup more transparent (92 %), blurs the page
    behind it, rounds every frame by 4 px and gives the edit box a translucent background; macOS rounds them by 12 px.
    The band of an answer floating against the popup, minimized or closed, is rounded as the frames."""
    look = ('opacity', 'border-top-left-radius', 'backdrop-filter')
    t.load(settings=EMULE)
    t.js(PLAIN)
    t.eq(style(t, '#theDiv', *look), ['0.97', '0px', 'none'], 'a theme without these values: the popup')
    t.edit_mode()
    field = ("(function () { var d = document.createElement('div'); d.style.backgroundColor = 'Field';"
             " document.getElementById('theDiv').appendChild(d); var c = getComputedStyle(d).backgroundColor; d.remove(); return c; })()")
    t.eq(style(t, '#theDiv textarea', 'background-color'), [t.js(field)],
         'a theme without these values: the edit box in the color of the fields of the browser (dark)')
    t.load(settings=dict(EMULE, theme='win11'))
    t.edit_mode()
    t.eq(style(t, '#theDiv textarea', 'background-color', 'color'), ['rgb(43, 43, 43)', 'rgb(230, 230, 230)'], 'Windows 11 dark: the edit box')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(style(t, '#GM_config_field_emuleUrl', 'background-color', 'color'), ['rgb(43, 43, 43)', 'rgb(230, 230, 230)'],
         'Windows 11 dark: the fields of the settings as the edit box')
    t.load(settings=dict(EMULE, theme='light'))
    t.eq(style(t, '#theDiv', *look), ['0.97', '4px', 'none'], 'Default light: the popup rounded by 4 px')
    t.edit_mode()
    t.eq(style(t, '#theDiv textarea', 'background-color', 'color'), ['rgb(255, 255, 255)', 'rgb(0, 0, 0)'], 'Default light: the edit box')
    t.load(settings=dict(EMULE, theme='glass'))
    popup = style(t, '#theDiv', *look)
    t.eq(popup[:2], ['0.92', '4px'], 'Transparent glass: the popup more transparent, rounded')
    t.check(popup[2].startswith('blur(18px)'), 'Transparent glass: the page blurred behind the popup', popup[2])
    t.edit_mode()
    t.eq(style(t, '#theDiv textarea', 'background-color', 'color'), ['rgba(255, 255, 255, 0.8)', 'rgb(16, 16, 16)'],
         'Transparent glass: the edit box translucent')
    t.load(settings=dict(EMULE, theme='glass'))
    t.click('#emlHelpBtn')
    t.eq(style(t, '#emlHelp', 'border-top-left-radius'), ['4px'], 'Transparent glass: the help rounded')
    t.press('Escape')
    t.click('#emlClose')
    t.eq(style(t, '#emlMsg', 'border-top-left-radius'), ['4px'], 'Transparent glass: the message rounded')
    t.press('Escape')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(style(t, '#GM_config', 'border-top-left-radius'), ['4px'], 'Transparent glass: the settings rounded as before')
    t.load(settings=dict(EMULE, theme='macos'))
    t.eq(style(t, '#theDiv', 'border-top-left-radius'), ['12px'], 'macOS: the popup rounded by 12 px')
    for name, radius in (('plain', '0px'), ('light', '4px'), ('glass', '4px')):
        t.load(settings=dict(EMULE, theme=name if name != 'plain' else 'oled'))
        if name == 'plain':
            t.js(PLAIN)
        t.click('#emlMin')
        t.js("STATUS_DELAY = 600000; showStatus('answer', true)")
        t.eq(style(t, '#emlStatus.toast', 'border-top-left-radius'), [radius], f'{name}, minimized: the band of the answer rounded as the frames')
        t.click('#emlClose')
        t.press('Escape')
        t.eq(style(t, '#emlStatus.toast', 'border-top-left-radius'), [radius], f'{name}, closed: the band of the answer rounded as the frames')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_buttons(t):
    """SF-13.4: the buttons of a theme shown, under the mouse and pressed. A theme without the optional values keeps
    the look of the buttons: Close red on the background of the buttons under the mouse. Default light frames
    Download by 2 px of blue, fills it with blue under the mouse, darker pressed, and turns Close red with a white cross
    under the mouse; the other buttons get a steel blue border under the mouse, a light blue background pressed. Firefox light turns Close
    red with a white cross under the mouse, darker pressed; Legacy draws the native buttons of the browser (a darker
    border under the mouse, a lighter background pressed, Download and Save framed as the others); macOS has larger
    buttons at the top right, its traffic lights, the symbols drawn on them. A button pressed and released away from
    it is not clicked."""
    t.load(settings=EMULE)
    t.js(PLAIN)
    t.hover('#emlClose')
    t.eq(style(t, '#emlClose', 'background-color', 'color'), ['rgb(38, 38, 38)', 'rgb(255, 92, 92)'], 'a theme without these values: Close under the mouse')
    t.load(settings=dict(EMULE, theme='win11'))
    t.hover('#emlClose')
    t.eq(style(t, '#emlClose', 'background-color', 'color'), ['rgb(196, 43, 28)', 'rgb(255, 255, 255)'], 'Windows 11 dark: Close red under the mouse')
    t.load(settings=dict(EMULE, theme='light'))
    t.eq(style(t, '#emlTop .emlAdd', 'border-top-width', 'border-top-color'), ['2px', 'rgb(0, 117, 255)'], 'Default light: Download')
    t.hover('#emlTop .emlAdd')
    t.eq(style(t, '#emlTop .emlAdd', 'background-color', 'color'), ['rgb(0, 117, 255)', 'rgb(255, 255, 255)'], 'Default light: Download under the mouse')
    t.hold('#emlTop .emlAdd')
    t.eq(style(t, '#emlTop .emlAdd', 'background-color'), ['rgb(0, 95, 208)'], 'Default light: Download pressed')
    t.release_away()
    t.hover('#emlEdit')
    t.eq(style(t, '#emlEdit', 'border-top-color'), ['rgb(43, 92, 138)'], 'Default light: Edit mode under the mouse, a steel blue border')
    t.hold('#emlEdit')
    t.eq(style(t, '#emlEdit', 'background-color'), ['rgb(214, 230, 245)'], 'Default light: Edit mode pressed, a light blue background')
    t.release_away()
    t.eq(t.js(POPUP)[2], 0, 'Edit mode released away from it: not clicked')
    t.hover('#emlClose')
    t.eq(style(t, '#emlClose', 'background-color', 'color'), ['rgb(208, 0, 0)', 'rgb(255, 255, 255)'], 'Default light: Close under the mouse')
    t.load(settings=dict(EMULE, theme='firefox'))
    t.eq(style(t, '#emlClose', 'background-color', 'color'), ['rgba(0, 0, 0, 0)', 'rgb(21, 20, 26)'], 'Firefox light: Close without frame')
    t.hover('#emlClose')
    t.eq(style(t, '#emlClose', 'background-color', 'color'), ['rgb(232, 17, 35)', 'rgb(255, 255, 255)'], 'Firefox light: Close under the mouse')
    t.hold('#emlClose')
    t.eq(style(t, '#emlClose', 'background-color'), ['rgb(197, 15, 31)'], 'Firefox light: Close pressed')
    t.release_away()
    t.eq(t.js(POPUP)[0], 1, 'Close released away from it: the popup stays')
    t.load(settings=dict(EMULE, theme='legacy'))
    look = ('border-top-width', 'border-top-color', 'background-color')
    t.eq(style(t, '#emlTop .emlAdd', *look), ['1px', 'rgb(118, 118, 118)', 'rgb(239, 239, 239)'], 'Legacy: Download as the other buttons')
    t.hover('#emlTop .emlAdd')
    t.eq(style(t, '#emlTop .emlAdd', *look), ['1px', 'rgb(79, 79, 79)', 'rgb(229, 229, 229)'], 'Legacy: under the mouse, a darker border')
    t.hold('#emlTop .emlAdd')
    t.eq(style(t, '#emlTop .emlAdd', *look), ['1px', 'rgb(141, 141, 141)', 'rgb(245, 245, 245)'], 'Legacy: pressed, a lighter background')
    t.release_away()
    t.hold('#emlClose')
    t.eq(style(t, '#emlClose', 'border-top-color', 'background-color'), ['rgb(141, 141, 141)', 'rgb(245, 245, 245)'], 'Legacy: Close pressed')
    t.release_away()
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(style(t, '#GM_config_saveBtn', 'border-top-width', 'border-top-color'), ['1px', 'rgb(118, 118, 118)'], 'Legacy: Save as the other buttons')
    t.eq(style(t, '#GM_config_resetBtn', 'background-color', 'border-top-color'), ['rgb(239, 239, 239)', 'rgb(118, 118, 118)'],
         'Legacy: the buttons of the settings in the colors of the theme')
    t.load(settings=dict(EMULE, theme='macos'))
    t.eq(style(t, '#emlClose', 'width', 'height', 'color'), ['26px', '26px', 'rgb(255, 95, 87)'], 'macOS: Close larger, a red dot')
    t.eq(style(t, '#emlClose svg', 'width'), ['16px'], 'macOS: its icon larger')
    t.eq(style(t, '#emlMin', 'color'), ['rgb(254, 188, 46)'], 'macOS: Minimize, a yellow dot')
    t.eq(style(t, '#emlClose svg .eml-glyph:last-child', 'stroke'), ['rgba(0, 0, 0, 0.5)'], 'macOS: the cross drawn on the dot')
    t.click('#emlMin')
    t.eq(style(t, '#emlMin svg', 'color'), ['rgb(40, 200, 64)'], 'macOS: Maximize, a green dot')
    t.eq(t.errors, [], 'no JavaScript error')


def test_theme_icon_sets(t):
    """SF-13.3: a set of icons lists only the icons it changes, the others being those of outline: Monochrome light
    draws its question mark without a circle, and the other icons of outline. Each theme of the script has its set."""
    t.load(settings=dict(EMULE, theme='mono'))
    t.eq(t.js("document.querySelectorAll('#emlHelpBtn svg circle').length"), 1, 'Monochrome light: the question mark without a circle')
    t.eq(t.js("icon('close') == ICONS.outline.close.replace('<svg ', '<svg data-eml-icon=\"close\" ')"), True,
         'Monochrome light: Close taken from outline')
    t.eq(t.js("Object.keys(THEMES).filter(function (n) { return !ICONS[THEMES[n].icons]; })"), [], 'each theme has its set of icons')
    t.eq(t.errors, [], 'no JavaScript error')


SIZE_LOOK = """(function () { var a = document.querySelector('#divBody a'), b = document.querySelector('#emlTop .emlAdd'),
  i = document.querySelector('#emlClose svg'), s = getComputedStyle(b);
  return [getComputedStyle(a).fontSize, b.getBoundingClientRect().height, i.getBoundingClientRect().width, s.borderTopWidth,
          s.borderTopLeftRadius]; })()"""


def near(a, b):
    return abs(a - b) < 0.1


SECTIONS = """[].map.call(document.querySelectorAll('#GM_config .section_header_holder'), function (h) {
  return [h.querySelector('.section_header').textContent, h.classList.contains('emlFolded')]; })"""


def test_settings_sections(t):
    """SF-8: the sections of the settings dialog, in their order: General, Servers, Keyboard shortcuts, Toolbars, Popup, Edit
    box; Show a message when the popup is closed in Popup, after Popup scrolling. A click on a header, or Enter on it, folds
    or unfolds its section, a chevron at its right; the first time, General and Servers only are unfolded (settingsUnfolded);
    each choice is stored at once, without Save, and kept at the next opening. A wrong value unfolds its section on Save."""
    t.load(settings=EMULE, folded=None)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(SECTIONS), [['General', False], ['Servers', False], ['Keyboard shortcuts', True], ['Toolbars', True], ['Popup', True],
                          ['Edit box', True]], 'the sections, in their order; General and Servers unfolded the first time')
    t.eq(t.js("settingsUnfolded"), ['general', 'servers'], 'in PARAM')
    t.eq(t.js("[].map.call(document.querySelectorAll('#GM_config .section_header_holder'), function (h) { return h.getAttribute('data-section'); })"),
         ['general', 'servers', 'shortcuts', 'toolbars', 'popup', 'editbox'], 'each section known by the name that keeps its state')
    t.eq(t.js("getComputedStyle(document.getElementById('GM_config_popupRows_var')).display"), 'none', 'a folded section: its fields hidden')
    t.eq(t.js("[getComputedStyle(document.querySelector('#GM_config_section_header_0'), '::after').content,"
              " getComputedStyle(document.querySelector('#GM_config_section_header_4'), '::after').content]"), ['"▾"', '"▸"'],
         'the chevron: down unfolded, right folded')
    t.eq(t.js("document.getElementById('GM_config_popupScroll_var').nextElementSibling.id"), 'GM_config_closeMessage_var',
         'Show a message when the popup is closed: in Popup, after Popup scrolling')
    t.eq(t.js("document.getElementById('GM_config_closeMessage_var').nextElementSibling.id"), 'GM_config_popupRows_var', 'before Max lines')
    t.click('#GM_config_section_header_4')
    t.eq(t.js(SECTIONS)[4], ['Popup', False], 'a click: Popup unfolded')
    t.eq(json.loads(t.gm('settings_folded')), ['shortcuts', 'toolbars', 'editbox'], 'stored at once')
    t.click('#GM_config_section_header_0')
    t.js("document.getElementById('GM_config_section_header_2').dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true}))")
    t.eq([s[1] for s in t.js(SECTIONS)], [True, False, False, True, False, True], 'General folded by a click, Keyboard shortcuts unfolded by Enter')
    t.js("document.getElementById('GM_config_closeBtn').click()")
    t.check(t.open_settings(), 'settings dialog opened again')
    t.eq([s[1] for s in t.js(SECTIONS)], [True, False, False, True, False, True], 'the state kept')
    t.reload()
    t.check(t.open_settings(), 'opened on the next page')
    t.eq([s[1] for s in t.js(SECTIONS)], [True, False, False, True, False, True], 'kept on the next page')
    t.js(f"{field('editRow')}.value = '0'")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.eq([t.js(SECTIONS)[5][1], t.js("!!document.querySelector('#GM_config_editRow_var .error')")], [False, True],
         'a wrong value in Edit box, folded: the section unfolded on Save, the error shown')
    t.eq(t.errors, [], 'no JavaScript error')


SHORTCUT_ROWS = """[].map.call(document.querySelectorAll('#GM_config_shortcuts_var tr'), function (tr) {
  var s = tr.querySelector('select'); return [tr.querySelector('th').textContent, tr.cells[1].textContent.split(s.textContent)[0], s.id.replace('GM_config_field_', ''), s.value]; })"""


FIELD_EDGES = """(function (ids) { return ids.map(function (id) {
  var l = document.getElementById('GM_config_' + id + '_field_label') || document.querySelector('#GM_config_' + id + '_var > label'),
      f = document.getElementById('GM_config_field_' + id);
  return [Math.round(l.getBoundingClientRect().right * 2) / 2, Math.round(f.getBoundingClientRect().left * 2) / 2]; }); })"""


def test_settings_fields_aligned(t):
    """SF-8: the labels and the fields of the server edited, inside the list of the servers, are aligned on those of the
    other sections (they were 7 px further right: the padding of the row of the list and its border), at every size, the
    dialog wide enough for its two columns."""
    for size in (100, 140):
        t.load(settings=dict(EMULE, textSize=size))
        t.set_viewport(1800, 1000)
        t.check(t.open_settings(), f'{size} %: settings dialog opened')
        edges = t.js(FIELD_EDGES + "(['language', 'serverName', 'emuleUrl', 'popupRows'])")
        t.check(all(abs(e[0] - edges[0][0]) < 0.6 and abs(e[1] - edges[0][1]) < 0.6 for e in edges),
                f'{size} %: the labels end and the fields start at the same place in every section', edges)
    t.eq(t.errors, [], 'no JavaScript error')


# each list of the table of the shortcuts at least as wide as the browser makes it for its choices (None not cut), all alike
SHORTCUT_WIDTHS = """(function () {
  var lists = [].slice.call(document.querySelectorAll('#GM_config_shortcuts_var select'));
  var clone = lists[0].cloneNode(true); clone.style.setProperty('width', 'auto', 'important');
  lists[0].parentNode.appendChild(clone); var natural = clone.getBoundingClientRect().width; clone.remove();
  var widths = lists.map(function (l) { return l.getBoundingClientRect().width; });
  return [Math.min.apply(null, widths) >= natural - 0.5, Math.max.apply(null, widths) - Math.min.apply(null, widths) < 0.5]; })()"""


def test_shortcut_lists_width(t):
    """SF-9: the lists of the table of the shortcuts show None whole (Aucun in French), all of the same width (None was cut
    by a width of 9 characters)."""
    for language in ('en', 'fr'):
        t.load(settings=dict(EMULE, language=language))
        t.check(t.open_settings(), f'{language}: settings dialog opened')
        t.eq(t.js(SHORTCUT_WIDTHS), [True, True], f'{language}: every list as wide as its choices, all alike')
    t.eq(t.errors, [], 'no JavaScript error')


def test_shortcuts_in_settings(t):
    """SF-9: the letters of the keyboard shortcuts chosen in the settings, in the section Keyboard shortcuts: a row per action,
    Ctrl+Alt+ and a list, None then A to Z, the letters of the PARAM block by default; a letter used twice is refused under
    the field, nothing saved; a letter saved works on the next page, the old one no more, the tooltips and the menu of the
    manager follow; None turns a shortcut off; Reset sets the letters of PARAM back."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(SHORTCUT_ROWS), [['Check or uncheck all links', 'Ctrl+Alt+', 'keyCheckAll', 'A'], ['Download', 'Ctrl+Alt+', 'keyDownload', 'D'],
                               ['Copy the links', 'Ctrl+Alt+', 'keyCopy', 'C'], ['Export (its menu)', 'Ctrl+Alt+', 'keyExport', ''],
                               ['Edit mode / Normal mode', 'Ctrl+Alt+', 'keyEditMode', ''], ['Settings', 'Ctrl+Alt+', 'keySettings', 'S'],
                               ['Help', 'Ctrl+Alt+', 'keyHelp', 'H'], ['Switch view (maximized, minimized, closed)', 'Ctrl+Alt+', 'keyView', 'W'],
                               ['Close the popup', 'Ctrl+Alt+', 'keyClose', ''], ['Open the popup', 'Ctrl+Alt+', 'keyOpen', 'O'],
                               ['Debug traces (on / off)', 'Ctrl+Alt+', 'keyDebug', '']], 'a row per action, the letters of PARAM')
    t.eq(t.js("[].map.call(document.querySelectorAll('#GM_config_field_keyCopy option'), function (o) { return o.textContent; }).join('')"),
         'None' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'None, then A to Z')
    t.js(f"{field('keyCopy')}.value = 'D'")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(0.5)
    t.eq([t.settings_open(), t.js("(document.querySelector('#GM_config_keyCopy_var .error') || {}).textContent")],
         [True, 'Already the shortcut of Download'], 'a letter used twice: refused, nothing saved')
    t.js(f"{field('keyCopy')}.value = 'K'; {field('keyClose')}.value = 'Q'; {field('keyCheckAll')}.value = ''")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq([t.stored_settings().get(k) for k in ('keyCopy', 'keyClose', 'keyCheckAll')], ['K', 'Q', ''], 'saved')
    t.js(EXPORT_CATCH)
    t.keys('c')
    t.eq(t.js('window.__copied'), [], 'Ctrl+Alt+C: nothing any more')
    t.keys('k')
    t.eq(len(t.js('window.__copied')), 1, 'Ctrl+Alt+K copies')
    t.keys('a')
    t.eq(t.js("document.querySelectorAll('#divBody input.smallcheck:checked').length"), 9, 'None: Ctrl+Alt+A does nothing')
    t.eq(t.js("document.getElementById('emlClose').title"), 'Close (Ctrl+Alt+Q)', 'the tooltips follow')
    t.keys('q')
    t.eq(t.js("!!document.getElementById('theDiv')"), False, 'Ctrl+Alt+Q closes the popup')
    t.press('Escape')
    t.check(t.open_settings(), 'settings dialog opened again')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq([t.js(f"{field(k)}.value") for k in ('keyCopy', 'keyClose', 'keyCheckAll')], ['C', '', 'A'], 'Reset: the letters of PARAM')
    t.eq(t.js("document.getElementById('GM_config_keyCopy_var').classList.contains('changed')"), True, 'highlighted')
    t.load(settings=dict(EMULE, keySettings='P', keyHelp='p', keyOpen='?'))
    t.eq(t.js("[shortcuts.settings, shortcuts.help, shortcuts.open]"), ['P', '', ''], 'P for Settings; p, taken by Settings, and ?: none')
    t.eq([k in t.js('Object.keys(window.__GM_menu)') for k in 'pso'], [True, False, False], 'the menu of the manager follows')
    t.load(settings=dict(EMULE, keySettings='T'))
    t.eq(t.js("[window.__GM_menu.t === setButton, Object.keys(window.__GM_menu).filter(function (k) { return window.__GM_menu[k] === debugButton; })]"),
         [True, ['undefined']], 'T for Settings: the debug traces leave it, without an access key')
    t.load(settings=dict(EMULE, keyDebug='G'))
    t.eq(t.js("[window.__GM_menu.g === debugButton, 't' in window.__GM_menu]"), [True, False], 'the debug traces take the letter of their shortcut')
    t.eq(t.errors, [], 'no JavaScript error')


def test_texts_of_the_shortcuts(t):
    """SF-9, SF-10.4, SF-11: the texts that name a keyboard shortcut are built from the shortcuts that exist, in English and
    French: the message of the closed popup, the help of Close, the help of Default popup view; a shortcut set to None is
    not named, and the sentence stays right (it showed "press , or" before)."""
    help_row = ("[].map.call(document.querySelectorAll('#emlHelp .emlHelpRows tr'), function (tr) { return tr.cells[1].textContent; })"
                ".filter(function (s) { return /^(Closes|Ferme) /.test(s); })[0]")
    items = "[].map.call(document.querySelectorAll('#emlMsg .emlMsgText li'), function (li) { return li.textContent; })"
    view_help = "document.querySelector('#GM_config_popupView_var .help').textContent"
    none = dict(keyOpen='', keyView='', keySettings='')
    cases = [
        ('en', {}, ['press Ctrl+Alt+O, or', 'press Ctrl+Alt+W, or', 'choose Open Popup in the menu of Tampermonkey.'],
         'Closes the popup on this page; Ctrl+Alt+O opens it again',
         'can then be opened only with the keyboard shortcuts (Ctrl+Alt+O or Ctrl+Alt+W: the popup, Ctrl+Alt+S: this dialog) or from the menu of'),
        ('en', none, ['choose Open Popup in the menu of Tampermonkey.'], 'Closes the popup on this page',
         'can then be opened only from the menu of'),
        ('en', dict(keyOpen=''), ['press Ctrl+Alt+W, or', 'choose Open Popup in the menu of Tampermonkey.'], 'Closes the popup on this page',
         'can then be opened only with the keyboard shortcuts (Ctrl+Alt+W: the popup, Ctrl+Alt+S: this dialog) or from the menu of'),
        ('fr', {}, ['appuyez sur Ctrl+Alt+O, ou', 'appuyez sur Ctrl+Alt+W, ou', 'choisissez Ouvrir la popup dans le menu de Tampermonkey.'],
         'Ferme la popup sur cette page ; Ctrl+Alt+O la rouvre',
         'ne s\'ouvrent alors que par les raccourcis clavier (Ctrl+Alt+O ou Ctrl+Alt+W : la popup, Ctrl+Alt+S : ces réglages) ou par le menu de'),
        ('fr', none, ['choisissez Ouvrir la popup dans le menu de Tampermonkey.'], 'Ferme la popup sur cette page',
         'ne s\'ouvrent alors que par le menu de'),
    ]
    for language, keys, closed, close_help, view in cases:
        name = f'{language}, {", ".join(k for k in keys) or "every shortcut"}'
        t.load(settings=dict(EMULE, language=language, **keys))
        t.click('#emlHelpBtn')
        t.eq(t.js(help_row), close_help, f'{name}: the help of Close')
        t.press('Escape')
        t.click('#emlClose')
        t.eq(t.js(items), closed, f'{name}: the message of the closed popup')
        t.press('Escape')
        t.js('setButton()')     # as its button: Ctrl+Alt+S may be None
        t.pump(0.5)
        t.check(t.settings_open(), f'{name}: settings dialog opened')
        text = t.js(view_help)
        t.check(view in text and '``' not in text and '()' not in text, f'{name}: the help of Default popup view', text)
    t.eq(t.errors, [], 'no JavaScript error')


def test_size_slider(t):
    """SF-2.5: Size, in the General section after Theme, a slider from 80 % to 160 % by steps of 10 % (SIZE_MIN, SIZE_MAX,
    SIZE_STEP), its value at its right, 100 % (default); saved, the screens follow; Reset puts 100 % back; a value out of
    the range or of the steps, or a name of the first trials (medium), is read as 100 %, stored once."""
    value = "[document.getElementById('GM_config_field_textSize').value, document.getElementById('GM_config_textSizeValue').textContent]"
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_theme_var').nextElementSibling.id"), 'GM_config_textSize_var', 'after Theme')
    t.eq(t.js("(function(f){return [f.type, f.min, f.max, f.step];})(document.getElementById('GM_config_field_textSize'))"),
         ['range', '80', '160', '10'], 'a slider, 80 to 160 by 10')
    t.eq(t.js('[SIZE_MIN, SIZE_MAX, SIZE_STEP]'), [80, 160, 10], 'in PARAM')
    t.eq(t.js(value), ['100', '100 % (default)'], '100 % by default')
    t.js("var f = document.getElementById('GM_config_field_textSize'); f.value = 120; f.dispatchEvent(new Event('input'))")
    t.eq(t.js(value), ['120', '120 %'], 'moved: its value follows')
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq([t.stored_settings().get('textSize'), t.js('sizeFactor()'), t.js(SIZE_LOOK)[0]], [120, 1.2, '12px'], 'saved: the popup at 120 %')
    t.check(t.open_settings(), 'settings dialog opened again')
    t.eq(t.js(value), ['120', '120 %'], 'the slider at 120 %')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js(value), ['100', '100 % (default)'], 'Reset: 100 %')
    for wrong in ('medium', 85, 200):
        t.load(settings=dict(EMULE, textSize=wrong))
        t.eq([t.js(SIZE_LOOK)[0], t.stored_settings().get('textSize')], ['10px', 100], f'{wrong!r}: read as 100 %, stored once')
    t.load(settings=dict(EMULE, language='fr', textSize=140))
    t.check(t.open_settings(), 'settings dialog opened, in French')
    t.eq(t.js(value), ['140', '140 %'], 'in French')
    t.eq(t.errors, [], 'no JavaScript error')


def test_size_scale(t):
    """SF-2.5: the size multiplies every length of 3 px or more of the screens of the script by its factor (1, 1.2,
    1.4): the text of the list (10, 12, 14 px), the height of the buttons (22 px at Small), their icons (12 px), the
    radius of the theme (3 px for Default light); the borders of 1 and 2 px stay thin. The help, the message of the
    closed popup and the settings dialog follow; so do the sizes given by a theme (the buttons of macOS, 26 px)."""
    for name, factor in ((100, 1), (120, 1.2), (140, 1.4)):
        t.load(settings=dict(EMULE, textSize=name))
        font, height, icon, border, radius = t.js(SIZE_LOOK)
        t.eq(font, f'{round(10 * factor)}px', f'{name}: the text of the list')
        t.check(near(height, 22 * factor) and near(icon, 12 * factor), f'{name}: the buttons and their icons', [height, icon])
        t.eq([border, radius], ['2px', f'{round(3 * factor, 2):g}px'], f'{name}: the border of Download stays, its radius follows')
        t.click('#emlHelpBtn')
        t.eq(t.js("getComputedStyle(document.querySelector('#emlHelp td:nth-child(2)')).fontSize"), f'{round(12 * factor, 2):g}px',
             f'{name}: the help')
        t.press('Escape')
        t.click('#emlClose')
        t.eq(t.js("getComputedStyle(document.querySelector('#emlMsg .emlMsgText')).fontSize"), f'{round(12 * factor, 2):g}px',
             f'{name}: the message of the closed popup')
        t.press('Escape')
        t.check(t.open_settings(), f'{name}: settings dialog opened')
        t.eq(t.js("getComputedStyle(document.querySelector('#GM_config .field_label')).fontSize"), f'{round(12 * factor, 2):g}px',
             f'{name}: the settings dialog')
    t.load(settings=dict(EMULE, theme='macos', textSize=140))
    t.check(near(t.js("document.getElementById('emlClose').getBoundingClientRect().width"), 26 * 1.4), 'macOS, Large: its buttons follow',
            t.js("document.getElementById('emlClose').getBoundingClientRect().width"))
    t.eq(t.errors, [], 'no JavaScript error')


def test_size_lists_in_characters(t):
    """SF-6.11: the widths of the category list and of the server list are given in characters: they follow the size."""
    width = "parseFloat(getComputedStyle(document.querySelector('#emlTop .emlCat')).minWidth)"
    t.eq(t.js("[categoryListMinWidth, categoryListMaxWidth, serverListMaxWidth]"), [16, 22, 22], 'in characters, in PARAM')
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2'))
    small = t.js(width)
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2', textSize=140))
    large = t.js(width)
    t.check(small > 80 and abs(large / small - 1.4) < 0.02, 'the min width of the category list follows the size', [small, large])
    t.eq(t.js("getComputedStyle(document.querySelector('#emlTop .emlCat')).maxWidth.slice(-2)"), 'px', 'computed in pixels')
    t.eq(t.errors, [], 'no JavaScript error')


def test_popup_rows_cols(t):
    """SF-2.3: the maximum height of the popup in lines of its list (popupRows): the list shows that many lines, and
    scrolls beyond, at every size; 0 shows every line. The maximum width in characters of the list (popupCols)."""
    rows = """(function () { var l = document.getElementById('divBody'), r = l.querySelectorAll('tr');
      return [l.clientHeight / r[1].getBoundingClientRect().height, l.scrollHeight > l.clientHeight + 1]; })()"""
    for size in (100, 140):
        t.load(settings=dict(EMULE, popupRows=4, textSize=size))
        shown, scrolls = t.js(rows)
        t.check(abs(shown - 4) < 0.1 and scrolls, f'{size}: four lines, the list scrolls', [shown, scrolls])
    t.load(settings=dict(EMULE, popupRows=0))
    t.eq(t.js(rows)[1], False, '0: every line')
    t.load(settings=dict(EMULE, popupCols=40))
    ch = ("(function () { var d = document.getElementById('theDiv'), p = document.createElement('span');"
          " p.style.cssText = 'display:inline-block;width:40ch'; d.appendChild(p); var w = p.getBoundingClientRect().width; p.remove();"
          " return [parseFloat(getComputedStyle(d).width), w]; })()")
    width, limit = t.js(ch)
    t.check(width <= limit + 0.5, 'the popup no wider than 40 characters of its list, its margins and frame apart', [width, limit])
    t.eq(t.errors, [], 'no JavaScript error')


def test_popup_rows_cols_migration(t):
    """SF-8: the maximum height and width of the popup, stored in pixels before 0.15 (popupHeight, popupWidth), are
    converted once in lines and characters: 800 px give 43 lines and 148 characters; 0 stays unlimited; a width too
    small gives the minimum, 35 characters (POPUP_COLS_MIN)."""
    t.load(settings=dict(EMULE, popupHeight=800, popupWidth=800))
    t.eq([t.stored_settings().get(k) for k in ('popupRows', 'popupCols')], [43, 148], '800 px: 43 lines, 148 characters')
    t.load(settings=dict(EMULE, popupHeight=0, popupWidth=50))
    t.eq([t.stored_settings().get(k) for k in ('popupRows', 'popupCols')], [0, 35], 'unlimited stays, a small width gives the minimum, 35')
    t.load(settings=dict(EMULE, popupRows=12, popupHeight=800))
    t.eq(t.stored_settings().get('popupRows'), 12, 'converted once: a number of lines already stored is kept')
    t.eq(t.errors, [], 'no JavaScript error')


def test_settings_narrow(t):
    """SF-8: in a narrow window (a phone, 390 px), the settings dialog fits in it: no part out of it, each label
    above its field, the rows of the servers on several lines."""
    t.load(settings=EMULE)     # a page first: WebDriver BiDi sets no viewport before (the test may run first)
    t.set_viewport(390, 844)
    try:
        t.load(settings=EMULE)
        t.check(t.open_settings(), 'settings dialog opened')
        t.eq(t.js("(function (d) { return [d.scrollWidth <= d.clientWidth + 1, d.getBoundingClientRect().right <= innerWidth]; })"
                  "(document.getElementById('GM_config'))"), [True, True], 'nothing out of the dialog, the dialog in the window')
        t.eq(t.js("(function () { var l = document.getElementById('GM_config_theme_field_label').getBoundingClientRect(),"
                  " f = document.getElementById('GM_config_field_theme').getBoundingClientRect(); return l.bottom <= f.top + 0.5; })()"),
             True, 'the label above its field')
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


FOLD = """(function () { var d = document.getElementById('theDiv'), bars = d.querySelectorAll('.toolbar');
  var names = {emlEditBtn: 'edit', emlSrv: 'server', emlCat: 'category', emlExport: 'export', emlDrag: 'space'};
  var hidden = function (c) { return getComputedStyle(c).display == 'none'; };
  return {folded: (hidden(document.getElementById('emlMenuBtn')) ? [] : ['menu']).concat([].concat.apply([], [].map.call(bars, function (b) {
            return [].filter.call(b.children, function (c) { return !c.classList.contains('emlOff') && !c.classList.contains('emlIcon') && hidden(c); }).map(function (c) {
              var n = Object.keys(names).filter(function (k) { return c.classList.contains(k); })[0];
              return b.id.replace('eml', '').toLowerCase() + '.' + (names[n] || c.id || c.className); }); }))),
          data: d.dataset.folded, menu: document.getElementById('emlMenuBtn').getClientRects().length > 0,
          stay: [].every.call(d.querySelectorAll('.toolbar > .checkall, .toolbar > .emlCount, .toolbar > .emlAdd:not(.emlOff)'),
                              function (c) { return getComputedStyle(c).display != 'none'; }),
          overflow: [].some.call(bars, function (b) { return b.getClientRects().length && b.scrollWidth > b.clientWidth + 1; }),
          add: document.querySelector('#emlTop .emlAdd').getBoundingClientRect().width,
          drag: document.querySelector('#emlTop .emlDrag').getBoundingClientRect().width,
          help: document.getElementById('emlHelpBtn').getBoundingClientRect().width}; })()"""
MENU_ROWS = """[].map.call(document.querySelectorAll('#emlMenu .emlMenuRow'), function (r) {
  return r.tagName == 'LABEL' ? r.firstChild.textContent : r.querySelector('.emlMenuText').textContent; })"""
# the commands of the menu of Export, in their order (SF-14)
EXPORT_ROWS = ['Copy the links', 'eMule collection (.emulecollection)', 'CSV (.csv)', 'Text, one link per line (.txt)']


FOLD_ORDER = {'top': ['top.server', 'top.category', 'top.space'], 'bottom': ['bottom.edit', 'bottom.export', 'bottom.server', 'bottom.category']}


def fold_narrowing(t, orders=FOLD_ORDER):
    """The folding as the window narrows, checked at each width: the menu button first, then in each toolbar its
    controls one by one from left to right (orders), never the check box, the counter nor Download, no control
    narrowed, the free space kept until folded, no toolbar cut before everything is folded; the folding of each
    width, from the widest."""
    wide = t.js(FOLD)
    seen = []
    for width in range(640, 150, -10):
        t.set_viewport(width, 700)
        t.pump(0.2)
        now = t.js(FOLD)
        folded = now['folded']
        seen.append(folded)
        if folded and folded[0] != 'menu':
            t.check(False, f'{width} px: the menu button first', folded)
        if (now.get('data') or '') != ' '.join(folded):
            t.check(False, f'{width} px: what is folded, told by the popup (data-folded)', now)
        for bar, order in orders.items():
            mine = [f for f in folded if f.startswith(bar + '.')]
            if mine != order[:len(mine)]:
                t.check(False, f'{width} px: the {bar} toolbar folded from left to right', folded)
        if not now['stay']:
            t.check(False, f'{width} px: the check box, the counter and Download never folded', now)
        if now['overflow'] and len(folded) < 1 + sum(len(o) for o in orders.values()):
            t.check(False, f'{width} px: no toolbar cut', now)
        if abs(now['add'] - wide['add']) > 0.5 or (not folded and abs(now['help'] - wide['help']) > 0.5):
            t.check(False, f'{width} px: the controls keep their width', [now, wide])
        if 'top.space' not in folded and now['drag'] < 23.5:
            t.check(False, f'{width} px: the free space kept to move the popup', now)
    t.check(all(set(a) <= set(b) for a, b in zip(seen, seen[1:])), 'the folding only goes on as the window narrows', seen)
    return seen


def test_toolbars_fold(t):
    """SF-2.13: as soon as a toolbar does not fit in the popup, the menu button takes the place of the buttons at the
    top right; then, while a toolbar does not fit, its controls go one by one into the menu, from left to right (Edit
    mode, the server list, the category list), each toolbar on its own; at last, the free space of the top toolbar,
    kept until then (24 px at least) to move the popup. The check box, the counter and Download stay; no control is
    narrowed, no toolbar cut on the way. A wider window shows them again."""
    servers = two_servers()
    t.load(settings=settings_of(servers), servers=servers)
    wide = t.js(FOLD)
    t.eq([wide['folded'], wide['menu'], wide['overflow']], [[], False, False], 'wide enough: every control, no menu button')
    try:
        seen = fold_narrowing(t)
        t.check(any('bottom.edit' in f and 'bottom.server' not in f for f in seen),
                'Edit mode of the bottom toolbar folded before its server list (from left to right)', seen)
        t.check({'menu', 'top.server', 'top.category', 'bottom.edit', 'bottom.export', 'bottom.server', 'bottom.category'} <= set(seen[-1]),
                'at last, every control folded', seen[-1])
    finally:
        t.clear_viewport()
    t.pump(0.3)
    t.eq(t.js(FOLD)['folded'], [], 'the window wide again: every control back')
    t.eq(t.errors, [], 'no JavaScript error')


def test_toolbars_fold_each(t):
    """SF-2.13: each toolbar folds on its own: a toolbar that fits keeps its controls while the other one folds; the
    bottom toolbar alone too wide puts the menu button in place of the buttons at the top right first. A list folded
    in one toolbar and shown in the other is in the menu."""
    servers = two_servers()
    base = settings_of(servers)
    try:
        # the bottom toolbar holding Download only: it always fits, the top one folds
        t.load(settings=dict(base, tbEditBottom='none', tbExportBottom='none', tbServerBottom='none', tbCategoryBottom='none'), servers=servers)
        seen = fold_narrowing(t, {'top': FOLD_ORDER['top'], 'bottom': []})
        t.check(any('top.category' in f for f in seen), 'the top toolbar folded', seen)
        t.check(not any(f.startswith('bottom.') for s in seen for f in s), 'the bottom toolbar, which fits, not folded', seen)
        t.clear_viewport()
        # the top toolbar without lists: the bottom one folds alone, after the menu button
        t.load(settings=dict(base, tbServerTop='none', tbCategoryTop='none'), servers=servers)
        seen = fold_narrowing(t, {'top': ['top.space'], 'bottom': FOLD_ORDER['bottom']})
        first = next(s for s in seen if s)
        t.check(first[0] == 'menu' and not any(f.startswith('top.') for f in first),
                'the bottom toolbar too wide, the top one fitting: the menu button in place of the buttons at the top right', first)
        t.check(any('bottom.category' in s for s in seen), 'the bottom toolbar folded', seen)
        t.clear_viewport()
        # a list folded at the bottom, still shown at the top (a top toolbar without category list): in the menu anyway, once
        t.load(settings=dict(base, tbCategoryTop='none'), servers=servers)
        for width in range(800, 150, -10):
            t.set_viewport(width, 700)
            t.pump(0.2)
            folded = t.js(FOLD)['folded']
            if 'bottom.server' in folded and 'top.server' not in folded:
                break
        t.check('bottom.server' in folded and 'top.server' not in folded, f'{width} px: the server list folded at the bottom only', folded)
        t.click('#emlMenuBtn')
        t.eq(t.js(MENU_ROWS).count('Server'), 1, 'in the menu, once')
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_popup_in_narrow_window(t):
    """SF-2.3: in a window narrower than the popup, the popup keeps in it, its padding and its frame included, at
    every size: nothing of it, its buttons included, is out of the window (it went 14 px out of it before). Limited by the
    window, it takes its whole width: its frame stays 2 px on each side at every size (at 140 %, it was 1.6 px narrower)."""
    try:
        for size in (100, 140):
            for width in (360, 250):
                t.load(settings=dict(EMULE, textSize=size))
                t.set_viewport(width, 700)
                t.pump(0.3)
                edges = t.js("(function(){var r=document.getElementById('theDiv').getBoundingClientRect(),"
                             " b=document.getElementById('emlMenuBtn').getBoundingClientRect();"
                             " return [r.right <= document.documentElement.clientWidth + 0.5, b.right <= r.right + 0.5];})()")
                t.eq(edges, [True, True], f'{size}, {width} px: the popup and its menu button in the window')
                whole = t.js("(function(){var d=document.getElementById('theDiv'), r=d.getBoundingClientRect();"
                             " return d.style.minWidth ? null : Math.abs(r.width - document.documentElement.clientWidth) < 0.5;})()")
                if width == 250:    # narrower than the list: the window limits the popup
                    t.check(whole is not False, f'{size}, {width} px: the popup as wide as the window', whole)
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


MENU_REACHABLE = """(function () { var r = document.getElementById('theDiv').getBoundingClientRect();
  return ['emlMenuBtn', 'GM_none'].concat([].map.call(document.querySelectorAll('#emlTop [data-icon=settings]'), function () { return 'settings'; }))
    .some(function (id) { var e = id == 'settings' ? document.querySelector('#emlTop [data-icon=settings]') : document.getElementById(id);
      if (!e) { return false; } var b = e.getBoundingClientRect(); return b.width > 0 && b.left >= r.left - 0.5 && b.right <= r.right + 0.5; }); })()"""


TB_TABLE = """(function () { var t = document.querySelector('#GM_config_toolbars_var table.emlToolbars'); if (!t) { return null; }
  return [].map.call(t.querySelectorAll('tr:not(.top):not(#GM_config_tbForced)'), function (r) {
    return [r.querySelector('th').firstChild.textContent].concat([].map.call(r.querySelectorAll('td'), function (c) {
      var s = c.querySelector('select'); return s ? s.id.replace('GM_config_field_', '') + '=' + s.value : c.textContent; })); }); })()"""
TB_OPTIONS = "(function(id){return [].map.call(document.getElementById('GM_config_field_'+id).options,function(o){return o.value+'='+o.text;});})"
TB_FIELD = "document.getElementById('GM_config_field_{}')"


def tb_set(t, field, value):
    t.js(f"var s = {TB_FIELD.format(field)}; s.value = '{value}'; s.dispatchEvent(new Event('change'))")


def test_toolbar_settings(t):
    """SF-2.14: the table Toolbars of the Popup section, first in it, in place of the checkboxes Show the category list and
    Show the server list: a row per control, from left to right as in the toolbars, a column per toolbar; Shown, In the
    menu, Not shown at the top, Shown, Not shown at the bottom; Edit mode not shown at the top by default. As soon as a
    control of the top toolbar is in the menu, the buttons at the top right are too: their list grayed out, a note under
    it; the choice of the user comes back without it, and is the one saved. Reset sets the defaults back, highlighted;
    narrow, the table is stacked."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.querySelector('#GM_config_toolbars_var .field_label').textContent"), '', 'no label: the title of its section')
    t.eq(t.js("document.getElementById('GM_config_toolbars_var').closest('.section_header_holder').querySelector('.section_header').textContent"),
         'Toolbars', 'in its own section, Toolbars')
    t.eq(t.js("document.querySelector('#GM_config_toolbars_var .order').textContent"), 'From left to right, as in the toolbars', 'its order told')
    t.eq(t.js(TB_TABLE), [['Check box and counter', 'Always shown', 'Always shown'], ['Edit mode', 'tbEditTop=none', 'tbEditBottom=shown'],
                          ['Export', 'tbExportTop=none', 'tbExportBottom=shown'],
                          ['Server list', 'tbServerTop=shown', 'tbServerBottom=shown'], ['Category list', 'tbCategoryTop=shown', 'tbCategoryBottom=shown'],
                          ['Download', 'Always shown', 'tbDownloadBottom=shown'], ['Buttons at the top right', 'tbButtonsTop=shown', '\u2014']],
         'a row per control, from left to right, its defaults')
    t.eq([t.js(TB_OPTIONS + f"('{f}')") for f in ('tbServerTop', 'tbServerBottom', 'tbButtonsTop')],
         [['shown=Shown', 'menu=In the menu \u2630', 'none=Not shown'], ['shown=Shown', 'none=Not shown'], ['shown=Shown', 'menu=In the menu \u2630']],
         'the choices at the top, at the bottom, of the buttons at the top right')
    help = t.js("document.querySelector('#GM_config_toolbars_var .help').textContent")
    t.check('two choices' in help and 'fewer than two categories' in help and 'not used' in help, 'its help', help)
    forced = f"[{TB_FIELD.format('tbButtonsTop')}.value, {TB_FIELD.format('tbButtonsTop')}.disabled, document.getElementById('GM_config_tbForced').hidden]"
    t.eq(t.js(forced), ['shown', False, True], 'the buttons at the top right: shown, free')
    tb_set(t, 'tbServerTop', 'menu')
    t.eq(t.js(forced), ['menu', True, False], 'the server list in the menu: the buttons follow, grayed out, a note')
    tb_set(t, 'tbServerTop', 'shown')
    t.eq(t.js(forced), ['shown', False, True], 'back: their own choice again')
    tb_set(t, 'tbEditTop', 'shown')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq([t.js(TB_FIELD.format('tbEditTop') + '.value'), t.js("document.getElementById('GM_config_tbEditTop_var').classList.contains('changed')")],
         ['none', True], 'Reset: the default back, highlighted')
    tb_set(t, 'tbCategoryTop', 'menu')
    tb_set(t, 'tbDownloadBottom', 'none')
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq([t.stored_settings().get(k) for k in ('tbCategoryTop', 'tbDownloadBottom', 'tbButtonsTop')], ['menu', 'none', 'shown'],
         'saved, the buttons at the top right with their own choice')
    t.load(settings=EMULE)
    try:
        t.set_viewport(390, 800)
        t.pump(0.2)
        t.check(t.open_settings(), 'settings dialog opened in a narrow window')
        t.eq(t.js("[getComputedStyle(document.getElementById('GM_config_tbServerTop_var')).display,"
                  " getComputedStyle(document.querySelector('#GM_config_toolbars_var tr.top td.head')).display]"), ['grid', 'none'],
             'narrow: stacked, one line per toolbar')
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_toolbar_choices(t):
    """SF-2.14: the popup follows the choices of the settings. Edit mode shown at the top: after the counter, it switches
    the mode. The server list in the menu: gone from the top toolbar, kept at the bottom, the menu button in place of the
    buttons at the top right, the menu holding the server list then these buttons. The buttons alone in the menu: the menu
    holds them only. Download not shown at the bottom. In a narrow popup, a list shown at the bottom only goes into the
    menu when folded."""
    servers = two_servers()
    base = settings_of(servers)
    shown = "(function(id){var e=document.getElementById(id); return e ? getComputedStyle(e).display != 'none' : null;})"
    t.load(settings=dict(base, tbEditTop='shown'), servers=servers)
    t.eq([c[0] for c in t.js(BAR + "('emlTop')")][:4], ['checkall', 'emlCount', 'emlEditTop', 'srv'], 'Edit mode at the top, after the counter')
    t.click('#emlEditTop')
    t.eq(t.js(POPUP)[2], 1, 'it switches to edit mode')
    t.load(settings=dict(base, tbServerTop='menu'), servers=servers)
    t.eq([t.js(f"{shown}('{i}')") for i in ('srv', 'srv2', 'emlMenuBtn', 'emlClose', 'emlHelpBtn')], [False, True, True, False, False],
         'the server list in the menu: not at the top, at the bottom; the menu button in place of the buttons')
    t.click('#emlMenuBtn')
    t.eq(t.js(MENU_ROWS), ['Server', 'Settings', 'Help', 'Minimize', 'Close'], 'the menu: the server list, then the buttons')
    t.press('Escape')
    t.load(settings=dict(base, tbButtonsTop='menu'), servers=servers)
    t.click('#emlMenuBtn')
    t.eq(t.js(MENU_ROWS), ['Settings', 'Help', 'Minimize', 'Close'], 'the buttons alone in the menu')
    t.press('Escape')
    t.load(settings=dict(base, tbDownloadBottom='none'), servers=servers)
    t.eq([t.js("getComputedStyle(document.querySelector('#emlTop .emlAdd')).display"), t.js("getComputedStyle(document.querySelector('#emlBottom .emlAdd')).display")],
         ['block', 'none'], 'Download not shown at the bottom, always at the top')
    t.load(settings=dict(base, tbServerTop='none'), servers=servers)
    try:
        for width in range(800, 200, -10):      # the widest window where the server list of the bottom toolbar is folded
            t.set_viewport(width, 700)
            t.pump(0.2)
            if 'bottom.server' in t.js(FOLD)['folded']:
                break
        t.click('#emlMenuBtn')
        t.eq(t.js(MENU_ROWS)[:1], ['Server'], 'the server list shown at the bottom only: in the menu once folded')
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_toolbar_settings_migration(t):
    """SF-2.14: the checkboxes of 0.14, Show the category list and Show the server list, unchecked, become the lists shown
    nowhere, stored once; checked, nothing changes."""
    t.load(settings=dict(EMULE, showCategories=False, showServerList=False))
    t.eq([t.stored_settings().get(k) for k in ('tbServerTop', 'tbServerBottom', 'tbCategoryTop', 'tbCategoryBottom')], ['none'] * 4,
         'unchecked: shown nowhere')
    t.eq([t.js(CAT_LISTS), t.js(SRV_LISTS)], [[], []], 'no list')
    t.load(settings=dict(EMULE, showCategories=True))
    t.eq(t.stored_settings().get('tbCategoryTop'), None, 'checked: nothing stored')
    t.eq(t.errors, [], 'no JavaScript error')


def test_menu_reachable_narrowest(t):
    """SF-2.13, SF-8.10: the narrowest popup allowed, in normal mode (popupCols at its minimum, POPUP_COLS_MIN) and in
    edit mode (editCol at its minimum, EDIT_COLS_MIN), in every theme and size, in French (the widest texts), shows its
    menu button, and the settings open from it; a smaller value is refused by Save, and one stored anyway is corrected.
    A list of one line, or an edit box of one row, keeps its toolbars."""
    t.load(settings=EMULE)
    t.eq(t.js('[POPUP_COLS_MIN, EDIT_COLS_MIN]'), [35, 35], 'the minimums, in PARAM: the same for the popup and the edit box')
    themes = t.js('Object.keys(THEMES)')
    for theme in themes:
        for size in (100, 140):
            base = dict(EMULE, language='fr', theme=theme, textSize=size)
            t.load(settings=dict(base, popupCols=35))
            t.check(t.js(MENU_REACHABLE), f'{theme}, {size}, 35 characters: the settings or the menu button in the popup')
            t.load(settings=dict(base, editCol=35), popup_mode=2)
            t.check(t.js(MENU_REACHABLE), f'{theme}, {size}, edit mode, 35 columns: the settings or the menu button in the popup')
    t.load(settings=dict(EMULE, popupCols=35))
    t.click('#emlMenuBtn')
    t.click('#emlMenu [data-menu=settings]')
    t.check(t.settings_open(), 'the settings opened from the menu')
    t.set_field('popupCols', '34')
    t.set_field('editCol', '34')
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(0.3)
    errors = t.js("[].map.call(document.querySelectorAll('#GM_config .error'), function (e) { return e.parentNode.id; })")
    t.check('GM_config_popupCols_var' in errors and 'GM_config_editCol_var' in errors, 'smaller values refused, under their fields', errors)
    t.load(settings=dict(EMULE, popupCols=20, editCol=10))
    t.eq([t.stored_settings().get(k) for k in ('popupCols', 'editCol')], [0, 35], 'stored by an older version: corrected')
    t.check('would hide its menu' in (t.js("(document.querySelector('#emlStatus .emlStatusText') || {}).textContent") or ''), 'the width corrected: told in the band', t.js("(document.querySelector('#emlStatus .emlStatusText') || {}).textContent"))
    for settings, mode in ((dict(EMULE, popupRows=1), 1), (dict(EMULE, editRow=1), 2)):
        t.load(settings=settings, popup_mode=mode)
        t.eq(t.js("document.getElementById('emlTop').getBoundingClientRect().height > 0"), True, f'one line, mode {mode}: the toolbars kept')
    t.eq(t.dialogs, [], 'no alert')


def test_toolbar_menu(t):
    """SF-2.13: the menu button opens, under it, the controls folded, in the order Server, Category, Edit mode,
    Settings, Help, Minimize, Close (the buttons at the top right only, when nothing else is folded); its lists act as those of
    the toolbars (the server chosen for the page), its commands as their buttons; it closes on a choice, on Escape and
    on a click elsewhere."""
    servers = two_servers()
    t.load(settings=settings_of(servers), servers=servers)
    try:
        for width in range(420, 150, -10):      # the widest window where the bottom toolbar is folded, and fits
            t.set_viewport(width, 700)
            t.pump(0.2)
            fold = t.js(FOLD)
            if 'bottom.category' in fold['folded']:
                break
        t.eq(['bottom.category' in fold['folded'], fold['overflow']], [True, False], f'a narrow popup ({width} px): the lists and Edit mode folded, nothing cut')
        t.click('#emlMenuBtn')
        t.eq(t.js(MENU_ROWS), ['Server', 'Category', 'Edit mode'] + EXPORT_ROWS + ['Settings', 'Help', 'Minimize', 'Close'], 'the menu, in its order')
        t.eq(t.js("document.getElementById('emlMenuBtn').getAttribute('aria-expanded')"), 'true', 'its button pressed')
        menu = t.js("(function(){var m=document.getElementById('emlMenu').getBoundingClientRect(); return [m.left >= 0, m.right <= innerWidth];})()")
        t.eq(menu, [True, True], 'the menu in the window')
        t.js("var l = document.getElementById('srvMenu'); l.value = 'srv1'; l.dispatchEvent(new Event('change'))")
        t.eq([t.js("document.getElementById('srv').value"), t.js("!!document.getElementById('emlMenu')")], ['srv1', False],
             'a server chosen in the menu: the server of the page, the menu closed')
        t.click('#emlMenuBtn')
        t.press('Escape')
        t.eq([t.js("!!document.getElementById('emlMenu')"), t.js("!!document.getElementById('theDiv')")], [False, True],
             'Escape: the menu closed, the popup kept')
        t.click('#emlMenuBtn')
        t.click('#emlTop .emlCount')      # out of the menu, which covers the middle of the list
        t.eq(t.js("!!document.getElementById('emlMenu')"), False, 'a click elsewhere: the menu closed')
        t.click('#emlMenuBtn')
        t.click('#emlMenu [data-menu=help]')
        t.eq([t.js("!!document.getElementById('emlHelp')"), t.js("!!document.getElementById('emlMenu')")], [True, False],
             'Help in the menu: the help shown, the menu closed')
        t.press('Escape')
        # the bottom toolbar without Export, narrower than the top one: a width where the menu button alone is enough
        t.load(settings=dict(settings_of(servers), tbExportBottom='none'), servers=servers)
        for width in range(800, 300, -10):      # the widest window where the menu button is needed
            t.set_viewport(width, 700)
            t.pump(0.2)
            if t.js(FOLD)['folded'] == ['menu']:
                break
        t.eq(t.js(FOLD)['folded'], ['menu'], f'{width} px: the menu button only')
        t.click('#emlMenuBtn')
        t.eq(t.js(MENU_ROWS), ['Settings', 'Help', 'Minimize', 'Close'], 'step 1: the buttons at the top right only')
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_menu_in_short_window(t):
    """SF-2.13: in a window too short for the menu below or above its button, the menu stays in the window, as high as it at
    most, and scrolls: its last command reachable."""
    servers = two_servers()
    t.load(settings=settings_of(servers), servers=servers)
    try:
        t.set_viewport(300, 260)
        t.pump(0.3)
        t.click('#emlMenuBtn')
        box = t.js("(function(){var m=document.getElementById('emlMenu'), r=m.getBoundingClientRect();"
                   " return [r.top >= -0.5, r.bottom <= innerHeight + 0.5, m.scrollHeight > m.clientHeight];})()")
        t.eq(box, [True, True, True], 'in the window, scrolled')
        t.click('#emlMenu [data-menu=close]')
        t.eq(t.js("!!document.getElementById('theDiv')"), False, 'its last command, Close, reachable')
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')

# the files saved and the texts copied by the export, caught: the click on the link of a file, the clipboard, the command copy
EXPORT_CATCH = """(function () {
  window.__saved = []; window.__copied = [];
  HTMLAnchorElement.prototype.click = function () {
    var entry = {name: this.download, type: null, data: null}; window.__saved.push(entry);
    fetch(this.href).then(function (r) { entry.type = r.headers.get('content-type'); return r.arrayBuffer(); }).then(function (b) {
      var s = ''; new Uint8Array(b).forEach(function (c) { s += String.fromCharCode(c); }); entry.data = btoa(s); }); };
  if (navigator.clipboard) { navigator.clipboard.writeText = function (text) { window.__copied.push(['clipboard', text]); return Promise.resolve(); }; }
  document.execCommand = function (command) { window.__copied.push([command, document.activeElement.value]); return true; };
})()"""
EXPORT_DATE = "(function(){var d=new Date();return d.getFullYear()+'-'+('0'+(d.getMonth()+1)).slice(-2)+'-'+('0'+d.getDate()).slice(-2);})()"
STATUS_TEXT = "(document.querySelector('#emlStatus .emlStatusText') || {}).textContent"


def export_saved(t):
    """The files saved by the export: (name, type, bytes)."""
    import base64
    t.pump(0.3)
    return [(f['name'], f['type'], base64.b64decode(f['data'] or '')) for f in t.js('window.__saved')]


def export_choose(t, row):
    """A format chosen in the menu of Export, opened by its button in the bottom toolbar."""
    t.click('#emlExport')
    t.click(f'#emlMenu [data-menu=export-{row}]')


def read_collection(data):
    """An eMule collection read as eMule reads it (Collection.cpp, CollectionFile.cpp, CTag of packets.cpp): its version,
    its header tags, then its files, each one as {tag id: value}; every byte read."""
    pos = 0

    def uint(size):
        nonlocal pos
        value = int.from_bytes(data[pos:pos + size], 'little')
        pos += size
        return value

    def tag():
        nonlocal pos
        kind = uint(1)
        if kind & 0x80:
            kind &= 0x7F
            ident = uint(1)
        else:
            length = uint(2)
            ident = data[pos:pos + length]
            pos += length
        if kind == 0x01:
            value = data[pos:pos + 16].hex()
            pos += 16
        elif kind == 0x02 or 0x11 <= kind <= 0x20:
            length = uint(2) if kind == 0x02 else kind - 0x10
            value = data[pos:pos + length].decode('utf-8')
            pos += length
        else:
            value = uint({0x09: 1, 0x08: 2, 0x03: 4, 0x0B: 8}[kind])
        return ident, value

    version = uint(4)
    header = dict(tag() for _ in range(uint(4)))
    files = [dict(tag() for _ in range(uint(4))) for _ in range(uint(4))]
    assert pos == len(data), f'{len(data) - pos} byte(s) left'
    return version, header, files


def link_info(link):
    """What an ed2k link of a file tells, read independently of the script: name, size, hash, AICH hash."""
    import urllib.parse
    parts = link.split('|')
    name = urllib.parse.unquote(parts[2]) if '%' in parts[2] else parts[2]
    aich = next((p[2:].upper() for p in parts if p.lower().startswith('h=')), '')
    return {'name': name, 'size': int(parts[3]), 'hash': parts[4].lower(), 'aich': aich}


def test_export_button(t):
    """SF-14, SF-2.14: Export, after Edit mode in the bottom toolbar (not shown at the top by default), its label and its
    tooltip; its menu, under it on its left edge: Copy, eMule collection, CSV, Text; the button pressed while open; a click
    on it again, Escape or a click elsewhere closes it."""
    t.load(settings=EMULE)
    t.eq([c[0] for c in t.js(BAR + "('emlBottom')")][:4], ['checkall2', 'emlCount', 'emlEdit', 'emlExport'], 'after Edit mode, at the bottom')
    t.eq(t.js("getComputedStyle(document.getElementById('emlExportTop')).display"), 'none', 'not shown at the top')
    t.eq(t.js("[document.getElementById('emlExport').textContent, !!document.querySelector('#emlExport u'),"
              " document.getElementById('emlExport').title]"),
         ['Export', False, 'Export the checked links: copy them, or save them as an eMule collection, a CSV or a text file'
                           '\nCtrl+Alt+C copies the links'],
         'its label (no letter underlined: no shortcut) and its tooltip')
    t.click('#emlExport')
    t.eq(t.js(MENU_ROWS), EXPORT_ROWS, 'its menu, in its order')
    place = t.js("(function(){var m=document.getElementById('emlMenu').getBoundingClientRect(), b=document.getElementById('emlExport').getBoundingClientRect();"
                 " return [Math.abs(m.left-b.left) < 0.5, m.top >= b.bottom - 0.5 || m.bottom <= b.top + 0.5,"
                 " document.getElementById('emlExport').getAttribute('aria-expanded')];})()")
    t.eq(place, [True, True, 'true'], 'under it (or above), on its left edge; the button pressed')
    t.click('#emlExport')
    t.eq([t.js("!!document.getElementById('emlMenu')"), t.js("document.getElementById('emlExport').getAttribute('aria-expanded')")],
         [False, 'false'], 'a click again: closed')
    t.click('#emlExport')
    t.press('Escape')
    t.eq([t.js("!!document.getElementById('emlMenu')"), t.js("!!document.getElementById('theDiv')")], [False, True], 'Escape: closed, the popup kept')
    t.click('#emlExport')
    t.click('#divBody')
    t.eq(t.js("!!document.getElementById('emlMenu')"), False, 'a click elsewhere: closed')
    t.eq(t.errors, [], 'no JavaScript error')


def test_export_files(t):
    """SF-14: the checked links saved as a file named <title of the page> <date>: a text file (a link per line, CRLF), a
    CSV (UTF-8 with its BOM, Link, Name, Size as in the list, Referer the page, RFC 4180) and an eMule collection (read as
    eMule reads it: version, name of the collection, hash, size, name and AICH hash of each file); the answer in the band."""
    import csv
    import io
    t.load(settings=EMULE)
    t.click('#l0')      # one link unchecked: left out
    t.js(EXPORT_CATCH)
    checked = t.js('getSelectLink(eLinks)')
    t.check(0 < len(checked) < t.js('eLinks.length'), 'some links checked', checked)
    stem = t.js('document.title') + ' ' + t.js(EXPORT_DATE)
    export_choose(t, 'text')
    t.eq(t.js(STATUS_TEXT), f'{len(checked)} link(s) exported (text)', 'the answer')
    export_choose(t, 'csv')
    export_choose(t, 'collection')
    saved = export_saved(t)
    t.eq([(name, kind.split(';')[0]) for name, kind, _ in saved],
         [(stem + '.txt', 'text/plain'), (stem + '.csv', 'text/csv'), (stem + '.emulecollection', 'application/octet-stream')],
         'three files, named after the page and the day')
    t.eq(saved[0][2].decode('utf-8'), '\r\n'.join(checked) + '\r\n', 'text: the checked links, one per line')
    text = saved[1][2].decode('utf-8')
    t.check(text.startswith('\ufeff') and '\r\n' in text, 'CSV: UTF-8 with its BOM, CRLF')
    rows = list(csv.reader(io.StringIO(text[1:], newline='')))
    url = t.js('location.href')
    sizes = [t.js(f"humanFileSize({link_info(l)['size']}, false, 0)") for l in checked]
    t.eq(rows, [['Link', 'Name', 'Size', 'Referer']] + [[l, link_info(l)['name'], size, url] for l, size in zip(checked, sizes)],
         'CSV: Link, Name, Size as in the list, Referer')
    version, header, files = read_collection(saved[2][2])
    infos = [link_info(l) for l in checked]
    t.eq(version, 2 if any(i['size'] > 4290048000 for i in infos) else 1, 'collection: version 2 with a file over 4 290 048 000 bytes')
    t.eq(header, {0x01: t.js('document.title')}, 'collection: its name, the title of the page, no author')
    t.eq(files, [{0x28: i['hash'], 0x02: i['size'], 0x01: i['name'], **({0x27: i['aich']} if i['aich'] else {})} for i in infos],
         'collection: hash, size, name, AICH hash of each file')
    t.eq(t.errors, [], 'no JavaScript error')


def test_export_edit_mode(t):
    """SF-14: in edit mode, the links of the edit box are exported; a link that is not a file (a server) is left out of the
    collection; in the CSV, a name with a comma or a quote is quoted, a name taken for a formula starts with an apostrophe;
    a collection with a small file and a short name (one-byte integer, short string)."""
    import csv
    import io
    hash1, hash2 = '0123456789abcdef0123456789abcdef', 'fedcba9876543210fedcba9876543210'
    lines = [f'ed2k://|file|a,b "c".avi|100|{hash1}|h=ABCDEFGHIJKLMNOPQRSTUVWXYZ234567|/',
             f'ed2k://|file|=1+1.avi|70000|{hash2}|/', 'ed2k://|server|10.0.0.1|4661|/']
    t.load(settings=EMULE, popup_mode=2)
    t.js(EXPORT_CATCH)
    t.js(f"document.getElementById('editbox').value = {json.dumps(chr(10).join(lines + ['not a link', '']))}")
    export_choose(t, 'csv')
    export_choose(t, 'collection')
    t.eq(t.js(STATUS_TEXT), '2 link(s) exported (eMule collection)', 'the collection: the two files only')
    saved = export_saved(t)
    rows = list(csv.reader(io.StringIO(saved[0][2].decode('utf-8')[1:], newline='')))
    t.eq([r[:3] for r in rows[1:]], [[lines[0], 'a,b "c".avi', '100 B'], [lines[1], "'=1+1.avi", '68 KiB'], [lines[2], '', '']],
         'CSV: the lines of the edit box, quoted, the formula neutralized')
    t.check('"a,b ""c"".avi"' in saved[0][2].decode('utf-8'), 'a name with a comma and quotes, quoted (RFC 4180)')
    version, header, files = read_collection(saved[1][2])
    t.eq([version, files], [1, [{0x28: hash1, 0x02: 100, 0x01: 'a,b "c".avi', 0x27: 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'},
                                {0x28: hash2, 0x02: 70000, 0x01: '=1+1.avi'}]], 'collection: the two files')
    size = len(header[0x01].encode('utf-8'))
    t.eq(saved[1][2][8], 0x80 | (0x11 + size - 1) if size <= 16 else 0x82, 'the name of the collection: a short string type when it fits')
    t.eq(t.errors, [], 'no JavaScript error')


def test_export_copy(t):
    """SF-14: Copy puts the checked links, one per line, in the clipboard of the browser; without it (a page in http), by
    a hidden text selected and copied; the answer in the band. Nothing checked: nothing exported, a warning."""
    t.load(settings=EMULE)
    t.js(EXPORT_CATCH)
    checked = t.js('getSelectLink(eLinks)')
    export_choose(t, 'copy')
    t.eq(t.js('window.__copied'), [['clipboard', '\n'.join(checked)]], 'copied by the clipboard of the browser')
    t.eq(t.js(STATUS_TEXT), f'{len(checked)} link(s) copied', 'the answer')
    t.js("window.__copied = []; Object.defineProperty(navigator, 'clipboard', {value: undefined, configurable: true})")
    export_choose(t, 'copy')
    t.eq(t.js('window.__copied'), [['copy', '\n'.join(checked)]], 'without the clipboard: a hidden text copied')
    t.eq(t.js("document.querySelectorAll('body > textarea').length"), 0, 'the hidden text removed')
    t.js("[].forEach.call(document.querySelectorAll('#divBody input[type=checkbox]:checked'), function (c) { c.click(); })")
    t.eq(t.js('getSelectLink(eLinks).length'), 0, 'no link checked')
    export_choose(t, 'text')
    t.eq([t.js(STATUS_TEXT), len(export_saved(t))], ['No link to export: check some links first', 0], 'nothing exported, a warning')
    t.eq(t.errors, [], 'no JavaScript error')


def test_export_shortcut(t):
    """SF-14: the shortcut of Export, none by default, given a letter in the PARAM block (P here), opens its menu, its first
    command focused (Enter copies), and closes it again; without Export shown, under the top toolbar at its right; nothing
    with the popup closed."""
    t.load(settings=EMULE)
    t.js(EXPORT_CATCH)
    t.js("shortcuts.export = 'P'")
    t.keys('p')
    t.eq([t.js("document.getElementById('emlMenu').getAttribute('data-for')"), t.js("document.activeElement.getAttribute('data-menu')")],
         ['export', 'export-copy'], 'Ctrl+Alt+P: the menu, Copy focused')
    # the focused command activated, as Enter does (headless Firefox, its window never focused, does not activate a button on Enter)
    t.js('document.activeElement.click()')
    t.eq([len(t.js('window.__copied')), t.js("!!document.getElementById('emlMenu')")], [1, False], 'Copy activated: copied, the menu closed')
    t.keys('p')
    t.keys('p')
    t.eq(t.js("!!document.getElementById('emlMenu')"), False, 'Ctrl+Alt+P again: closed')
    t.load(settings=dict(EMULE, tbExportBottom='none'))
    t.js("shortcuts.export = 'P'")
    t.keys('p')
    t.eq(t.js("(function(){var m=document.getElementById('emlMenu'), b=document.getElementById('emlTop').getBoundingClientRect();"
              " return m ? Math.abs(m.getBoundingClientRect().right - b.right) < 0.5 : null;})()"), True,
         'Export shown nowhere: the menu under the top toolbar, at its right')
    t.load(settings=EMULE)
    t.js("shortcuts.export = 'P'")
    t.click('#emlClose')
    t.keys('p')
    t.eq(t.js("!!document.getElementById('emlMenu')"), False, 'the popup closed: nothing')
    t.eq(t.errors, [], 'no JavaScript error')


def test_copy_shortcut(t):
    """SF-9, SF-14: Ctrl+Alt+C copies the links that Download would send: the checked ones, those of the edit box in edit
    mode, those that the popup would check when it is closed (SF-5.5); its message in the band. Nothing on a page without
    ed2k links, not even a band."""
    t.load(settings=EMULE)
    t.js(EXPORT_CATCH)
    t.click('#l0')
    t.keys('c')
    copied = t.js('window.__copied')
    t.eq([len(copied), len(copied[-1][1].split('\n')) if copied else 0, t.js(STATUS_TEXT)], [1, 8, '8 link(s) copied'],
         'Ctrl+Alt+C: the 8 links checked copied, the message in the band')
    t.eq(t.js(VIEW), 'maximized', 'the popup still open')
    t.edit_mode()
    t.js("var e = document.getElementById('editbox'); e.value = e.value.split('\\n').slice(0, 2).join('\\n')")
    t.keys('c')
    t.eq(len(t.js('window.__copied')[-1][1].split('\n')), 2, 'edit mode: the links of the edit box')
    t.load(settings=EMULE, popup_mode=0)
    t.js(EXPORT_CATCH)
    t.keys('c')
    copied = t.js('window.__copied')
    t.eq([len(copied), len(copied[-1][1].split('\n')) if copied else 0, t.js(VIEW)], [1, 9, 'closed'],
         'the popup closed: the links it would check, the popup left closed')
    t.eq(t.js(STATUS_TEXT), '9 link(s) copied', 'the message in the band')
    t.load('__nolinks', settings=EMULE)
    t.js(EXPORT_CATCH)
    t.keys('c')
    t.eq([t.js('window.__copied'), t.js("!!document.getElementById('emlStatus')")], [[], False], 'no ed2k link: nothing, no band')
    t.eq(t.errors, [], 'no JavaScript error')


def test_removed_shortcuts(t):
    """SF-9: Ctrl+Alt+M, Ctrl+Alt+E and Ctrl+Alt+X do nothing any more (X is taken by Firefox); the menu of the userscript
    manager holds Settings, Help, Open Popup and the debug traces only."""
    t.load(settings=EMULE)
    for key in 'mex':
        t.keys(key)
        t.eq([t.js(VIEW), t.js('popupMode'), t.js("!!document.getElementById('emlMenu')")], ['maximized', 1, False],
             f'Ctrl+Alt+{key.upper()}: nothing')
    t.eq(sorted(t.js('Object.keys(window.__GM_menu)')), ['h', 'o', 's', 't'], 'the menu of the manager: its access keys')
    t.eq(t.errors, [], 'no JavaScript error')


SHORTCUT_TEXTS = """(function(){var t=function(s){var e=document.querySelector(s);return e?e.title:null;};
  return {checkAll: t('#checkall'), download: t('#emlTop .emlAdd'), downloadLabel: document.querySelector('#emlTop .emlAdd').innerHTML,
  edit: t('#emlEdit'), editLabel: document.getElementById('emlEdit').innerHTML, export: t('#emlExport'),
  settings: t('#emlTop .emlRight'), help: t('#emlHelpBtn'), min: t('#emlMin'), close: t('#emlClose')};})()"""


def test_shortcut_letters(t):
    """SF-9: the letters of the shortcuts, in the PARAM block (shortcuts): the tooltips, the help and the keys follow them;
    an action without a letter has none, one given a letter gets it (close, editMode, export); the letter underlined in a
    label that holds it."""
    t.load(settings=EMULE)
    t.eq(t.js('SHORTCUTS_DEFAULT'), {'checkAll': 'A', 'download': 'D', 'view': 'W', 'settings': 'S', 'help': 'H', 'open': 'O', 'copy': 'C'},
         'the letters by default')
    t.eq(t.js(SHORTCUT_TEXTS), {'checkAll': 'Check or uncheck every link (Ctrl+Alt+A)', 'download': 'Download the checked links (Ctrl+Alt+D)',
                                'downloadLabel': '<u>D</u>ownload', 'edit': 'Edit the links as text', 'editLabel': 'Edit mode',
                                'export': 'Export the checked links: copy them, or save them as an eMule collection, a CSV or a text file'
                                          '\nCtrl+Alt+C copies the links',
                                'settings': 'Settings (Ctrl+Alt+S)', 'help': 'Help (Ctrl+Alt+H)', 'min': 'Minimize (Ctrl+Alt+W)',
                                'close': 'Close'}, 'the tooltips by default')
    # other letters, as the PARAM block would give them: the popup drawn again
    t.js("shortcuts = {checkAll: '', download: 'L', view: 'V', settings: 'S', help: 'H', open: 'O', copy: '', close: 'Q',"
         " editMode: 'T', export: 'P'}; closePopup(); openButton();")
    shown = t.js(SHORTCUT_TEXTS)
    t.eq([shown['checkAll'], shown['download'], shown['downloadLabel'], shown['edit'], shown['editLabel'], shown['export'],
          shown['min'], shown['close']],
         ['Check or uncheck every link', 'Download the checked links (Ctrl+Alt+L)', 'Down<u>l</u>oad', 'Edit the links as text (Ctrl+Alt+T)',
          'Edi<u>t</u> mode', 'Export the checked links: copy them, or save them as an eMule collection, a CSV or a text file (Ctrl+Alt+P)',
          'Minimize (Ctrl+Alt+V)', 'Close (Ctrl+Alt+Q)'], 'the tooltips and the underlined letters follow')
    t.keys('h')
    t.eq(t.js(HELP_ROWS), [[True, s] for s in ('', '', '', '', 'Ctrl+Alt+L', 'Ctrl+Alt+T', 'Ctrl+Alt+P', 'Ctrl+Alt+S',
                                                 'Ctrl+Alt+H', 'Ctrl+Alt+V', 'Ctrl+Alt+Q', '')], 'the help follows')
    t.keys('h')
    t.keys('p')
    t.eq([t.js("document.getElementById('emlMenu').getAttribute('data-for')"), t.js("document.activeElement.getAttribute('data-menu')")],
         ['export', 'export-copy'], 'Ctrl+Alt+P: the menu of Export, Copy focused')
    t.keys('p')
    t.eq(t.js("!!document.getElementById('emlMenu')"), False, 'Ctrl+Alt+P again: closed')
    t.keys('t')
    t.eq(t.js('popupMode'), 2, 'Ctrl+Alt+T: edit mode')
    t.keys('a')
    t.keys('d')
    t.eq(t.dialogs, [], 'A and D: nothing')
    t.keys('v')
    t.eq(t.js(VIEW), 'minimized', 'Ctrl+Alt+V: minimized')
    t.keys('q')
    t.eq(t.js(VIEW), 'closed', 'Ctrl+Alt+Q: closed')
    t.eq(t.errors, [], 'no JavaScript error')


def test_export_in_menu(t):
    """SF-14, SF-2.14: Export put in the menu of the toolbars by the settings: the menu button in place of the buttons at the
    top right, the menu holding a heading Export and its commands after Edit mode, before Settings; a command chosen there."""
    t.load(settings=dict(EMULE, tbExportTop='menu', tbExportBottom='none'))
    t.js(EXPORT_CATCH)
    t.eq(t.js("getComputedStyle(document.getElementById('emlMenuBtn')).display != 'none'"), True, 'the menu button')
    t.click('#emlMenuBtn')
    t.eq(t.js(MENU_ROWS), EXPORT_ROWS + ['Settings', 'Help', 'Minimize', 'Close'], 'the commands of Export, then the buttons')
    t.eq(t.js("document.querySelector('#emlMenu .emlMenuHead').textContent"), 'Export', 'under a heading')
    t.click('#emlMenu [data-menu=export-csv]')
    t.eq([name[-4:] for name, _, _ in export_saved(t)], ['.csv'], 'the CSV saved from the menu')
    t.eq(t.errors, [], 'no JavaScript error')


def test_shortcuts_without_links(t):
    """SF-1.12: on a page without ed2k links, no shortcut opens a popup or raises an error."""
    for key in 'owcad':
        t.load('__nolinks', settings=EMULE)
        t.keys(key)
        t.eq(t.js(POPUP), [0, 0, 0], f'Ctrl+Alt+{key.upper()}: no popup')
        t.eq(t.errors, [], f'Ctrl+Alt+{key.upper()}: no JavaScript error')
    t.edit_mode()
    t.eq([t.js(POPUP), t.js('popupMode')], [[0, 0, 0], 1], 'Edit mode: no popup, mode unchanged')


def test_debug_traces(t):
    """SF-9: the debug traces are off on a new installation, and the menu entry
    "Toggle debug traces" switches them on and off, for the next pages too."""
    t.load(debug=None)
    t.eq([c for c in t.console if 'saveConfig()' in c], [], 'no trace on a new installation')
    t.menu('t')
    t.eq([t.dialogs, t.js("(document.querySelector('#emlStatus .emlStatusText') || {}).textContent"), t.js("document.getElementById('emlStatus').className")],
         [[], 'Emule Linker: debug traces on (see the browser console)', 'ok'], 'menu: traces switched on, told in the band, no alert')
    t.eq(t.gm('debug_mode'), 1, 'setting stored')
    t.console.clear()
    t.reload()
    t.check(t.traced('saveConfig() storing the settings'), 'traces shown on the next page')
    t.menu('t')
    t.eq([t.dialogs, t.js("(document.querySelector('#emlStatus .emlStatusText') || {}).textContent")], [[], 'Emule Linker: debug traces off'], 'menu: traces switched off, in the band')
    t.console.clear()
    t.reload()
    t.eq([c for c in t.console if 'saveConfig()' in c], [], 'no trace any more on the next page')


def test_internal_error(t):
    """An error that should never happen (an unknown state of the popup) is told in the band, in red until closed,
    translated, and traced, rather than in an alert of the browser (up to 0.14)."""
    t.load(settings=EMULE)
    t.js("popupMode = 7; addButton()")
    t.eq([t.dialogs, t.js("(document.querySelector('#emlStatus .emlStatusText') || {}).textContent"),
          t.js("(document.getElementById('emlStatus') || {}).className")],
         [[], 'Internal error of Emule Linker (popupMode=7): please report the problem', 'ko'], 'in the band, in red, no alert')
    t.check(t.traced('ERROR: popupMode=7'), 'traced')
    t.eq(t.errors, [], 'no JavaScript error')


def test_menu_entries(t):
    """SF-9: the userscript manager menu entries, called the way Tampermonkey calls them."""
    t.load(settings=EMULE)
    t.close_popup()
    t.press('Escape')
    try:
        t.menu('o')
        t.eq(t.js(POPUP), [1, 9, 0], 'menu "Open Popup" opens it, without reloading the page')
    except RuntimeError as e:
        t.check(False, 'menu "Open Popup" works', str(e).splitlines()[0])
    t.menu('h')
    t.check(t.js("!!document.getElementById('emlHelp')"), 'menu "Help" shows the help')
    t.menu('h')
    t.menu('s')
    t.check(t.settings_open(), 'menu "Settings" opens the settings dialog')
    t.eq(t.errors, [], 'no JavaScript error')


# ---- a huge number of links (SF-4.5) -----------------------------------------------------
def many_links(t, count):
    """Serve a page with that many valid ed2k links, at /__many."""
    h = 'ABCDEF1234567890ABCDEF1234567890'
    t.serve('/__many', '<!doctype html><meta charset="utf-8">' + ''.join(
        f'<a href="ed2k://|file|a-long-file-name-to-fill-the-popup-number-{i:05}.mp3|1048576|{h}|/">{i}</a> '
        for i in range(count)))


def test_many_links_normal_mode(t):
    """SF-4.5: with 1,000 links, the list of the popup is complete and its end reachable."""
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
    """SF-2.9: with many links only the list scrolls, both toolbars stay visible."""
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
              "var c = function (e) { var r = e.getBoundingClientRect(); return (r.top + r.bottom) / 2; };"
              "return Math.abs(c(bar.firstElementChild) - c(bar.lastElementChild)) < 1; })"),
         [True, True], 'the two halves of each toolbar on one line')


def test_many_links_edit_mode(t):
    """SF-4.5: with 1,000 links (about 108,000 characters), the edit box holds the whole
    list and has no maximum length: the user can still type in it."""
    many_links(t, 1000)
    t.load('__many', popup_mode=2)
    t.eq(t.dialogs, [], 'no alert')
    t.check(t.js("document.getElementById('editbox').value === eLinks.join('\\n')"),
            'whole list, identical', t.js("document.getElementById('editbox').value.length"))
    t.eq(t.js("document.getElementById('editbox').maxLength"), -1, 'no maximum length')
    t.js("var e = document.getElementById('editbox'); e.focus(); e.setSelectionRange(e.value.length, e.value.length)")
    before = t.js("document.getElementById('editbox').value.length")
    t.type_text('x')
    t.eq(t.js("document.getElementById('editbox').value.length"), before + 1, 'a character typed at the end is kept')
    t.eq(t.js(TOOLBARS)[:2], [True, True], 'both toolbars visible')


def test_old_maxlength_setting_ignored(t):
    """SF-4.5: a MaxLength value stored by a previous version is ignored, without any alert."""
    t.load(settings={'editMaxLength': 10000}, popup_mode=2)
    t.eq(t.dialogs, [], 'no alert')
    t.eq(t.js("document.getElementById('editbox').maxLength"), -1, 'no maximum length on the edit box')
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("!!document.getElementById('GM_config_field_editMaxLength')"), False, 'no MaxLength field any more')


def test_download_methods_in_settings(t):
    """SF-7: the download methods of the settings dialog, in this order and with these labels.
    Only the labels changed in 0.11: the stored value of a method chosen before is kept."""
    t.load(settings={'ed2kDlMethod': 'amule'})
    t.check(t.open_settings(), 'settings dialog opened')
    options = t.js("[].map.call(document.getElementById('GM_config_field_ed2kDlMethod').options,"
                   "function (o) { return [o.value, o.text]; })")
    t.eq(options, [['local', 'Local (your system default)'], ['emule', 'eMule (web)'],
                   ['amuleapi', 'aMule 3.x (amuleapi)'], ['amule', 'aMule 2.x (amuleweb)'],
                   ['mldonkey', 'MLDonkey (web)'], ['custom', 'Custom (post to your own server)']],
         'methods, labels and order')
    t.eq(t.js("document.getElementById('GM_config_field_ed2kDlMethod').value"), 'amule',
         'the method chosen before is still selected')
    t.eq([[r[1], r[3]] for r in t.js(SERVER_ROWS)][1], [True, 'aMule 2.x (amuleweb)'], 'its server checked, with its method')


# ---- links checked by default (SF-5.7) -------------------------------------------------
BLACKLIST = r'/^(?!.*\.emulecollection$)/i'      # the examples of the help of the field
WHITELIST = r'/\.(cbz|cbr|rar|zip)$/i'
COLLECTION = 'Guide Réseau été 2024.emulecollection'
FILTERED_TITLE = 'Not checked by default: its name does not match the filter of the settings'

# the rows of the popup: [file name, checked, greyed, tooltip]
FILTER_ROWS = ("[].map.call(document.querySelectorAll('#divBody tr'), function (r) {"
               "return [r.querySelector('a.ed2k').textContent, r.querySelector('input').checked,"
               " r.classList.contains('filtered'), r.title]; })")
# the "check all" boxes of the top and the bottom toolbars: [checked, mixed, disabled]
ALL_BOXES = ("[].map.call(document.querySelectorAll('#theDiv input.checkall'), function (b) {"
             "return [b.checked, b.indeterminate, b.disabled]; })")
CHECKED = "[].map.call(document.querySelectorAll('#divBody tr input'), function (b) { return b.checked; })"


def test_tab_order(t):
    """SF-3.6: the boxes of the links have the tab order of the list, 1 for the first one, the
    filtered ones included (once 1, 11, 21...: the index and 1 joined as text)."""
    t.load(settings=with_emule(checkFilter=BLACKLIST))
    t.eq(t.js("[].map.call(document.querySelectorAll('#divBody tr input'), function (b) { return b.getAttribute('tabindex'); })"),
         [str(i) for i in range(1, 10)], 'tab order 1 to 9')


def test_filter_blacklist(t):
    """SF-5.7: the blacklist example of the help: every link is checked but the eMule collection,
    still listed, unchecked, its name and its size greyed, with a tooltip; the "check all" boxes of
    both toolbars are mixed. The name is tested decoded (twice here)."""
    t.load(settings=with_emule(checkFilter=BLACKLIST))
    rows = t.js(FILTER_ROWS)
    t.eq(len(rows), 9, 'every link still listed')
    t.eq([r[0] for r in rows if not r[1]], [COLLECTION], 'only the collection unchecked')
    t.eq([r[0] for r in rows if r[2]], [COLLECTION], 'only its row greyed')
    t.eq(sorted({r[3] for r in rows}), ['', FILTERED_TITLE], 'the tooltip of its row only')
    t.eq(t.js("(function(){var r=document.querySelector('#divBody tr.filtered');"
              "return [getComputedStyle(r.querySelector('a.ed2k')).color, getComputedStyle(r.lastElementChild).color];})()"),
         ['rgb(153, 153, 153)', 'rgb(153, 153, 153)'], 'its name and its size greyed')
    t.eq(t.js("getComputedStyle(document.querySelector('#divBody tr:not(.filtered) a.ed2k')).color"),
         'rgb(0, 0, 0)', 'the other names in black')
    t.eq(t.js(ALL_BOXES), [[False, True, False], [False, True, False]], 'both boxes mixed, and enabled')


def test_filter_case_sensitive(t):
    """SF-5.7: written alone or without /i, the filter is case-sensitive: \\.CBZ$ matches no file of
    the page (example1.cbz in small letters); with /i, it checks example1.cbz."""
    for value in (r'\.CBZ$', r'/\.CBZ$/'):
        t.load(settings=with_emule(checkFilter=value))
        t.eq(t.js(CHECKED), [False] * 9, f'{value}: no link checked')
    t.load(settings=with_emule(checkFilter=r'/\.CBZ$/i'))
    t.eq([r[0] for r in t.js(FILTER_ROWS) if r[1]], ['example1.cbz'], '/\\.CBZ$/i: example1.cbz checked')


def test_filter_whitelist(t):
    """SF-5.7: the whitelist example of the help: only the cbz, cbr, rar and zip files are checked."""
    t.load(settings=with_emule(checkFilter=WHITELIST))
    rows = t.js(FILTER_ROWS)
    t.eq([r[0] for r in rows if r[1]], ['example1.cbz'], 'only the cbz file checked')
    t.eq(len([r for r in rows if r[2]]), 8, 'the 8 others greyed')
    t.eq(t.js(ALL_BOXES), [[False, True, False], [False, True, False]], 'both boxes mixed')
    t.load(settings=with_emule(checkFilter='/^nothing$/'))
    t.eq(t.js(CHECKED), [False] * 9, 'a filter that no name matches: every link unchecked')
    t.eq(t.js(ALL_BOXES), [[False, False, False], [False, False, False]], 'both boxes unchecked, not mixed')
    t.load(settings=EMULE)
    t.eq([t.js(CHECKED), t.js("document.querySelectorAll('#divBody tr.filtered').length")], [[True] * 9, 0],
         'no filter (default): every link checked, none greyed')
    t.eq(t.js(ALL_BOXES), [[True, False, False], [True, False, False]], 'both boxes checked')


def test_filter_duplicate_names(t):
    """SF-5.7 and SF-1.9: the filter tests the file name without the suffix added to a second file
    of the same name."""
    h = 'ABCDEF1234567890ABCDEF123456789'
    t.serve('/__duplicates', '<!doctype html><meta charset="utf-8"><title>duplicates</title>'
            + ''.join(f'<a href="ed2k://|file|{n}|1048576|{h}{i}|/">{n}</a> '
                      for i, n in enumerate(('a.emulecollection', 'a.emulecollection', 'b.cbz'))))
    t.load('__duplicates', settings=with_emule(checkFilter=r'/\.emulecollection$/'))
    t.eq([r[:2] for r in t.js(FILTER_ROWS)], [['a.emulecollection', True], ['a.emulecollection (1)', True], ['b.cbz', False]],
         'both collections checked, the suffix of the second one ignored')


def test_filter_stored_invalid(t):
    """SF-5.7: a filter that can not be read, stored anyway, is ignored with a trace: every link is
    checked, without an alert."""
    t.load(settings=with_emule(checkFilter=r'/\.(cbz|cbr$/i'))
    t.eq(t.dialogs, [], 'no alert')
    t.eq(t.js(CHECKED), [True] * 9, 'every link checked')
    t.check(t.traced('filter of the links checked by default ignored'), 'trace of saveConfig()')


def test_check_all_boxes(t):
    """SF-5.1 and SF-5.4: the "check all" boxes of both toolbars check or uncheck every link, a
    mixed one checks them all; they follow the boxes of the links. Disabled in edit mode, where the
    filter does not apply: the edit box lists every link."""
    t.load(settings=with_emule(checkFilter=BLACKLIST))
    t.click('#checkall')
    t.eq([t.js(CHECKED), t.js(ALL_BOXES)], [[True] * 9, [[True, False, False]] * 2],
         'the mixed top box clicked: every link checked, both boxes checked')
    t.click('#checkall2')
    t.eq([t.js(CHECKED), t.js(ALL_BOXES)], [[False] * 9, [[False, False, False]] * 2],
         'the bottom box clicked: every link unchecked, both boxes unchecked')
    t.click('#l0')
    t.eq(t.js(ALL_BOXES), [[False, True, False]] * 2, 'a link checked by hand: both boxes mixed')
    for i in range(1, 9):
        t.click(f'#l{i}')
    t.eq(t.js(ALL_BOXES), [[True, False, False]] * 2, 'every link checked by hand: both boxes checked')
    t.edit_mode()
    lines = t.js("document.getElementById('editbox').value.split('\\n')")
    t.eq([len(lines), any(COLLECTION in line for line in lines)], [9, True], 'edit mode: every link, the collection included')
    t.eq([b[2] for b in t.js(ALL_BOXES)], [True, True], 'both boxes disabled')
    t.edit_mode()
    t.eq([r[0] for r in t.js(FILTER_ROWS) if not r[1]], [COLLECTION], 'normal mode again: the filter applied again')


def test_settings_check_filter(t):
    """SF-8 and SF-8.10: the field Links checked by default, last of the Popup section, as wide as
    its help, in a monospace font; a filter that can not be read, or with the flag g or y, is
    refused under the field and nothing is saved; a right one is saved, and applied."""
    error = "(document.querySelector('#GM_config_checkFilter_var .error') || {}).textContent"
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_popupCols_var').nextElementSibling.id"), 'GM_config_checkFilter_var',
         'after the Max Popup Width')
    t.eq(t.js("document.getElementById('GM_config_checkFilter_field_label').textContent"), 'Links checked by default', 'label')
    t.eq(t.js("document.getElementById('GM_config_section_desc_4').textContent"),
         'How the popup is displayed, and the links it checks', 'description of the section')
    t.eq(t.js(f"{field('checkFilter')}.value"), '', 'empty by default')
    t.click('#GM_config_helpBtn')       # the help shown, to compare the widths
    t.eq(t.js("(function(){var f=document.getElementById('GM_config_field_checkFilter').getBoundingClientRect(),"
              "h=document.querySelector('#GM_config_checkFilter_var .help').getBoundingClientRect();"
              "return [Math.abs(f.left-h.left)<0.5, Math.abs(f.right-h.right)<0.5];})()"), [True, True], 'as wide as its help')
    t.check('Consolas' in t.js(f"getComputedStyle({field('checkFilter')}).fontFamily"), 'monospace font')
    for value, expected in ((r'/\.(cbz|cbr$/i', 'Not a valid regular expression: '),
                            (r'/\.cbz$/gi', 'The flags g and y are not allowed: each test would depend on the previous one'),
                            (r'/\.cbz$/y', 'The flags g and y are not allowed: each test would depend on the previous one')):
        t.set_field('checkFilter', value)
        t.js("document.getElementById('GM_config_saveBtn').click()")
        t.pump(0.5)
        t.check((t.js(error) or '').startswith(expected), f'{value}: refused under the field', t.js(error))
        t.eq([t.settings_open(), t.js("document.activeElement.id"), t.stored_settings().get('checkFilter')],
             [True, 'GM_config_field_checkFilter', None], f'{value}: focus on the field, nothing saved')
    t.eq(t.dialogs, [], 'no alert')
    t.set_field('checkFilter', WHITELIST)
    t.save_settings()
    t.eq(t.stored_settings().get('checkFilter'), WHITELIST, 'saved')
    t.eq([r[0] for r in t.js(FILTER_ROWS) if r[1]], ['example1.cbz'], 'applied after the reload')


def test_settings_help_code(t):
    """SF-8.3: in the helps, the code (addresses, values, regular expressions) is in a monospace
    font; the tooltips show the same text, without the backquotes that mark it."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    code = ("(function(n){return [].map.call(document.querySelectorAll('#GM_config_'+n+'_var .help code'),"
            "function (c) { return c.textContent; });})")
    t.eq(t.js(f"{code}('checkFilter')"), ['/expression/i', BLACKLIST, WHITELIST], 'Links checked by default: the expressions')
    t.eq(t.js(f"{code}('emuleUrl')"), ['http://127.0.0.1:4711/', '/'], 'Server URL: the address')
    t.eq(t.js(f"{code}('emuleUser')"), ['admin'], 'User: its default value')
    t.eq(t.js(f"{code}('emuleCat')"), ['name=value', ';', '*', '0', '*default=0;Video=2', '*Audio=audio;Video=Video', ';', '\\;'],
         'Category: the values')
    t.check('Consolas' in t.js("getComputedStyle(document.querySelector('#GM_config .help code')).fontFamily"), 'monospace font')
    t.check('Consolas' not in t.js("getComputedStyle(document.querySelector('#GM_config_checkFilter_var .help')).fontFamily"),
            'the rest of the help in the font of the dialog')
    t.eq(t.js("[].filter.call(document.querySelectorAll('#GM_config .help'), function (h) {"
              "return h.textContent.indexOf('`') >= 0; }).length"), 0, 'no backquote shown')
    tooltip = t.js("document.getElementById('GM_config_checkFilter_var').title")
    t.check('case-insensitive: /expression/i.' in tooltip and '`' not in tooltip, 'the tooltip without backquotes', tooltip)
