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
    """SF-1: the 9 valid links of test_sample.html, the 2 invalid ones ignored. The page starts
    with the malformed link: the detection goes on after it (SF-1.7)."""
    t.load(settings=EMULE)
    t.eq(t.js("document.querySelector('a[href^=\"ed2k\"]').getAttribute('href')"), 'ed2k://xxxxxxxx',
         'the first ed2k link of the page is the malformed one')
    t.eq(t.js('eFiles[0]'), 'example1.mp3', 'the first file of the popup: the valid link that follows it')
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


def script_version():
    with open(os.path.join(ROOT, 'GM_EmuleLinker.user.js'), encoding='utf-8') as f:
        return re.search(r'^// @version\s+(\S+)', f.read(), re.M).group(1)


def field(name):
    return f"document.getElementById('GM_config_field_{name}')"


def test_settings_dialog_look(t):
    """SF-8.1, SF-8.3, SF-8.8 and SF-8.11: title with the version, the help of a field shown
    under it when it has the focus, masked password, backdrop, Escape to close."""
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js("document.getElementById('GM_config_header').firstChild.textContent"),
         f'Emule Linker {script_version()} — Settings', 'title with the version')
    tooltips = "document.querySelectorAll('#GM_config .config_var[title]').length"
    t.eq(t.js("document.querySelectorAll('#GM_config .config_var .help').length"), 11, 'a help for each field')
    t.eq(t.js(tooltips), 11, 'helps hidden: each one is the tooltip of its row')
    shown = ("[].filter.call(document.querySelectorAll('#GM_config .help'), function (h) {"
             "return getComputedStyle(h).display != 'none'; }).length")
    help_btn = "document.getElementById('GM_config_helpBtn').textContent"
    t.eq([t.js(shown), t.js(help_btn)], [0, '? Show help'], 'helps hidden at first')
    t.js(f"{field('emuleCat')}.focus()")
    t.eq(t.js(shown), 0, 'nothing shown on focus: the fields do not move')
    t.click('#GM_config_helpBtn')
    t.eq([t.js(shown), t.js(help_btn)], [11, 'Hide help'], 'Help button: every help shown')
    t.eq(t.js(tooltips), 0, 'helps shown: no tooltip repeating them')
    edges = ("(function(n){var f=document.getElementById('GM_config_field_'+n).getBoundingClientRect(),"
             "h=document.querySelector('#GM_config_'+n+'_var .help').getBoundingClientRect();"
             "return [Math.round(f.left)==Math.round(h.left), Math.round(f.right)==Math.round(h.right)];})")
    t.eq([t.js(f"{edges}('emuleUrl')"), t.js(f"{edges}('emuleCat')")], [[True, True], [True, True]],
         'Server URL and Category as wide as their help')
    t.eq(t.js("(function(){var p=document.getElementById('GM_config_field_emulePwd').getBoundingClientRect(),"
              "b=document.querySelector('#GM_config .reveal').getBoundingClientRect(),"
              "h=document.querySelector('#GM_config_emulePwd_var .help').getBoundingClientRect();"
              "return [Math.round(p.left)==Math.round(h.left), Math.round(b.right)==Math.round(h.right)];})()"),
         [True, True], 'Password and its Show button as wide as their help')
    t.close_settings()
    t.check(t.open_settings(), 'settings dialog opened again')
    t.eq(t.js(shown), 11, 'the choice is kept at the next opening')
    t.click('#GM_config_helpBtn')
    t.eq([t.js(shown), t.js(help_btn), t.gm('settings_help'), t.js(tooltips)], [0, '? Show help', 0, 11],
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
SHOWN_FIELDS = ("['serverName','serverMethod','emuleUrl','emulePwd','emuleCat'].filter(function (id) {"
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
                'mldonkey': ['serverName', 'serverMethod', 'emuleUrl'],
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
    right of the notice; in the list of the servers, on the right edge of the fields and of Show."""
    undo = ("(function(){var u=document.getElementById('GM_config_undoBtn'), s=document.querySelector('#GM_config .reveal');"
            "var n=u.parentNode, cu=getComputedStyle(u), cs=getComputedStyle(s), cn=getComputedStyle(n);"
            "return {style: [cu.fontSize, cu.padding, cs.fontSize, cs.padding],"
            "end: Math.round(n.getBoundingClientRect().right - parseFloat(cn.paddingRight) - u.getBoundingClientRect().right),"
            "show: Math.round(s.getBoundingClientRect().right - u.getBoundingClientRect().right)};})()")
    t.load(settings=EMULE)
    t.check(t.open_settings(), 'settings dialog opened')
    for name in ('aMule NAS', 'aMule seedbox'):
        t.click('#GM_config_addServer')
        set_server(t, name=name)
    click_server(t, 'aMule NAS', 'edit')
    click_server(t, 'aMule seedbox', 'delete')
    r = t.js(undo)
    t.eq(r['style'], ['11px', '2px 8px'] * 2, 'Undo of a deleted server: the style of Show')
    t.eq([r['end'], r['show']], [0, 0], 'on the right of its notice, under Show')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    r = t.js(undo)
    t.eq(r['style'], ['11px', '2px 8px'] * 2, 'Undo of Reset: the style of Show')
    t.eq(r['end'], 0, 'on the right of its notice')


def test_settings_reset_and_undo(t):
    """SF-8.12: Reset sets every setting back to its default value in the dialog only: Local is
    checked and every server removed. It highlights what it changed, and can be undone; Save then
    stores it."""
    custom = {'ed2kDlMethod': 'amuleapi', 'emuleUrl': 'http://192.168.1.10:4711/', 'emulePwd': 'secret',
              'emuleCat': '*Video=2;Audio=1', 'popupHeight': 600}
    marked = "[].map.call(document.querySelectorAll('#GM_config .config_var.changed'), function (r) { return r.id; })"
    notice = "(document.getElementById('GM_config_notice') || {}).textContent"
    t.load(settings=custom)
    t.check(t.open_settings(), 'settings dialog opened')
    t.check(t.js("!!document.getElementById('GM_config_resetBtn')"), 'Reset button')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.eq([[r[2], r[1]] for r in t.js(SERVER_ROWS)], [['Local', True]], 'Local checked, no server')
    t.eq([t.js(EDITED), t.js(f"{field('popupHeight')}.value")], [None, '800'], 'no field displayed, default sizes')
    t.eq(sorted(t.js(marked)), ['GM_config_ed2kDlMethod_var', 'GM_config_popupHeight_var'], 'servers and height highlighted')
    t.check((t.js(notice) or '').startswith('2 settings set back to their default value'), 'notice', t.js(notice))
    t.eq(t.stored_settings(), custom, 'nothing saved')
    t.js("document.getElementById('GM_config_undoBtn').click()")
    t.eq([[r[2], r[1]] for r in t.js(SERVER_ROWS)], [['Local', False], ['aMule 3.x (amuleapi)', True]], 'Undo: the server back')
    t.eq([t.js(f"{field(n)}.value") for n in ('emuleUrl', 'emulePwd', 'emuleCat', 'popupHeight')],
         ['http://192.168.1.10:4711/', 'secret', '*Video=2;Audio=1', '600'], 'Undo: its settings back')
    t.eq([t.js(marked), t.js(notice)], [[], None], 'Undo: no highlight, no notice')
    t.js("document.getElementById('GM_config_resetBtn').click()")
    t.save_settings()
    t.eq([t.stored_settings().get(k) for k in ('ed2kDlMethod', 'emulePwd', 'popupHeight')], ['local', '', 800],
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
    t.keys('a')
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
    """SF-9: the debug traces are off on a new installation, and the menu entry
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
              "var h = bar.children; return Math.abs(h[0].getBoundingClientRect().top - h[1].getBoundingClientRect().top) < 2; })"),
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