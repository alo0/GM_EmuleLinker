"""Take the screenshots of the README and of SPECIFICATIONS.md, in headless Chrome.

    python tests/take_screenshots.py [folder]

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
import sys

TESTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TESTS)
sys.path.insert(0, TESTS)
import run_tests  # noqa: E402

OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'screenshots')
SPEC = os.path.join(OUT, 'spec')

# README: one server, the default one of a new installation
README_SETTINGS = {'ed2kDlMethod': 'amuleapi', 'emuleUrl': 'http://127.0.0.1:4711/', 'emulePwd': '',
                   'emuleCat': '*Video=2;Audio=1;Documents=3'}

# SPECIFICATIONS.md: two servers, the first one checked and displayed
SPEC_SETTINGS = {'ed2kDlMethod': 'amuleapi', 'emuleUrl': 'http://192.168.1.10:4711/', 'emulePwd': 'secret',
                 'emuleCat': '*Video=2;Audio=1;Documents=3'}
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
    t.load(settings=README_SETTINGS, debug=0)
    cdp.pump(0.5)
    save(cdp, os.path.join(OUT, 'screenshot_main.png'))
    t.open_settings()
    cdp.pump(0.5)
    save(cdp, os.path.join(OUT, 'screenshot_settings.png'))


def open_dialog(t, **changes):
    """The settings dialog with the two servers, the page behind hidden."""
    t.load(settings=dict(SPEC_SETTINGS, **changes), debug=0)
    t.js(f"localStorage.setItem('gm:servers', {json.dumps(json.dumps(json.dumps(SPEC_SERVERS)))})")
    t.reload()
    t.open_settings()
    t.js(MARKERS)
    t.js('hidePage(false)')
    t.pump(0.3)


def spec(t, cdp):
    # the popup in normal mode, with the answer of aMule (legend: SF-2 in SPECIFICATIONS.md)
    t.load(settings=SPEC_SETTINGS, debug=0)
    t.js("var p = document.getElementById('theDiv'); p.style.marginTop = '34px'; p.style.marginLeft = '34px';")
    t.js("showStatus('9 link(s) added to aMule', true)")
    t.js(MARKERS)
    t.js('hidePage(true)')
    t.js("""(function () {
      var bars = document.querySelectorAll('#theDiv .toolbar'), top = bars[0], bottom = bars[bars.length - 1];
      var b = top.querySelectorAll('button'), rows = document.querySelectorAll('#theDiv table tr');
      var cells = rows[1].querySelectorAll('td');
      mark('#checkall', 1, 'top'); mark(b[0], 2, 'top'); mark(b[1], 3, 'top'); mark('#cat', 4, 'top');
      mark(b[2], 5, 'top'); mark(b[3], 6, 'top'); mark('#emlStatus', 7, 'left');
      mark(rows[0].querySelector('input'), 8, 'left'); mark(rows[1].querySelector('a'), 9, 'right');
      mark(cells[cells.length - 1], 10, 'left'); mark(bottom.querySelector('input'), 11, 'left');
    })()""")
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'popup.png'), union(box(t, '#theDiv', 34), {'x': 0, 'y': 0, 'width': 1, 'height': 1}))

    # the popup in edit mode (SF-4)
    t.load(settings=SPEC_SETTINGS, popup_mode=2, debug=0)
    t.js(MARKERS)
    t.js('hidePage(true)')
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'popup_edit.png'), box(t, '#theDiv', 2))

    # the settings dialog, every part numbered (legend: SF-8)
    open_dialog(t)
    t.js("""(function () {
      mark('#GM_config_helpBtn', 1, 'left'); mark('#GM_config_server_local', 2, 'left');
      mark('#GM_config_server_srv1', 3, 'left'); mark('#GM_config_server_srv1 .method', 4, 'left');
      mark('#GM_config_server_srv2 .acts', 5, 'right'); mark('#GM_config_server_fields', 6, 'left');
      mark('#GM_config_emulePwd_var .reveal', 7, 'left'); mark('#GM_config_testBtn', 8, 'right');
      mark('#GM_config_importBtn', 9, 'right'); mark('#GM_config_addServer', 10, 'right');
      mark('#GM_config_popupPos_var', 11, 'left'); mark('#GM_config_editCol_var', 12, 'left');
      mark('#GM_config_resetBtn', 13, 'left'); mark('#GM_config_saveBtn', 14, 'top');
      mark('#GM_config_issuesLink', 15, 'left'); mark('#GM_config_repoLink', 16, 'right');
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
         "document.getElementById('GM_config_field_popupHeight').value = '20';"
         "document.getElementById('GM_config_saveBtn').click()")
    cdp.pump(0.3)
    save(cdp, os.path.join(SPEC, 'settings_errors.png'), box(t, '#GM_config', 4))

    # a server deleted: the notice in its place, with Undo (SF-8.14)
    open_dialog(t)
    t.click('#GM_config_server_srv2 .del')
    save(cdp, os.path.join(SPEC, 'settings_delete.png'), box(t, '#GM_config_servers', 8))

    # Reset to defaults: the two settings it changed highlighted, with Undo (SF-8.12)
    open_dialog(t, popupHeight=600)
    t.click('#GM_config_resetBtn')
    save(cdp, os.path.join(SPEC, 'settings_reset.png'), box(t, '#GM_config', 4))

    # Test and Import (SF-8.16 to SF-8.18): connected; categories imported, with Undo
    open_dialog(t)
    t.js(f"""(function () {{
      var field = document.getElementById('GM_config_field_emuleCat'), before = field.value;
      var merged = mergeAmuleCategories({json.dumps(AMULE_CATEGORIES)}, before);
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


def main():
    os.makedirs(SPEC, exist_ok=True)
    server, base, chrome, cdp = run_tests.start_session()
    try:
        cdp.call('Emulation.setScrollbarsHidden', {'hidden': True})     # no scrollbar in the pictures
        t = run_tests.T(cdp, base, chrome)
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1470, 'height': 1255, 'deviceScaleFactor': 1, 'mobile': False})
        readme(t, cdp)
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1470, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
        spec(t, cdp)
        if t.errors:
            sys.exit(f'JavaScript errors: {t.errors}')
    finally:
        print('temporary profile removed:', run_tests.stop_session(server, chrome, cdp))


if __name__ == '__main__':
    main()
