"""Take the screenshots of the README and of SPECIFICATIONS.md, in headless Chrome.

    python tests/take_screenshots.py [folder [readme] [spec] [sizes] [themes]]

The script is injected unchanged into the test pages, as by the tests (run_tests.py), with
fictitious settings: nothing personal can appear in the pictures. They are written to the
screenshots folder of the repository (screenshots/ and screenshots/spec/), or under the folder
given, to compare them with the current ones before replacing them. Look at every picture before
committing it.

The pictures of the specification carry numbered markers, drawn over the page; their legend is
written in SPECIFICATIONS.md, next to each picture. Moving a marker means updating its legend.
The results of Test and Import are shown with the functions of the script, without a server.
"""
import base64
import json
import os
import pathlib
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
import run_tests  # noqa: E402

OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, 'screenshots')
SPEC = os.path.join(OUT, 'spec')

# README: one server, named as a user would name it (a long name would be cut in the lists of the popup)
README_SETTINGS = {'ed2kDlMethod': 'amuleapi', 'emuleUrl': 'http://127.0.0.1:4711/', 'emulePwd': '',
                   'emuleCat': '*Video=2;Audio=1;Documents=3'}
README_SERVERS = {'active': 'srv1', 'list': [{'id': 'srv1', 'name': 'aMule NAS', 'method': 'amuleapi',
                                              'emuleUrl': 'http://127.0.0.1:4711/', 'emulePwd': '',
                                              'emuleCat': '*Video=2;Audio=1;Documents=3'}]}
README_WIDTH = 800      # the width of the window of both pictures of the README

# SPECIFICATIONS.md: two servers, the first one checked and displayed; the eMule collection of the
# test page left unchecked by the filter of the links checked by default (SF-5.7)
SPEC_SETTINGS = {'ed2kDlMethod': 'amuleapi', 'emuleUrl': 'http://192.168.1.10:4711/', 'emulePwd': 'secret',
                 'emuleCat': '*Video=2;Audio=1;Documents=3', 'checkFilter': r'/^(?!.*\.emulecollection$)/i'}
SPEC_SERVERS = {'active': 'srv1', 'list': [
    {'id': 'srv1', 'name': 'aMule NAS', 'method': 'amuleapi', 'emuleUrl': 'http://192.168.1.10:4711/',
     'emulePwd': 'secret', 'emuleCat': '*Video=2;Audio=1;Documents=3'},
    {'id': 'srv2', 'name': 'eMule desktop', 'method': 'emule', 'emuleUrl': 'http://127.0.0.1:4711/',
     'emulePwd': '', 'emuleCat': '*default=0;Video=2'}]}
AMULE_CATEGORIES = [{'index': 0, 'name': 'Default'}, {'index': 1, 'name': 'Audio'}, {'index': 2, 'name': 'Video'},
                    {'index': 3, 'name': 'Documents'}, {'index': 4, 'name': 'Software'}]

# Numbered markers drawn over the page: mark(element, number, side of the element). hidePage()
# hides the test page behind the popup or the dialog.
MARKERS = r"""
window.mark = function (el, n, where) {
  if (typeof el == 'string') el = document.querySelector(el);
  var r = el.getBoundingClientRect(), d = document.createElement('div'), x, y;
  if (where == 'left') { x = r.left - 24; y = r.top + r.height / 2 - 10; }
  if (where == 'right') { x = r.right + 4; y = r.top + r.height / 2 - 10; }
  if (where == 'top') { x = r.left + r.width / 2 - 10; y = r.top - 24; }
  d.textContent = n;
  d.className = 'specmark';
  d.setAttribute('style', 'position:fixed; z-index:2147483647; left:' + x + 'px; top:' + y + 'px; width:20px; height:20px;'
    + ' border-radius:50%; background:#d9480f; color:#fff; font:bold 11px/20px Arial,sans-serif; text-align:center;'
    + ' box-shadow:0 0 0 2px #fff, 0 1px 3px rgba(0,0,0,.4);');
  document.body.appendChild(d);
};
window.hidePage = function (keepPopup) {
  var s = document.createElement('style');
  s.textContent = 'body > *:not(#GM_config):not(#GM_config_backdrop):not(.specmark)'
    + (keepPopup ? ':not(#theDiv):not(:has(#theDiv))' : '') + ' { visibility: hidden !important; }';
  document.head.appendChild(s);
};
"""


def save(cdp, path, clip=None):
    params = {'format': 'png'}
    if clip:
        params['clip'] = dict(clip, scale=1)
    data = cdp.call('Page.captureScreenshot', params)['data']
    with open(path, 'wb') as f:
        f.write(base64.b64decode(data))
    print('written', os.path.relpath(path, ROOT) if path.startswith(ROOT) else path)


def box(t, selector, margin=0):
    """The area of an element, with a margin around it."""
    r = t.js(f"(function(){{var b=document.querySelector({json.dumps(selector)}).getBoundingClientRect();"
             "return [b.left,b.top,b.width,b.height];})()")
    return {'x': max(0, r[0] - margin), 'y': max(0, r[1] - margin), 'width': r[2] + 2 * margin, 'height': r[3] + 2 * margin}


def union(*areas):
    x = min(a['x'] for a in areas)
    y = min(a['y'] for a in areas)
    return {'x': x, 'y': y, 'width': max(a['x'] + a['width'] for a in areas) - x,
            'height': max(a['y'] + a['height'] for a in areas) - y}


def readme(t, cdp):
    """The pictures of the README, in a window README_WIDTH wide: the popup over the page, down to the first two rows of the
    table of the page, to see the links it lists; the settings dialog over the page, its sections as at its first opening."""
    cdp.call('Emulation.setDeviceMetricsOverride', {'width': README_WIDTH, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
    t.load(settings=README_SETTINGS, servers=README_SERVERS, debug=0, folded=None)
    cdp.pump(0.5)
    bottom = t.js("Math.ceil([].filter.call(document.querySelectorAll('table'), function (e) { return !e.closest('#theDiv'); })[0]"
                  ".rows[2].getBoundingClientRect().bottom + 12)")     # the table of the page, not the list of the popup
    save(cdp, os.path.join(OUT, 'screenshot_main.png'), {'x': 0, 'y': 0, 'width': README_WIDTH, 'height': bottom})
    t.open_settings()
    cdp.pump(0.5)
    bottom = t.js("Math.ceil(document.getElementById('GM_config').getBoundingClientRect().bottom + 10)")
    save(cdp, os.path.join(OUT, 'screenshot_settings.png'), {'x': 0, 'y': 0, 'width': README_WIDTH, 'height': bottom})


def open_dialog(t, folded=None, **changes):
    """The settings dialog with the two servers, the page behind hidden; its sections as at its first opening (General and
    Servers unfolded) unless folded gives the sections folded, () for none."""
    t.load(settings=dict(SPEC_SETTINGS, **changes), debug=0, folded=folded)
    t.js(f"localStorage.setItem('gm:servers', {json.dumps(json.dumps(json.dumps(SPEC_SERVERS)))})")
    t.reload()
    t.open_settings()
    t.js(MARKERS)
    t.js('hidePage(false)')
    t.pump(0.3)


def spec(t, cdp):
    # the popup in normal mode, with the two servers and the answer of aMule (legend: SF-2 in SPECIFICATIONS.md);
    # the band of the answer covers the first rows of the list: the markers of a row are on the next ones
    t.load(settings=SPEC_SETTINGS, servers=SPEC_SERVERS, debug=0)
    t.js("var p = document.getElementById('theDiv'); p.style.marginTop = '34px'; p.style.marginLeft = '34px';")
    t.js("STATUS_DELAY = 600000; showStatus('8 link(s) added to aMule', true)")
    t.js(MARKERS)
    t.js('hidePage(true)')
    t.js("""(function () {
      var rows = document.querySelectorAll('#theDiv table tr'), cells = rows[3].querySelectorAll('td');
      mark('#checkall', 1, 'left'); mark('#emlTop .emlCount', 2, 'top'); mark('#srv', 3, 'top');
      mark('#emlTop .emlAdd', 4, 'top'); mark('#emlTop [data-icon=settings]', 5, 'top'); mark('#emlMin', 6, 'top');
      mark('#emlClose', 7, 'top'); mark('#emlStatus', 8, 'left');
      mark(rows[2].querySelector('input'), 9, 'left'); mark(rows[3].querySelector('a'), 10, 'right');
      mark(cells[cells.length - 1], 11, 'left'); mark('#checkall2', 12, 'left');
      mark(document.querySelector('#theDiv tr.filtered a'), 13, 'right');
    })()""")
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'popup.png'), union(box(t, '#theDiv', 34), {'x': 0, 'y': 0, 'width': 1, 'height': 1}))

    # the popup in edit mode (SF-4)
    t.load(settings=SPEC_SETTINGS, servers=SPEC_SERVERS, popup_mode=2, debug=0)
    t.js(MARKERS)
    t.js('hidePage(true)')
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'popup_edit.png'), box(t, '#theDiv', 2))

    # the settings dialog as at its first opening, every part numbered (legend: SF-8)
    open_dialog(t)
    t.js("""(function () {
      var head = function (key) { return '[data-section=' + key + '] > .section_header'; };
      mark('#GM_config_helpBtn', 1, 'left'); mark('#GM_config_server_local', 2, 'left');
      mark('#GM_config_server_srv1', 3, 'left'); mark('#GM_config_server_srv1 .method', 4, 'left');
      mark('#GM_config_server_srv2 .acts', 5, 'right'); mark('#GM_config_server_fields', 6, 'left');
      mark('#GM_config_emulePwd_var .reveal', 7, 'left'); mark('#GM_config_testBtn', 8, 'right');
      mark('#GM_config_importBtn', 9, 'right'); mark('#GM_config_addServer', 10, 'right');
      mark(head('shortcuts'), 11, 'left'); mark(head('toolbars'), 12, 'left');
      mark(head('popup'), 13, 'left'); mark(head('editbox'), 14, 'left');
      mark('#GM_config_resetBtn', 15, 'left'); mark('#GM_config_saveBtn', 16, 'top');
      mark('#GM_config_issuesLink', 17, 'left'); mark('#GM_config_repoLink', 18, 'right');
    })()""")
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'settings.png'), box(t, '#GM_config', 30))

    # the helps shown under the fields (SF-8.3)
    open_dialog(t)
    t.click('#GM_config_helpBtn')
    save(cdp, os.path.join(SPEC, 'settings_help.png'), union(box(t, '#GM_config_header', 8), box(t, '#GM_config_servers', 8)))

    # values checked before saving (SF-8.10): a name already used, no valid category, a popup too low
    open_dialog(t)
    t.js("document.getElementById('GM_config_field_serverName').value = 'eMule desktop';"
         "document.getElementById('GM_config_field_emuleCat').value = 'Video';"
         "document.getElementById('GM_config_field_popupCols').value = '10';"
         "document.getElementById('GM_config_saveBtn').click()")
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'settings_errors.png'), box(t, '#GM_config', 4))

    # a server deleted: the notice in its place, with Undo (SF-8.14)
    open_dialog(t)
    t.click('#GM_config_server_srv2 .del')
    save(cdp, os.path.join(SPEC, 'settings_delete.png'), box(t, '#GM_config_servers', 8))

    # Reset to defaults: the two settings it changed highlighted, with Undo (SF-8.12)
    open_dialog(t, popupRows=20)
    t.click('#GM_config_resetBtn')
    save(cdp, os.path.join(SPEC, 'settings_reset.png'), box(t, '#GM_config', 4))

    # Test and Import (SF-8.16 to SF-8.18): connected; categories imported, with Undo
    open_dialog(t)
    t.js(f"""(function () {{
      var field = document.getElementById('GM_config_field_emuleCat'), before = field.value;
      var merged = mergeCategories({json.dumps(AMULE_CATEGORIES)}, before);
      showApiStatus('import', merged.message, 'ok', function () {{ field.value = before; }});
      field.value = merged.value;
      document.getElementById('GM_config_emuleCat_var').classList.add('changed');
      showApiStatus('test', 'Connected to aMule 3.1.0 (ed2k: connected, Kad: connected).', 'ok');
    }})()""")
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'settings_test_import.png'), box(t, '#GM_config_server_fields', 4))
    for kind, text, name in [('warn', 'Connected to aMule 3.1.0, but this password can not add downloads: '
                                      'the admin password of aMule is needed', 'settings_test_warn.png'),
                             ('ko', 'aMule refused the password', 'settings_test_ko.png')]:
        t.js(f"showApiStatus('test', {json.dumps(text)}, '{kind}')")
        cdp.pump(0.2)
        save(cdp, os.path.join(SPEC, name), union(box(t, '#GM_config_emulePwd_var', 2), box(t, '#GM_config_testStatus', 2)))


# The picture of each theme (SF-13), screenshots/theme/<theme>.png: every screen of the script in this theme,
# on a page of its kind (light or dark), with its main colors and the states of the buttons of the popup. The
# themes are read from the script: a new theme gets its picture. A translucent theme (blur) is shown on a
# colorful page, its text left visible, to show the transparency and the blur.
THEME_PAGE = {'light': '#f3f3f3', 'dark': '#1e1e1e'}
TRANSLUCENT_PAGE = ('radial-gradient(circle at 15% 20%, #ff9a8b 0, transparent 35%), radial-gradient(circle at 70% 30%, #6ec3f4 0, transparent 40%),'
                    ' radial-gradient(circle at 40% 85%, #b8f28c 0, transparent 40%), linear-gradient(135deg, #a18cd1, #fbc2eb)')
STATE_BUTTONS = [('Settings', '#emlTop [data-icon=settings]'), ('Help', '#emlHelpBtn'), ('Minimize', '#emlMin'),
                 ('Close', '#emlClose'), ('Menu', '#emlMenuBtn'), ('Download', '#emlTop .emlAdd'), ('Edit mode', '#emlEdit')]
SHOW_SCREENS = """(function () {
  var keep = ['theDiv', 'emlHelp', 'emlMsg', 'emlMsgBackdrop', 'GM_config', 'GM_config_backdrop', 'emlStatus', 'emlMenu'];
  [].forEach.call(document.body.children, function (c) {
    var mine = keep.some(function (id) { var e = document.getElementById(id); return e && (c === e || c.contains(e)); });
    c.style.visibility = mine ? '' : 'hidden';
  });
})()"""
NO_SELECTION = ("(function(){var a=document.activeElement; if (a && a.setSelectionRange) a.setSelectionRange(0, 0);"
                " if (a && a.blur) a.blur(); window.getSelection().removeAllRanges();})()")


def theme_shot(t, cdp, page, selectors, margin=12, show_page=False):
    """The elements on the page of the theme, at twice the size; the rest of the page hidden, unless show_page."""
    t.js(f"document.documentElement.style.background = document.body.style.background = '{page}';")
    if not show_page:
        t.js(SHOW_SCREENS)
    t.pump(0.2)
    r = t.js(f"""(function (sels) {{
      var x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9;
      sels.forEach(function (s) {{ document.querySelectorAll(s).forEach(function (e) {{
        if (!e.getClientRects().length) return;
        var b = e.getBoundingClientRect();
        x0 = Math.min(x0, b.left); y0 = Math.min(y0, b.top); x1 = Math.max(x1, b.right); y1 = Math.max(y1, b.bottom); }}); }});
      return [x0, y0, x1, y1];
    }})({json.dumps(selectors)})""")
    clip = {'x': max(0, r[0] - margin), 'y': max(0, r[1] - margin), 'width': r[2] - r[0] + 2 * margin,
            'height': r[3] - r[1] + 2 * margin, 'scale': 2}
    return cdp.call('Page.captureScreenshot', {'format': 'png', 'clip': clip})['data']


def state_shot(t, cdp, selector, state):
    """A button of the popup, three times larger: shown, under the mouse, or pressed (and released away from it,
    so that it is not clicked)."""
    clip = dict(box(t, selector, 4), scale=3)
    if state == 'hover':
        t.hover(selector)
    if state == 'pressed':
        t.hold(selector)
    data = cdp.call('Page.captureScreenshot', {'format': 'png', 'clip': clip})['data']
    t.release_away() if state == 'pressed' else t.move_away()
    return data


def menu_state_shot(t, cdp, selector, state):
    """The menu button as in a narrow popup (in place of the buttons at the top right, SF-2.13), in a state."""
    # its width kept: a narrower popup would have its toolbars adapted again, and the menu button hidden
    t.js("var d = document.getElementById('theDiv'); d.style.width = getComputedStyle(d).width; setToolbarsMenu(d, true)")
    data = state_shot(t, cdp, selector, state)
    t.js("document.getElementById('theDiv').style.width = ''; adaptToolbars()")
    return data


def states_table(t, cdp, settings, page, show_page):
    """The buttons of the popup in the theme: shown, under the mouse, pressed."""
    t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
    t.js(f"document.documentElement.style.background = document.body.style.background = '{page}';")
    if not show_page:
        t.js(SHOW_SCREENS)
    rows = ''
    for state, label in (('shown', 'Shown'), ('hover', 'Under the mouse'), ('pressed', 'Pressed')):
        cells = ''.join(f'<td><img src="data:image/png;base64,{(menu_state_shot if selector == "#emlMenuBtn" else state_shot)(t, cdp, selector, state)}"'
                        ' onload="this.width=this.naturalWidth/2.5"></td>' for _, selector in STATE_BUTTONS)
        rows += f'<tr><th>{label}</th>{cells}</tr>'
    head = ''.join(f'<th>{title}</th>' for title, _ in STATE_BUTTONS)
    return f'<table class="states"><tr><th></th>{head}</tr>{rows}</table>'


def theme_sheet(t, cdp, name):
    settings = dict(SPEC_SETTINGS, theme=name)
    t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
    colors = t.js(f'THEMES[{json.dumps(name)}]')
    title = t.js(f"tr('theme.{name}')")
    translucent = bool(colors.get('blur'))
    page = TRANSLUCENT_PAGE if translucent else THEME_PAGE[colors['scheme']]
    shot = lambda selectors, margin=12: theme_shot(t, cdp, page, selectors, margin, translucent)  # noqa: E731
    t.js('STATUS_DELAY = 600000;')
    pics = {'popup': shot(['#theDiv'])}
    t.edit_mode()
    t.js(NO_SELECTION)
    pics['edit'] = shot(['#theDiv'])
    t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
    t.click('#emlMin')
    t.move_away()   # no button left under the mouse
    pics['min'] = shot(['#theDiv'])
    t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
    t.js('STATUS_DELAY = 600000;')
    for key, call in (('ok', "'8 link(s) added to aMule', true"), ('doubt', "'2 link(s) left out by aMule (already in the list)', 'doubt'"),
                      ('ko', "'aMule refused the password', false")):
        t.js(f'showStatus({call})')
        pics[key] = shot(['#emlTop', '#emlStatus'])
    t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
    t.click('#emlHelpBtn')
    t.move_away()
    pics['help'] = shot(['#emlHelp'])
    t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
    t.click('#emlClose')
    t.move_away()
    pics['msg'] = shot(['#emlMsg'], 24)
    # the band of an answer, the popup closed: alone in the corner of the popup
    t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
    t.js("STATUS_DELAY = 600000; showStatus('8 link(s) added to aMule', true)")
    t.click('#emlClose')
    t.press('Escape')
    t.move_away()
    pics['toast'] = shot(['#emlStatus'])
    # a narrow popup, the lists and Edit mode of its bottom toolbar folded (SF-2.13), its menu open: the widest window where it is needed
    for width in range(420, 150, -10):
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': width, 'height': 900, 'deviceScaleFactor': 1, 'mobile': False})
        t.load(settings=settings, servers=SPEC_SERVERS, debug=0)
        if 'bottom.category' in (t.js("document.getElementById('theDiv').dataset.folded") or ''):
            break
    t.click('#emlMenuBtn')
    t.hover('#emlMenu [data-menu=help]')
    t.js(f"document.documentElement.style.background = document.body.style.background = '{page}';")
    if not translucent:
        t.js(SHOW_SCREENS)
    t.pump(0.2)
    bottom = t.js("Math.max(document.getElementById('theDiv').getBoundingClientRect().bottom,"
                  " document.getElementById('emlMenu').getBoundingClientRect().bottom)")
    pics['narrow'] = cdp.call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': 0, 'y': 0, 'width': width, 'height': bottom + 12,
                                                                                    'scale': 2}})['data']
    t.move_away()
    cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1600, 'height': 2600, 'deviceScaleFactor': 1, 'mobile': False})
    states = states_table(t, cdp, settings, page, translucent)
    open_dialog(t, folded=(), theme=name)     # every section unfolded: the theme on every control
    pics['settings'] = shot(['#GM_config'])
    dark = colors['scheme'] == 'dark'
    themed.append((title, page, pics['popup'], dark))    # for the overview of the themes
    img = lambda k: f'<img src="data:image/png;base64,{pics[k]}" onload="this.width=this.naturalWidth/2">'  # noqa: E731
    # the fonts: the one of the screens (the first of its list, then the others if it is missing), the monospace one
    first = lambda stack: stack.split(',')[0].strip().strip('"')  # noqa: E731
    mono = 'Consolas, "Courier New", monospace'
    fonts = ''.join(f"<div class='font'><span style='font-family: {stack}'>{label}: {first(stack)}, Aa Bb Cc 0123</span>"
                    f"<i>{stack.replace(chr(34), '')}</i></div>"
                    for label, stack in (('Screens', colors['font']), ('Edit box and filter', mono)))
    swatches = ''.join(f'<span class="sw"><i style="background:{colors[k]}"></i>{k} {colors[k]}</span>'
                       for k in ('bg', 'bar', 'ctlBg', 'line', 'frame', 'text', 'muted', 'accent', 'title', 'danger'))
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {{ margin: 0; padding: 24px; background: {page}; color: {'#dddddd' if dark else '#222222'}; font: 13px 'Segoe UI', Arial, sans-serif; }}
h1 {{ margin: 0 0 8px; font-size: 20px; }}
.sw {{ display: inline-flex; align-items: center; gap: 4px; margin: 0 12px 6px 0; font: 11px Consolas, monospace; }}
.sw i {{ width: 14px; height: 14px; border: 1px solid #888; display: inline-block; }}
.grid {{ display: flex; gap: 28px; align-items: flex-start; margin-top: 12px; }}
.col {{ display: flex; flex-direction: column; gap: 14px; }}
.cap {{ font-size: 11px; color: #888; margin: 0 0 2px; }} img {{ display: block; }}
.row {{ display: flex; gap: 28px; align-items: flex-start; }} .fonts {{ width: 270px; }}
.font {{ margin: 0 0 3px; }} .font span {{ font-size: 12px; display: block; }} .font i {{ display: block; font: 10px Consolas, monospace; color: #888; }}
table.states {{ border-collapse: collapse; }} table.states td {{ padding: 2px 8px 2px 0; }}
table.states th {{ font-size: 11px; font-weight: normal; color: #888; text-align: left; padding: 2px 8px 2px 0; white-space: nowrap; }}
</style></head><body><div id="wrap" style="display:inline-block">
<h1>{title}</h1><div>{swatches}</div>
<div class="grid">
  <div class="col">
    <div><div class="cap">Popup</div>{img('popup')}</div>
    <div><div class="cap">Minimized</div>{img('min')}</div>
    <div><div class="cap">Answers: success, warning, error</div>{img('ok')}{img('doubt')}{img('ko')}</div>
    <div><div class="cap">Edit mode</div>{img('edit')}</div>
    <div><div class="cap">Narrow popup, the menu open</div>{img('narrow')}</div>
  </div>
  <div class="col">
    <div><div class="cap">Help</div>{img('help')}</div>
    <div><div class="cap">Popup closed</div>{img('msg')}</div>
    <div><div class="cap">Buttons of the popup</div>{states}</div>
    <div class="row"><div><div class="cap">Answer, the popup closed</div>{img('toast')}</div>
      <div class="fonts"><div class="cap">Fonts</div>{fonts}</div></div>
  </div>
  <div class="col"><div><div class="cap">Settings</div>{img('settings')}</div></div>
</div></div></body></html>"""


themed = []     # the title, the page and the popup of each theme drawn, for the overview


def theme_overview():
    """The popups of every theme side by side (screenshots/theme/0_overview.png, first in the folder), each one on its page."""
    cells = ''.join(f'<div class="cell" style="background:{page}"><div class="cap" style="color:{"#dddddd" if dark else "#222222"}">'
                    f'{title}</div><img src="data:image/png;base64,{popup}" onload="this.width=this.naturalWidth/2"></div>'
                    for title, page, popup, dark in themed)
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {{ margin: 0; padding: 0; background: {THEME_PAGE['dark']}; font: 14px 'Segoe UI', Arial, sans-serif; }}
.grid {{ display: grid; grid-template-columns: repeat(3, max-content); gap: 0; }}
.cell {{ padding: 18px 22px; }} .cap {{ font-weight: bold; margin: 0 0 6px; }} img {{ display: block; }}
</style></head><body><div id="wrap" style="display:inline-block"><div class="grid">{cells}</div></div></body></html>"""


def render_sheet(cdp, folder, html, file):
    """A sheet made in HTML, as a picture: the page written, opened in the browser, captured whole."""
    cdp.call('Emulation.setDeviceMetricsOverride', {'width': 2400, 'height': 1600, 'deviceScaleFactor': 1, 'mobile': False})
    page = os.path.join(folder, '_sheet.html')
    with open(page, 'w', encoding='utf-8') as f:
        f.write(html)
    cdp.navigate(pathlib.Path(page).as_uri())
    cdp.pump(0.8)
    # the script, injected into every page, would open its settings there (a first run): only the sheet is kept
    cdp.js("[].slice.call(document.body.children).forEach(function (c) { if (c.id != 'wrap') { c.remove(); } })")
    size = cdp.js('(function(){var r=document.getElementById("wrap").getBoundingClientRect();'
                  ' return [Math.ceil(r.right + r.left), Math.ceil(r.bottom + r.top)];})()')     # the same margin all around
    data = cdp.call('Page.captureScreenshot', {'format': 'png', 'captureBeyondViewport': True,
                                               'clip': {'x': 0, 'y': 0, 'width': size[0], 'height': size[1], 'scale': 1}})['data']
    os.remove(page)
    path = os.path.join(folder, file)
    with open(path, 'wb') as f:
        f.write(base64.b64decode(data))
    print('written', path)


def sizes(t, cdp):
    """The popup in each size (SF-2.5), side by side: screenshots/spec/sizes.png."""
    cells = ''
    for name in (100, 120, 140):
        t.load(settings=dict(SPEC_SETTINGS, textSize=name), servers=SPEC_SERVERS, debug=0)
        title = f'{name} %'
        popup = theme_shot(t, cdp, THEME_PAGE['light'], ['#theDiv'])
        cells += (f'<div class="cell"><div class="cap">{title}</div>'
                  f'<img src="data:image/png;base64,{popup}" onload="this.width=this.naturalWidth/2"></div>')
    render_sheet(cdp, SPEC, f"""<!DOCTYPE html><html><head><meta charset="utf-8"><style>
body {{ margin: 0; padding: 0; background: {THEME_PAGE['light']}; font: 14px 'Segoe UI', Arial, sans-serif; color: #222222; }}
.grid {{ display: flex; align-items: flex-start; }} .cell {{ padding: 18px 22px; }} .cap {{ font-weight: bold; margin: 0 0 6px; }}
img {{ display: block; }}
</style></head><body><div id="wrap" style="display:inline-block"><div class="grid">{cells}</div></div></body></html>""", 'sizes.png')


def themes(t, cdp):
    folder = os.path.join(OUT, 'theme')
    os.makedirs(folder, exist_ok=True)
    t.load(settings=SPEC_SETTINGS, servers=SPEC_SERVERS, debug=0)
    names = t.js('Object.keys(THEMES)')
    for name in names:
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1600, 'height': 2600, 'deviceScaleFactor': 1, 'mobile': False})
        render_sheet(cdp, folder, theme_sheet(t, cdp, name), name + '.png')
    render_sheet(cdp, folder, theme_overview(), '0_overview.png')


def main():
    # the parts to take, all by default: readme, spec, themes (python tests/take_screenshots.py <folder> themes)
    parts = sys.argv[2:] or ['readme', 'spec', 'themes']
    os.makedirs(SPEC, exist_ok=True)
    server, base, chrome, cdp = run_tests.start_session()
    try:
        cdp.call('Emulation.setScrollbarsHidden', {'hidden': True})     # no scrollbar in the pictures
        t = run_tests.T(cdp, base, chrome)
        if 'readme' in parts:
            readme(t, cdp)
        if 'spec' in parts:
            # high enough for the settings dialog with every help shown, which the dialog would otherwise scroll
            cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1470, 'height': 1800, 'deviceScaleFactor': 1, 'mobile': False})
            spec(t, cdp)
        if 'spec' in parts or 'sizes' in parts:
            cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1600, 'height': 1600, 'deviceScaleFactor': 1, 'mobile': False})
            sizes(t, cdp)
        if 'themes' in parts:
            themes(t, cdp)
        if t.errors:
            sys.exit(f'JavaScript errors: {t.errors}')
    finally:
        print('temporary profile removed:', run_tests.stop_session(server, chrome, cdp))


if __name__ == '__main__':
    main()
