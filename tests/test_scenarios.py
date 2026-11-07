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
    """SF-6.5: an empty Category setting raises one alert, no longer stops the script,
    and the corrected value is stored so that the alert does not come back (SF-8.7)."""
    t.load(settings=with_emule(emuleCat=''))
    t.eq(len(t.dialogs), 1, 'one alert')
    t.check(t.dialogs and 'No valid category' in t.dialogs[0], 'it is the category alert', t.dialogs)
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


def script_version():
    with open(os.path.join(ROOT, 'GM_EmuleLinker.user.js'), encoding='utf-8') as f:
        return re.search(r'^// @version\s+(\S+)', f.read(), re.M).group(1)


def field(name):
    return f"document.getElementById('GM_config_field_{name}')"


def test_settings_dialog_look(t):
    """SF-8.1, SF-8.3, SF-8.8 and SF-8.11: title with the version, on the light blue of the toolbars
    of the popup (I-2), the help of a field shown under it when it has the focus, masked password,
    backdrop, Escape to close."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_header').firstChild.textContent"),
         f'Emule Linker {script_version()} — Settings', 'title with the version')
    t.eq(t.js("getComputedStyle(document.getElementById('GM_config_header')).backgroundColor"),
         t.js("getComputedStyle(document.getElementById('emlTop')).backgroundColor"), 'title on the color of the toolbars')
    t.eq(t.js("getComputedStyle(document.getElementById('GM_config_header')).backgroundColor"), 'rgb(232, 241, 251)', 'light blue')
    tooltips = "document.querySelectorAll('#GM_config .config_var[title]').length"
    t.eq(t.js("document.querySelectorAll('#GM_config .config_var .help').length"), 19,
         'a help for each field (User included, 0.12; Links checked by default, 0.13; Language, Default popup view, '
         'Show a message when the popup is closed, Show the category list, Show the server list, '
         'Popup position and Popup scrolling in place of Popup Position, 0.14)')
    t.eq(t.js(tooltips), 19, 'helps hidden: each one is the tooltip of its row')
    shown = ("[].filter.call(document.querySelectorAll('#GM_config .help'), function (h) {"
             "return getComputedStyle(h).display != 'none'; }).length")
    help_btn = "document.getElementById('GM_config_helpBtn').title"
    t.eq([t.js(shown), t.js(help_btn)], [0, 'Display inline help'], 'helps hidden at first')
    t.js(f"{field('emuleCat')}.focus()")
    t.eq(t.js(shown), 0, 'nothing shown on focus: the fields do not move')
    t.click('#GM_config_helpBtn')
    t.eq([t.js(shown), t.js(help_btn)], [19, 'Hide inline help'], 'Help button: every help shown')
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
    t.eq(t.js(shown), 19, 'the choice is kept at the next opening')
    t.click('#GM_config_helpBtn')
    t.eq([t.js(shown), t.js(help_btn), t.gm('settings_help'), t.js(tooltips)], [0, 'Display inline help', 0, 19],
         'Help button again: hidden, stored, tooltips back')
    t.eq([t.js(f"{field(n)}.size") for n in ('emuleUrl', 'emuleCat', 'popupHeight', 'editRow')],
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
              'emuleCat': '*Video=2;Audio=1', 'popupHeight': 600, 'checkFilter': r'/\.cbz$/i'}
    marked = "[].map.call(document.querySelectorAll('#GM_config .config_var.changed'), function (r) { return r.id; })"
    notice = "(document.getElementById('GM_config_notice') || {}).textContent"
    t.load(settings=custom)
    t.check(t.open_settings(), 'settings dialog opened')
    t.check(t.js("!!document.getElementById('GM_config_resetBtn')"), 'Reset button')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq([[r[2], r[1]] for r in t.js(SERVER_ROWS)], [['Local', True]], 'Local checked, no server')
    t.eq([t.js(EDITED), t.js(f"{field('popupHeight')}.value"), t.js(f"{field('checkFilter')}.value")], [None, '800', ''],
         'no field displayed, default sizes, no filter')
    t.eq(sorted(t.js(marked)), ['GM_config_checkFilter_var', 'GM_config_ed2kDlMethod_var', 'GM_config_popupHeight_var'],
         'servers, height and filter highlighted')
    t.check((t.js(notice) or '').startswith('3 settings set back to their default value'), 'notice', t.js(notice))
    t.eq(t.stored_settings(), custom, 'nothing saved')
    t.js("document.getElementById('GM_config_undoBtn').click()")
    t.eq([[r[2], r[1]] for r in t.js(SERVER_ROWS)], [['Local', False], ['aMule 3.x (amuleapi)', True]], 'Undo: the server back')
    t.eq([t.js(f"{field(n)}.value") for n in ('emuleUrl', 'emulePwd', 'emuleCat', 'popupHeight', 'checkFilter')],
         ['http://192.168.1.10:4711/', 'secret', '*Video=2;Audio=1', '600', r'/\.cbz$/i'], 'Undo: its settings back')
    t.eq([t.js(marked), t.js(notice)], [[], None], 'Undo: no highlight, no notice')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.save_settings()
    t.eq([t.stored_settings().get(k) for k in ('ed2kDlMethod', 'emulePwd', 'popupHeight', 'checkFilter')], ['local', '', 800, ''],
         'Reset then Save: default values stored')
    t.eq(stored_servers(t)['list'], [], 'no server')


def test_settings_checked_before_saving(t):
    """SF-8.10: a wrong value is shown under its field, without an alert, and nothing is saved;
    once corrected, the settings are saved."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.set_field('emuleCat', ';;')
    t.set_field('popupHeight', '20')
    t.set_field('popupWidth', 'abc')
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(0.5)
    t.eq(t.dialogs, [], 'no alert')
    t.check(t.settings_open(), 'the dialog stays open')
    t.eq(t.stored_settings(), EMULE, 'nothing saved')
    errors = t.js("[].map.call(document.querySelectorAll('#GM_config .error'), function (e) {"
                  "return e.parentNode.id + ': ' + e.textContent; })")
    t.check(len(errors) == 3, 'three errors shown', errors)
    t.check(all(any(e.startswith(f'GM_config_{n}_var') for e in errors) for n in ('emuleCat', 'popupHeight', 'popupWidth')),
            'each one under its field', errors)
    t.eq(t.js("document.activeElement.id"), 'GM_config_field_emuleCat', 'focus on the first wrong field')
    t.set_field('emuleCat', '*default=0;Video=2')
    t.set_field('popupHeight', '0')
    t.set_field('popupWidth', '600')
    t.save_settings()
    t.eq(t.dialogs, [], 'no alert')
    t.eq([t.stored_settings().get(k) for k in ('emuleCat', 'popupHeight', 'popupWidth')],
         ['*default=0;Video=2', 0, 600], 'saved once corrected')


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
    t.keys('c')
    t.eq(t.js(POPUP), [0, 0, 0], 'closed on this page')
    t.reload()
    t.eq(t.js(POPUP), [1, 9, 0], 'open with its list on the next page')
    t.keys('m')
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
    """SF-9: Ctrl+Alt+C closes the popup, Ctrl+Alt+O opens it again, once."""
    t.load(settings=EMULE)
    t.keys('c')
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
BAR = ("(function(id){return [].map.call(document.getElementById(id).children,function(e){"
       "var r=e.getBoundingClientRect();return [e.id||e.className,r.left,r.top,r.width,r.height];});})")


def test_toggle_with_ctrl_alt_x(t):
    """SF-9 and I-2: Ctrl+Alt+X switches the popup maximized, minimized, closed, in turn, never
    duplicating it, starting from a popup closed at load (where it used to be duplicated)."""
    t.load(settings=EMULE, popup_mode=0)
    t.eq(t.js(VIEW), 'closed', 'closed at load')
    for expected in ('maximized', 'minimized', 'closed', 'maximized', 'minimized'):
        t.keys('x')
        t.eq(t.js(VIEW), expected, f'after Ctrl+Alt+X: {expected}')
    t.menu('x')
    t.eq(t.js(VIEW), 'closed', 'menu "Switch view": closed')
    t.eq(t.errors, [], 'no JavaScript error')


def test_toolbars(t):
    """SF-2.7 and I-2: the controls of both toolbars, in the order of the mockup, all 22 px high and
    on one line; the icons at the right of the top one; the category and Download at the right of the
    bottom one; every checkbox of the popup, toolbars and list, in one column, and the file names
    aligned on the counters. EMULE offers two servers, Local and eMule: the server lists are shown (I-6)."""
    t.load(settings=EMULE)
    top, bottom = t.js(BAR + "('emlTop')"), t.js(BAR + "('emlBottom')")
    t.eq([c[0] for c in top], ['checkall', 'emlCount', 'srv', 'cat', 'emlAdd', 'emlIcon emlRight', 'emlHelpBtn', 'emlMin', 'emlClose'],
         'top toolbar: box, counter, server, category, Download, settings, help, minimize, close')
    t.eq([c[0] for c in bottom], ['checkall2', 'emlCount', 'emlEdit', 'srv2', 'cat2', 'emlAdd'],
         'bottom toolbar: box, counter, Edit mode, server, category, Download')
    t.eq(t.js("[].map.call(document.querySelectorAll('#emlTop button'),function(b){"
              "return (b.getAttribute('data-icon')||b.textContent)+' | '+b.title;})"),
         ['Download | Download the checked links (Ctrl+Alt+D)', 'settings | Settings (Ctrl+Alt+S)', 'help | Help (Ctrl+Alt+H)',
          'minimize | Minimize (Ctrl+Alt+X)', 'close | Close (Ctrl+Alt+C)'], 'labels (icons) and tooltips of the top toolbar')
    for name, bar in (('top', top), ('bottom', bottom)):
        controls = [c for c in bar if c[0] not in ('checkall', 'checkall2', 'emlCount')]
        t.eq(sorted({round(c[4], 1) for c in controls}), [22], f'{name} toolbar: every control 22 px high')
        t.eq(len({round(c[2], 1) for c in controls}), 1, f'{name} toolbar: on one line')
        box, count = bar[0], bar[1]
        centers = [c[2] + c[4] / 2 for c in (box, count, controls[0])]
        t.check(max(centers) - min(centers) < 1, f'{name} toolbar: box and counter centered on the controls', centers)
    t.eq(t.js("document.querySelectorAll('#theDiv .emlIcon')[0].getBoundingClientRect().width"), 22, 'square icons')
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
    """I-2: each toolbar is centered between the border of the popup and the line that separates it
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
  return {controls: q('#theDiv .toolbar button, #theDiv .toolbar select'), boxes: q('#theDiv input.smallcheck'),
          rows: q('#divBody tr'), bars: q('#theDiv .toolbar'),
          fonts: [].map.call(document.querySelectorAll('#theDiv .toolbar button, #theDiv .toolbar select, #theDiv .emlCount'),
                             function(e){return getComputedStyle(e).fontSize;})};
})()"""


def test_sizes_kept_from_the_page(t):
    """SF-2.6 and I-2: the sizes of the popup are its own, whatever the styles of the page (a forum
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
    """I-2, as in the mockup: the checkboxes in one column; the file names on the counters; the list
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
    """I-2: the counter is as wide as its widest value on the page (total/total), its digits all of a
    width: checking or unchecking links moves nothing; 6 px between the counter and what follows."""
    links = ''.join(f'<div><a href="ed2k://|file|file{i:02d}.cbz|{i}048576|{i:02d}BCDEF1234567890ABCDEF12345678|/">f</a></div>'
                    for i in range(1, 13))
    t.serve('/__twelve', '<!doctype html><meta charset="utf-8"><title>twelve links</title>' + links)
    t.load('__twelve', settings=EMULE)
    place = "(function(){var c=document.querySelector('#emlTop .emlCount'),r=document.createRange();r.selectNodeContents(c);" \
            "return [r.getBoundingClientRect().right, c.nextElementSibling.getBoundingClientRect().left];})()"
    full, list_left = t.js(place)
    t.check(abs(list_left - full - 6) < 0.5, '6 px after 12/12', (full, list_left))
    for i in range(9):
        t.click(f'#l{i}')
    t.eq(t.js("document.querySelector('#emlTop .emlCount').textContent"), '3/12', '3/12')
    t.check(abs(t.js(place)[1] - list_left) < 0.5, 'the list has not moved', (t.js(place), list_left))
    t.eq(t.errors, [], 'no JavaScript error')


ICONS = """(function(){return [].map.call(document.querySelectorAll('#emlTop button.emlIcon'),function(b){
  var s=b.querySelector('svg'), r=b.getBoundingClientRect(), i=s?s.getBoundingClientRect():null;
  return [b.getAttribute('data-icon'), i ? Math.abs((i.top+i.bottom)/2-(r.top+r.bottom)/2) : null,
          i ? Math.abs((i.left+i.right)/2-(r.left+r.right)/2) : null, getComputedStyle(b).color];});})()"""


def test_icons(t):
    """I-2: the icons of the top toolbar are drawn (SVG), centered in their buttons whatever the fonts;
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
    """I-2: the toolbars are separated from the list by two lines that do not scroll with it, from one
    side of the frame to the other; none in edit mode, where the frame of the edit box separates."""
    many_links(t, 60)
    t.load('__many', settings=EMULE)
    lines = t.js(LINES)
    t.eq([lines['hr'], lines['top'], lines['bottom']], [0, '1px solid', '1px solid'], 'two lines, the borders of the list')
    t.check(abs(lines['left']) < 0.5 and abs(lines['right']) < 0.5, 'from one side of the frame to the other', lines)
    t.js("document.getElementById('divBody').scrollTop=300")
    t.pump(0.2)
    t.eq(t.js(LINES)['top'], '1px solid', 'still there once the list scrolled')
    t.keys('m')
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
    """I-2: a shadow on the edge of the list where links are hidden: at the bottom when the list is at
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
    t.keys('m')
    t.eq(t.js(SHADOWS), [], 'edit mode: no shadow')
    t.eq(t.errors, [], 'no JavaScript error')


def test_counter(t):
    """I-2: the counters tell the links that Download sends: the checked ones out of the links of the
    page, in both toolbars; in edit mode, the links of the text, as typed."""
    counters = "[].map.call(document.querySelectorAll('#theDiv .emlCount'),function(c){return c.textContent;})"
    t.load(settings=EMULE)
    t.eq(t.js(counters), ['9/9', '9/9'], 'every link checked')
    t.click('#l3')
    t.eq(t.js(counters), ['8/9', '8/9'], 'one link unchecked')
    t.keys('m')
    t.eq(t.js(counters), ['9/9', '9/9'], 'edit mode: the links of the text')
    t.js("var e=document.getElementById('editbox');e.value=e.value.split('\\n').slice(2).join('\\n');"
         "e.dispatchEvent(new Event('input'))")
    t.eq(t.js(counters), ['7/9', '7/9'], 'edit mode: two lines removed')
    t.eq(t.errors, [], 'no JavaScript error')


def test_minimize(t):
    """I-2: the minimize button shows the top toolbar only, at the same width: nothing moves in it;
    the list and the bottom toolbar are only hidden, the checked links kept; maximize shows them again.
    The same with the edit box, its text kept."""
    t.load(settings=EMULE)
    t.click('#l2')
    before = t.js(BAR + "('emlTop')")
    width = t.js("document.getElementById('theDiv').getBoundingClientRect().width")
    t.click('#emlMin')
    t.eq(t.js(VIEW), 'minimized', 'minimized')
    t.eq(t.js("document.getElementById('emlMin').getAttribute('data-icon')+' | '+document.getElementById('emlMin').title"),
         'maximize | Maximize (Ctrl+Alt+X)', 'the button maximizes now')
    after = t.js(BAR + "('emlTop')")
    t.check(all(abs(a[1] - b[1]) < 0.5 and abs(a[2] - b[2]) < 0.5 for a, b in zip(before, after)),
            'nothing moved in the top toolbar', (before, after))
    t.check(abs(t.js("document.getElementById('theDiv').getBoundingClientRect().width") - width) < 0.5, 'same width')
    t.click('#emlMin')
    t.eq(t.js(VIEW), 'maximized', 'maximized again')
    t.eq(t.js("document.getElementById('l2').checked"), False, 'the unchecked link still unchecked')
    t.keys('m')
    t.js("document.getElementById('editbox').value='ed2k://|file|kept.avi|1|0123456789ABCDEF0123456789ABCDEF|/'")
    t.click('#emlMin')
    t.eq(t.js(VIEW), 'minimized', 'edit mode minimized')
    t.click('#emlMin')
    t.eq(t.js("document.getElementById('editbox').value"), 'ed2k://|file|kept.avi|1|0123456789ABCDEF0123456789ABCDEF|/',
         'the edited text kept')
    t.eq(t.errors, [], 'no JavaScript error')


def test_default_view_minimized(t):
    """SF-10.2 and I-2: with the default view Minimized, the popup opens minimized, its top toolbar
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
    """I-2: Ctrl+Alt+A (and the menu entry) checks or unchecks every link, as the box of the top
    toolbar, and sends nothing; nothing in edit mode, where there is no box to check."""
    checked = "[].filter.call(document.querySelectorAll('#divBody input.smallcheck'),function(b){return b.checked;}).length"
    t.load(settings=EMULE)
    t.keys('a')
    t.eq(t.js(checked), 0, 'Ctrl+Alt+A: every link unchecked')
    t.menu('a')
    t.eq(t.js(checked), 9, 'menu: every link checked again')
    t.click('#l0')
    t.keys('a')
    t.eq(t.js(checked), 9, 'Ctrl+Alt+A on a mixed box: every link checked')
    t.eq(t.dialogs, [], 'nothing sent: no alert')
    t.keys('m')
    t.keys('a')
    t.eq(t.js("document.querySelectorAll('#editbox').length"), 1, 'edit mode: nothing changes')
    t.eq(t.errors, [], 'no JavaScript error')


def test_category_lists(t):
    """I-2: the category lists of both toolbars show the same category, chosen in either one."""
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2;Audio=1'))
    t.js("var s=document.getElementById('cat2');s.value='1';s.dispatchEvent(new Event('change'))")
    t.eq([t.js("document.getElementById('cat').value"), t.js("emuleCat.filter(function(c){return c.select==1;})[0].value")],
         ['1', '1'], 'chosen at the bottom: the top list and the category sent follow')
    t.eq(t.errors, [], 'no JavaScript error')


CAT_LISTS = """[].map.call(document.querySelectorAll('#theDiv select.emlCat'),function(s){
  return [s.id, s.disabled, Math.round(s.getBoundingClientRect().width*10)/10, s.title];})"""
LONG_CATEGORY = 'Comics and graphic novels (French)'


def test_category_list_grayed(t):
    """I-2: the category lists are grayed out when the server has fewer than two categories."""
    t.load(settings=dict(EMULE, emuleCat='*default=0'))
    t.eq([c[:2] for c in t.js(CAT_LISTS)], [['cat', True], ['cat2', True]], 'one category: both lists grayed out')
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2'))
    t.eq([c[:2] for c in t.js(CAT_LISTS)], [['cat', False], ['cat2', False]], 'two categories: both lists enabled')
    t.eq(t.errors, [], 'no JavaScript error')


def test_category_list_width(t):
    """I-2: the category lists are 140 px wide at most (categoryListMaxWidth): a long name does not
    widen the popup, it is cut, and the tooltip of the lists tells the category chosen, whole. They are
    100 px wide at least (categoryListMinWidth): short names of another server (I-6) move nothing."""
    t.load(settings=dict(EMULE, emuleCat='*default=0;Video=2'))
    short = t.js(CAT_LISTS)
    t.eq([c[2] for c in short], [100, 100], 'short names: 100 px')
    t.eq(t.js('categoryListMinWidth'), 100, 'a parameter of the script')
    t.load(settings=dict(EMULE, emuleCat='*Default=0;Audio=1;Documents=4;Software=5'))
    medium = t.js(CAT_LISTS)
    t.check(all(100 <= c[2] < 140 for c in medium), 'medium names: between 100 and 140 px', medium)
    t.check(all(c[3].startswith('Category: default') for c in short), 'the category chosen in the tooltip', short)
    t.load(settings=dict(EMULE, emuleCat=f'*{LONG_CATEGORY}=3;default=0;Video=2'))
    lists = t.js(CAT_LISTS)
    t.eq([c[2] for c in lists], [140, 140], 'a long name: 140 px')
    t.check(all(c[3].startswith('Category: ' + LONG_CATEGORY) for c in lists), 'the whole name in the tooltip', lists)
    t.eq(t.js('categoryListMaxWidth'), 140, 'a parameter of the script')
    t.js("var s=document.getElementById('cat');s.value='2';s.dispatchEvent(new Event('change'))")
    t.check(all(c[3].startswith('Category: Video') for c in t.js(CAT_LISTS)), 'another category chosen: the tooltips follow',
            t.js(CAT_LISTS))
    t.eq(t.errors, [], 'no JavaScript error')


def test_show_category_list_setting(t):
    """SF-8 and I-2: the setting "Show the category list" of the Popup section, checked by default;
    unchecked, the toolbars have no category list, Download follows the counter, and the links are sent
    to the default category of the server."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_showCategories_field_label').textContent"), 'Show the category list', 'label')
    t.eq(t.js("[document.getElementById('GM_config_field_showCategories').type, document.getElementById('GM_config_field_showCategories').checked]"),
         ['checkbox', True], 'a checkbox, checked by default')
    t.eq(t.js("document.getElementById('GM_config_showCategories_var').closest('.section_header_holder')"
              ".querySelector('.section_header').textContent"), 'Popup', 'in the Popup section')
    help = t.js("document.querySelector('#GM_config_showCategories_var .help').textContent")
    t.check('grayed out' in help and 'fewer than two categories' in help, 'the help tells when it is grayed out', help)
    t.js("document.getElementById('GM_config_field_showCategories').checked = false")
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js("[document.getElementById('GM_config_field_showCategories').checked,"
              " document.getElementById('GM_config_showCategories_var').classList.contains('changed')]"),
         [True, True], 'Reset: checked again, highlighted')
    t.js("document.getElementById('GM_config_field_showCategories').checked = false")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq(t.stored_settings().get('showCategories'), False, 'unchecked, saved')
    t.load(settings=dict(EMULE, emuleCat='default=0;*Video=2', showCategories=False))
    t.eq(t.js(CAT_LISTS), [], 'no category list')
    top = t.js(BAR + "('emlTop')")
    t.eq([c[0] for c in top][:4], ['checkall', 'emlCount', 'srv', 'emlAdd'], 'top toolbar: Download after the server list')
    t.eq(t.js('getSelectedCat()'), '2', 'the default category of the server is sent')
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
    """I-6: a server list in both toolbars, before the category list, when it offers two choices at
    least, Local included: Local, then the servers in the order of the settings; each page starts on the
    server checked in the settings. 140 px wide at most (serverListMaxWidth), the tooltip tells the
    server chosen, whole."""
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
    t.eq([c[0] for c in t.js(BAR + "('emlBottom')")][:6], ['checkall2', 'emlCount', 'emlEdit', 'srv2', 'cat2', 'emlAdd'],
         'bottom toolbar: the server list before the category list')
    t.eq(t.js("['srv2','cat2'].map(function(id){return document.getElementById(id).classList.contains('emlRight');})"),
         [True, False], 'bottom toolbar: the server list starts the group at the right')
    t.load(settings=dict(EMULE, showCategories=False), servers=None)
    t.eq([c[0] for c in t.js(BAR + "('emlBottom')")][:5], ['checkall2', 'emlCount', 'emlEdit', 'srv2', 'emlAdd'],
         'no category list: Download follows the server list')
    servers = two_servers(name='The big network attached storage of the attic')
    t.load(settings=settings_of(servers), servers=servers)
    lists = t.js(SRV_LISTS)
    t.eq([s[4] for s in lists], [140, 140], 'a long name: 140 px')
    t.check(all(s[5].startswith('Server: The big network attached storage of the attic,') for s in lists),
            'the whole name in the tooltip', lists)
    t.eq(t.js('serverListMaxWidth'), 140, 'a parameter of the script')
    t.keys('x')
    t.eq(t.js("[].map.call(document.querySelectorAll('#theDiv select.emlSrv'),function(s){return [s.id, s.getClientRects().length>0];})"),
         [['srv', True], ['srv2', False]], 'minimized: the server list of the top toolbar')
    t.eq(t.errors, [], 'no JavaScript error')


def test_server_list_choice(t):
    """I-6: the server chosen in the popup receives the links of this page only: both lists show it,
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
    """I-6: the list of the servers is read only on a page with ed2k links, where the popup can show it;
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
    """SF-8 and I-6: the setting "Show the server list" of the Popup section, after "Show the category
    list", checked by default; unchecked, the toolbars have no server list."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_showServerList_field_label').textContent"), 'Show the server list', 'label')
    t.eq(t.js("[document.getElementById('GM_config_field_showServerList').type, document.getElementById('GM_config_field_showServerList').checked]"),
         ['checkbox', True], 'a checkbox, checked by default')
    t.eq(t.js("document.getElementById('GM_config_showCategories_var').nextElementSibling.id"), 'GM_config_showServerList_var',
         'after "Show the category list"')
    help = t.js("document.querySelector('#GM_config_showServerList_var .help').textContent")
    t.check('two choices' in help and 'Local' in help and 'this page only' in help, 'the help tells when it is shown', help)
    t.js("document.getElementById('GM_config_field_showServerList').checked = false")
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq(t.js("[document.getElementById('GM_config_field_showServerList').checked,"
              " document.getElementById('GM_config_showServerList_var').classList.contains('changed')]"),
         [True, True], 'Reset: checked again, highlighted')
    t.js("document.getElementById('GM_config_field_showServerList').checked = false")
    t.js("document.getElementById('GM_config_saveBtn').click()")
    t.pump(1)
    t.eq(t.stored_settings().get('showServerList'), False, 'unchecked, saved')
    servers = two_servers()
    t.load(settings=dict(settings_of(servers), showServerList=False), servers=servers)
    t.eq(t.js(SRV_LISTS), [], 'no server list')
    t.eq([c[0] for c in t.js(BAR + "('emlTop')")][:4], ['checkall', 'emlCount', 'cat', 'emlAdd'], 'top toolbar: as before')
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
    """I-3: closing the popup (its Close button, Ctrl+Alt+C, the menu) shows a box inside the page,
    centered in the window, on a backdrop as the settings dialog, so that it cannot be missed: the page
    cannot be clicked behind it. It tells how to open the popup again; OK, its Close button or Escape
    close it, with its backdrop, and so does the popup opened again. Not with Ctrl+Alt+X, which goes through the views, nor at the load of a
    page whose default view is Closed, nor when no popup was open."""
    t.load(settings=EMULE)
    t.eq(t.js(MSG), None, 'no message while the popup is open')
    t.click('#emlClose')
    msg = t.js(MSG)
    t.check(msg is not None, 'the Close button: a message')
    if msg:
        t.eq(msg[0], 'Emule Linker — Popup closed', 'its title, as the one of the settings dialog')
        t.check(all(w in msg[1] for w in ('Ctrl+Alt+O', 'Ctrl+Alt+X', 'Open Popup', 'Tampermonkey', 'Default popup view')),
                'how to open the popup again, the menu of the userscript manager, the next pages', msg[1])
        t.eq(t.js("[].map.call(document.querySelectorAll('#emlMsg .emlMsgText li'), function (li) { return li.textContent; })"),
             ['press Ctrl+Alt+O, or', 'press Ctrl+Alt+X, or', 'choose Open Popup in the menu of Tampermonkey.'],
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
    t.keys('c')
    t.check(t.js(MSG) is not None, 'Ctrl+Alt+C: a message')
    t.press('Escape')
    t.eq([t.js(MSG), t.js(MSG_BACKDROP)], [None, None], 'Escape: gone, with its backdrop')
    t.keys('o')
    t.menu('c')
    t.check(t.js(MSG) is not None, 'menu Close Popup: a message')
    t.click('#emlMsgClose')
    t.eq(t.js(MSG), None, 'its Close button: gone')
    t.keys('o')
    t.keys('c')
    t.keys('o')
    t.eq([t.js(MSG), t.js(MSG_BACKDROP), t.js(VIEW)], [None, None, 'maximized'], 'the popup opened again: the message gone')
    t.keys('c')
    t.keys('c')
    t.eq(t.js("[document.querySelectorAll('#emlMsg').length, document.querySelectorAll('#emlMsgBackdrop').length]"), [1, 1],
         'Ctrl+Alt+C again, the popup closed: one message')
    t.press('Escape')
    t.keys('o')
    t.keys('x')
    t.keys('x')
    t.eq([t.js(MSG), t.js(VIEW)], [None, 'closed'], 'Ctrl+Alt+X: closed, no message')
    t.eq(t.stored_settings().get('closeMessage'), None, 'nothing stored')
    t.load(settings=dict(EMULE, popupScroll='static'))
    t.click('#emlClose')
    t.eq((t.js(MSG) or [None] * 4)[2:], [True, 'fixed'], 'the popup scrolling with the page: the message centered in the window all the same')
    t.load(settings=EMULE, popup_mode=0)
    t.eq(t.js(MSG), None, 'default view Closed: no message at load')
    t.eq(t.errors, [], 'no JavaScript error')


def test_close_message_dont_display(t):
    """I-3: "Don't display again", checked when the message is closed (OK, its Close button or
    Escape), unchecks the setting at once: no message any more, on this page and the next ones; the
    other settings stay as they were."""
    t.load(settings=EMULE)
    t.click('#emlClose')
    t.click('#emlMsgOff')
    t.click('#emlMsgOk')
    t.eq(t.stored_settings(), dict(EMULE, closeMessage=False), 'stored at once, the other settings as they were')
    t.keys('o')
    t.keys('c')
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
    """SF-8.19 and I-3: the setting "Show a message when the popup is closed" of the General section,
    after the default view, checked by default; unchecked, no message; checked again, the message is back."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_closeMessage_field_label').textContent"),
         'Show a message when the popup is closed', 'label')
    t.eq(t.js("[document.getElementById('GM_config_field_closeMessage').type, document.getElementById('GM_config_field_closeMessage').checked]"),
         ['checkbox', True], 'a checkbox, checked by default')
    t.eq(t.js("document.getElementById('GM_config_popupView_var').nextElementSibling.id"), 'GM_config_closeMessage_var',
         'in the General section, after Default popup view')
    help = t.js("document.querySelector('#GM_config_closeMessage_var .help').textContent")
    t.check('Ctrl+Alt+C' in help and "Don't display again" in help, 'the help tells when it is shown, and the box of the message', help)
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
    """I-5: the help built into the script, from the ? button of the top toolbar (between Settings and
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
    t.eq(t.js(HELP_ROWS), [[True, s] for s in ('Ctrl+Alt+A', '', '', '', 'Ctrl+Alt+D', 'Ctrl+Alt+M', 'Ctrl+Alt+S',
                                                 'Ctrl+Alt+H', 'Ctrl+Alt+X', 'Ctrl+Alt+C')],
         'each control of the toolbars drawn, with its shortcut')
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
    """I-5: the help is centered in the space at the right of the popup, so that both can be read at
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
        t.keys('c')
        t.press('Escape')
        t.keys('h')
        h = t.js(HELP)
        x, y = middle(h)
        t.check(abs(x - h['width'] / 2) < 1, 'the popup closed: centered in the window', h)
    finally:
        t.clear_viewport()
    t.eq(t.errors, [], 'no JavaScript error')


def test_help_drag(t):
    """I-5: the help is moved by dragging its title bar (a "move" cursor on it), within the window; not
    from its Close button, and without selecting text. Its place is kept for the page: closed and opened
    again, it comes back there, and a smaller window only brings it back into it. The next page places
    it automatically again."""
    def place(h):
        return [round(h['left']), round(h['top'])]
    t.load(settings=EMULE)
    try:
        t.set_viewport(1366, 768)
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
        t.set_viewport(1366, 768)
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
    t.set_field('popupHeight', '500')
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
    """I-14: the row of Local has a Disable link, at the place of the Delete links of the servers and in
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
    """I-14: Local disabled, deleting the checked server checks the first one left; deleting the last
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
    t.keys('x')
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
        t.keys('x')
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
    t.eq(t.js("document.getElementById('GM_config_showServerList_var').nextElementSibling.id"), 'GM_config_popupCorner_var',
         'after Show the server list')
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
    """I-7 and SF-8.19: the setting Language, first in the General section: Browser language (default),
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
    """I-7: in French, the toolbars, their tooltips, the help, the message of the closed popup and the
    settings dialog; the letter of a shortcut underlined only when the label holds it."""
    t.load(settings=EMULE, language='fr-FR')
    shown = t.js(TEXTS_SHOWN)
    t.eq(shown, {'download': 'Télécharger', 'downloadTitle': 'Télécharger les liens cochés (Ctrl+Alt+D)',
                 'edit': '<u>M</u>ode édition', 'close': 'Fermer (Ctrl+Alt+C)'},
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
    """I-7: the setting Language wins over the language of the browser; Browser language gives French
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


def test_texts_complete(t):
    """I-7: every text has its French version, with the same values {name}; a label marks at most one
    letter of shortcut (&)."""
    t.load()
    check = r"""(function(){var en=TEXTS.en, fr=TEXTS.fr, keys=function(o){return Object.keys(o).sort();},
      names=function(s){return (s.match(/\{\w+\}/g)||[]).sort().join(',');};
      return {missing: keys(en).filter(function(k){return !(k in fr);}), extra: keys(fr).filter(function(k){return !(k in en);}),
              values: keys(en).filter(function(k){return k in fr && names(en[k]) != names(fr[k]);}),
              marks: keys(en).concat(keys(fr)).filter(function(k){return ((en[k]||'')+'').split('&').length > 2 || ((fr[k]||'')+'').split('&').length > 2;})};})()"""
    t.eq(t.js(check), {'missing': [], 'extra': [], 'values': [], 'marks': []}, 'the tables complete and consistent')
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


def test_shortcuts_without_links(t):
    """SF-1.12: on a page without ed2k links, no shortcut opens a popup or raises an error."""
    for key in 'ocmx':
        t.load('__nolinks', settings=EMULE)
        t.keys(key)
        t.eq(t.js(POPUP), [0, 0, 0], f'Ctrl+Alt+{key.upper()}: no popup')
        t.eq(t.errors, [], f'Ctrl+Alt+{key.upper()}: no JavaScript error')
        if key == 'm':
            t.eq(t.js('popupMode'), 1, 'Ctrl+Alt+M: mode unchanged')


def test_debug_traces(t):
    """SF-9: the debug traces are off on a new installation, and the menu entry
    "Toggle debug traces" switches them on and off, for the next pages too."""
    t.load(debug=None)
    t.eq([c for c in t.console if 'saveConfig()' in c], [], 'no trace on a new installation')
    t.menu('t')
    t.check(t.dialogs and 'debug traces on' in t.dialogs[-1], 'menu: traces switched on', t.dialogs)
    t.eq(t.gm('debug_mode'), 1, 'setting stored')
    t.console.clear()
    t.reload()
    t.check(t.traced('saveConfig() storing the settings'), 'traces shown on the next page')
    t.menu('t')
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
    t.keys('m')
    lines = t.js("document.getElementById('editbox').value.split('\\n')")
    t.eq([len(lines), any(COLLECTION in line for line in lines)], [9, True], 'edit mode: every link, the collection included')
    t.eq([b[2] for b in t.js(ALL_BOXES)], [True, True], 'both boxes disabled')
    t.keys('m')
    t.eq([r[0] for r in t.js(FILTER_ROWS) if not r[1]], [COLLECTION], 'normal mode again: the filter applied again')


def test_settings_check_filter(t):
    """SF-8 and SF-8.10: the field Links checked by default, last of the Popup section, as wide as
    its help, in a monospace font; a filter that can not be read, or with the flag g or y, is
    refused under the field and nothing is saved; a right one is saved, and applied."""
    error = "(document.querySelector('#GM_config_checkFilter_var .error') || {}).textContent"
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_popupWidth_var').nextElementSibling.id"), 'GM_config_checkFilter_var',
         'after the Max Popup Width')
    t.eq(t.js("document.getElementById('GM_config_checkFilter_field_label').textContent"), 'Links checked by default', 'label')
    t.eq(t.js("document.getElementById('GM_config_section_desc_2').textContent"),
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
