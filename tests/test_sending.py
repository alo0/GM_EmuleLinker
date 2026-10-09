"""Level 2: sending, received by fake ed2k clients (eMule, aMule, MLDonkey, custom server).

The script really sends its requests, through the browser, to the local test server,
which stands for the web interface of the ed2k client (see Handler in run_tests.py).
Each test checks what an ed2k client would read in them. Nothing reaches a real one.
The references in the comments (SF-x, L-x, §) point to SPECIFICATIONS.md.
"""
import json
import time
from urllib.parse import unquote

# The 9 valid links of test_sample.html, as an ed2k client must read them: name, size, hash
EXPECTED = {
    ('example1.mp3', '1048576', 'ABCDEF1234567890ABCDEF1234567890'),
    ('example2.avi', '734003200', '123456ABCDEF7890123456ABCDEF7890'),
    ('Documentary Planet Earth 4K.mp4', '4294967296', '1A2B3C4D5E6F7A8B9C0D1E2F3A4B5C6D'),
    ('Été à Paris (Café).mp3', '8543210', '3F8E1D2C4B5A69786950413EAB7CD821'),
    ('Conférence Téléphonique (v2.0).mkv', '1879048192', '9C8B7A6D5E4F32107856943A12BCDE01'),
    ('François & Marie [Résumé].docx', '56789012', 'AB12CD34EF56789012ABCDEF34567890'),
    ('Ópera Española (Colección).flac', '287654321', '5E6F7A8B9C0D1E2F3A4B5C6D7E8F9012'),
    ('Bücher über Geräte (édition).pdf', '15728640', 'F0E1D2C3B4A5968778695047312ABCDE'),
    ('Guide Réseau été 2024.pdf', '20971520', 'C1D2E3F4A5B60718293A4B5C6D7E8F91'),
}



def links_of(text):
    """The ed2k links of a request, as an ed2k client reads them: one per line, the
    request parameter already decoded once, the file name decoded a second time (SF-7.2)."""
    links = set()
    for link in (text or '').split('\n'):
        if link:
            fields = link.split('|')
            links.add((unquote(fields[2]), fields[3], fields[4]))
    return links


def param(request, name, where='query'):
    values = request[where].get(name)
    return values[0] if values else None


def client(t, method, **changes):
    """Settings sending to the fake ed2k client."""
    settings = {'ed2kDlMethod': method, 'emuleUrl': t.fake_client_url,
                'emulePwd': 'secret', 'emuleCat': '*default=0;'}
    settings.update(changes)
    return settings


def mark_link(t, name):
    """Give an id to the popup link of a file, to click it or find its row."""
    t.js("[].filter.call(document.querySelectorAll('#divBody a.ed2k'), function (a) "
         f"{{ return a.textContent == {name!r}; }})[0].id = '__target'")


def click_add_all(t):
    """A real click on the top "Add all links" button. A click() from JavaScript would
    not be a user gesture, and Chrome would then block the window that sends the links."""
    t.js("[].filter.call(document.querySelectorAll('#theDiv button'),"
         "function (b) { return b.textContent == 'Add all links'; })[0].id = '__add'")
    t.click('#__add')


def change_category(t, value):
    """Choose a category in the drop-down list of the popup, as the user does."""
    t.js("var s = document.getElementById('cat'); s.value = %r; s.dispatchEvent(new Event('change'))" % value)
    t.pump(0.2)


# the category carried by each file name link of the popup
LINK_CATS = ("[].map.call(document.querySelectorAll('#divBody a.ed2k'), function (a) {"
             "var m = a.getAttribute('href').match(/[?&]cat=([^&]*)/); return m ? m[1] : null; })")


# ---- eMule -----------------------------------------------------------------------
def test_emule_add_all(t):
    """SF-7 (emule): one GET with the password, the category and the 9 links."""
    t.load(settings=client(t, 'emule'))
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        r = received[0]
        t.eq((r['method'], r['path']), ('GET', '/__emule/'), 'eMule web interface')
        t.eq(param(r, 'w'), 'password', 'w=password')
        t.eq(param(r, 'p'), 'secret', 'password')
        t.eq(param(r, 'cat'), '0', 'default category')
        t.eq(links_of(param(r, 'c')), EXPECTED, 'the 9 links, names correctly encoded')


def test_emule_empty_password(t):
    """SF-8 (emulePwd): without a password, the links are sent all the same, with an empty p="""
    t.load(settings=client(t, 'emule', emulePwd=''))
    t.eq(t.dialogs, [], 'no alert')
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(param(received[0], 'p'), '', 'empty password sent')
        t.eq(links_of(param(received[0], 'c')), EXPECTED, 'the 9 links')


def test_emule_popup_closed(t):
    """SF-5.5: with the popup closed, Ctrl+Alt+A sends every link of the page."""
    t.load(settings=client(t, 'emule'))
    t.keys('c')
    t.eq(t.js("!!document.getElementById('theDiv')"), False, 'popup closed by Ctrl+Alt+C')
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(links_of(param(received[0], 'c')), EXPECTED, 'the 9 links')


def test_emule_partial_selection(t):
    """SF-5.3: only the checked links are sent."""
    t.load(settings=client(t, 'emule'))
    for name in ('example1.mp3', 'example2.avi'):
        mark_link(t, name)
        t.js("document.getElementById('__target').closest('tr').querySelector('input').checked = false;"
             "document.getElementById('__target').id = ''")
    click_add_all(t)
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        expected = {e for e in EXPECTED if e[0] not in ('example1.mp3', 'example2.avi')}
        t.eq(links_of(param(received[0], 'c')), expected, 'the 7 checked links only')


def test_emule_category_change(t):
    """SF-6.6: the category chosen in the drop-down list is the one sent."""
    t.load(settings=client(t, 'emule', emuleCat='*Audio=1;Video=2'))
    change_category(t, '2')
    t.eq(t.js("document.getElementById('cat').value"), '2', 'drop-down list on Video')
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(param(received[0], 'cat'), '2', 'category sent: Video')


def test_category_change_keeps_popup(t):
    """SF-6.8: a category change keeps the popup as it is (checkboxes, size), only
    the URL of its links is updated, and the checked links are sent with the new category."""
    t.load(settings=client(t, 'emule', emuleCat='*Audio=1;Video=2'))
    t.js("var d = document.getElementById('theDiv'); d.__marker = 1; d.style.width = '500px';"
         "document.getElementById('l0').checked = false; document.getElementById('l1').checked = false")
    unchecked = set(t.js('[eFiles[0], eFiles[1]]'))
    change_category(t, '2')
    t.check(t.js("!!document.getElementById('theDiv').__marker"), 'same popup, not rebuilt')
    t.eq(t.js("document.getElementById('theDiv').style.width"), '500px', 'size kept')
    t.eq(t.js("document.querySelectorAll('#divBody input:checked').length"), 7, 'checkboxes kept')
    t.eq(set(t.js(LINK_CATS)), {'2'}, 'links of the list carry the new category')
    click_add_all(t)
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(param(received[0], 'cat'), '2', 'category sent: Video')
        t.eq(links_of(param(received[0], 'c')), {e for e in EXPECTED if e[0] not in unchecked},
             'the 7 links still checked')


def test_category_change_keeps_edit_box(t):
    """SF-6.8: in edit mode, a category change keeps the text typed by the user."""
    t.load(settings=client(t, 'emule', emuleCat='*Audio=1;Video=2'), popup_mode=2)
    t.js("document.getElementById('editbox').value = eLinks.filter(function (l) {"
         "return l.indexOf('Paris') >= 0; }).join('\\n')")
    typed = t.js("document.getElementById('editbox').value")
    change_category(t, '2')
    t.eq(t.js("document.getElementById('editbox').value"), typed, 'edit box text kept')
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(param(received[0], 'cat'), '2', 'category sent: Video')
        t.eq(links_of(param(received[0], 'c')), {e for e in EXPECTED if 'Paris' in e[0]},
             'the edited text is what is sent')


def test_category_choice_not_stored(t):
    """SF-6.9: the category chosen in the drop-down list is valid for the current page
    only: it is not stored, and the next page sends with the default category again."""
    t.load(settings=client(t, 'emule', emuleCat='*Audio=1;Video=2'))
    change_category(t, '2')
    t.eq(t.stored_settings().get('emuleCat'), '*Audio=1;Video=2', 'settings unchanged')
    t.reload()
    t.eq(t.js("document.getElementById('cat').value"), '1', 'new page: drop-down list on Audio')
    t.keys('c')
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(param(received[0], 'cat'), '1', 'popup closed: default category sent')


def test_emule_edit_mode_text_sent(t):
    """SF-4.3: in edit mode, the text of the edit box is what is sent."""
    t.load(settings=client(t, 'emule'))
    t.keys('m')
    t.js("document.getElementById('editbox').value = eLinks.filter(function (l) {"
         "return l.indexOf('Paris') >= 0 || l.indexOf('Conf') >= 0; }).join('\\n')")
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        expected = {e for e in EXPECTED if 'Paris' in e[0] or 'Conf' in e[0]}
        t.eq(links_of(param(received[0], 'c')), expected, 'the 2 links left in the edit box')


def test_emule_single_link_click(t):
    """SF-3.3: clicking a file name in the popup sends that file only."""
    t.load(settings=client(t, 'emule'))
    mark_link(t, 'Été à Paris (Café).mp3')
    t.click('#__target')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        expected = {e for e in EXPECTED if e[0] == 'Été à Paris (Café).mp3'}
        t.eq(links_of(param(received[0], 'c')), expected, 'that link only')


# ---- aMule -----------------------------------------------------------------------
def test_amule_without_password(t):
    """SF-7 (amule) and SF-6.3: one GET on footer.php, category 0 sent as "all"."""
    t.load(settings=client(t, 'amule', emulePwd=''))
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        r = received[0]
        t.eq(r['path'], '/__emule/footer.php', 'aMule web interface')
        t.eq(param(r, 'pass'), None, 'no password sent')
        t.eq(param(r, 'selectcat'), 'all', 'category 0 sent as "all"')
        t.eq(param(r, 'Submit'), 'Download link', 'Submit=Download+link')
        t.eq(links_of(param(r, 'ed2klink')), EXPECTED, 'the 9 links')


def test_amule_with_password(t):
    """SF-7.4: with a password, a login request first, then the links about 1 s later."""
    t.load(settings=client(t, 'amule'))
    t.keys('a')
    received = sorted(t.received(2, timeout=6), key=lambda r: r['time'])
    t.eq(len(received), 2, 'two requests')
    if len(received) == 2:
        login, links = received
        t.eq((login['path'], param(login, 'pass'), param(login, 'ed2klink')),
             ('/__emule/footer.php', 'secret', None), 'login request first, without links')
        t.check(links['time'] - login['time'] >= 0.9, 'links sent about 1 s later',
                f"{links['time'] - login['time']:.2f} s")
        t.eq(param(links, 'pass'), 'secret', 'password sent again with the links')
        t.eq(param(links, 'selectcat'), 'all', 'category')
        t.eq(links_of(param(links, 'ed2klink')), EXPECTED, 'the 9 links')


# ---- aMule 3.1 (amuleapi) --------------------------------------------------------------
def amuleapi_settings(t, **changes):
    settings = client(t, 'amuleapi', emuleUrl=t.fake_amuleapi_url)
    settings.update(changes)
    return settings


def by_path(received, path):
    return [r for r in received if r['path'] == '/__amuleapi/api/v1/' + path]


def status_line(t):
    return t.js("(document.getElementById('emlStatus') || {}).textContent")


def test_amuleapi_add_all(t):
    """SF-7.9 (amuleapi): a login, one JSON POST with the 9 links and the category, then a
    logout. The password travels in the login body only, never in a url."""
    t.load(settings=amuleapi_settings(t, emuleCat='*default=0;Video=2'))
    t.keys('a')
    received = sorted(t.received(3), key=lambda r: r['time'])
    t.eq([(r['method'], r['path'][len('/__amuleapi'):]) for r in received],
         [('POST', '/api/v1/auth/login'), ('POST', '/api/v1/downloads'), ('POST', '/api/v1/auth/logout')],
         'login, sending, logout')
    login, sending = by_path(received, 'auth/login'), by_path(received, 'downloads')
    if login:
        t.eq(login[0]['json'], {'password': 'secret'}, 'password in the login body')
        t.eq(login[0]['query'], {'include_token': ['true']}, 'token asked in the answer, nothing else in the url')
    if sending:
        t.eq(sending[0]['auth'], 'Bearer fake-token', 'the token of the login')
        t.eq(sending[0]['json']['category_index'], 0, 'default category, as a number')
        t.eq(links_of('\n'.join(sending[0]['json']['links'])), EXPECTED, 'the 9 links, names encoded once')
    t.check(all('secret' not in r['path'] + str(r['query']) for r in received), 'password in no url')
    t.eq(status_line(t), '9 link(s) added to aMule', 'SF-7.10: the answer of aMule shown in the popup')
    t.eq(t.dialogs, [], 'no alert')
    pages = t.open_pages()
    t.eq(len(pages), 1, 'no window opened')


def test_amuleapi_please_wait(t):
    """SF-7.10: while aMule has not answered, the popup shows an animated "Please wait",
    which the answer then replaces, the animation stopped."""
    t.load(settings=amuleapi_settings(t))
    t.amuleapi(delay=2)
    click_add_all(t)
    seen = set()
    end = time.time() + 1.5
    while time.time() < end:
        seen.add(status_line(t))
        t.pump(0.1)
    t.check(all((s or '').startswith('Please wait') for s in seen), 'Please wait shown while waiting', seen)
    t.check(len(seen) >= 3, 'the dots move', seen)
    t.received(3)
    t.eq(status_line(t), '9 link(s) added to aMule', 'replaced by the answer of aMule')
    t.pump(1)
    t.eq(status_line(t), '9 link(s) added to aMule', 'the animation is stopped')
    t.eq(t.js("getComputedStyle(document.getElementById('emlStatus')).color"), 'rgb(0, 102, 0)', 'success color')


ADD_BUTTONS = "[].map.call(document.querySelectorAll('#theDiv button.emlAdd'), function (b) { return b.disabled; })"


def test_amuleapi_no_double_sending(t):
    """SF-7.10: while aMule has not answered, the "Add all links" buttons are disabled, and
    neither the shortcut nor a click on a file name sends the links a second time."""
    t.load(settings=amuleapi_settings(t))
    t.eq(t.js(ADD_BUTTONS), [False, False], 'both buttons enabled before')
    t.amuleapi(delay=2)
    click_add_all(t)
    t.pump(0.3)
    t.eq(t.js(ADD_BUTTONS), [True, True], 'both buttons disabled while waiting')
    t.keys('a')
    mark_link(t, 'example1.mp3')
    t.click('#__target')
    received = t.received(3, timeout=6)
    t.eq(len(by_path(received, 'downloads')), 1, 'one sending only')
    t.eq(len(by_path(received, 'auth/login')), 1, 'one login only')
    t.eq(status_line(t), '9 link(s) added to aMule', 'the answer of the first sending')
    t.eq(t.js(ADD_BUTTONS), [False, False], 'both buttons enabled again')


def test_amuleapi_slow_answer(t):
    """SF-7.10: aMule answers only once every link is added, which takes long with many links.
    The time limit grows with the number of links; once it is over, the message says that aMule
    did not answer in time, not that it can not be reached: the links may well be added."""
    # time measured on aMule 3.1.0: 8.1 s for 500 links, 77.3 s for 2,000 links; twice that at least
    for count, measured in ((500, 8.1), (2000, 77.3)):
        limit = t.call('amuleApiTimeout', count)
        t.check(limit >= 2 * measured * 1000, f'time limit for {count} links: at least twice {measured} s', limit)
    t.load(settings=amuleapi_settings(t))
    t.js('amuleApiTimeout = function () { return 1000; }')      # 1 s, for the test
    t.amuleapi(delay=3)
    click_add_all(t)
    end = time.time() + 6
    while time.time() < end and (status_line(t) or 'Please wait').startswith('Please wait'):
        t.pump(0.2)
    t.eq(status_line(t), 'aMule has not answered within 1 s: the links may still be added, check aMule',
         'late answer: the links may be added')
    t.eq(t.js(ADD_BUTTONS), [False, False], 'buttons enabled again')
    t.eq(len(by_path(t.received(timeout=3), 'downloads')), 1, 'the links were sent once')


def test_amuleapi_category_change(t):
    """SF-6.6 (amuleapi): the category chosen in the drop-down list is sent as its index."""
    t.load(settings=amuleapi_settings(t, emuleCat='*Audio=1;Video=2'))
    change_category(t, '2')
    t.keys('a')
    sending = by_path(t.received(3), 'downloads')
    t.eq(len(sending), 1, 'one sending')
    if sending:
        t.eq(sending[0]['json']['category_index'], 2, 'category sent: Video')


def test_amuleapi_single_link_click(t):
    """SF-3.3 (amuleapi): clicking a file name sends that file only, without leaving the page."""
    t.load(settings=amuleapi_settings(t))
    mark_link(t, 'Été à Paris (Café).mp3')
    t.eq(t.js("document.getElementById('__target').getAttribute('href').slice(0, 17)"), 'ed2k://%7Cfile%7C',
         'the link holds its encoded ed2k link')
    t.click('#__target')
    sending = by_path(t.received(3), 'downloads')
    t.eq(len(sending), 1, 'one sending')
    if sending:
        t.eq(links_of('\n'.join(sending[0]['json']['links'])),
             {e for e in EXPECTED if e[0] == 'Été à Paris (Café).mp3'}, 'that link only')
    t.eq(status_line(t), '1 link(s) added to aMule', 'answer shown')
    pages = t.open_pages()
    t.eq(pages, [t.base + '/test_sample.html'], 'still on the page, nothing else opened')


def test_amuleapi_edit_mode(t):
    """SF-7.11: in edit mode, the lines that are not ed2k links are left out of the sending."""
    t.load(settings=amuleapi_settings(t), popup_mode=2)
    t.js("document.getElementById('editbox').value = '\\n' + eLinks.filter(function (l) {"
         "return l.indexOf('Paris') >= 0 || l.indexOf('Conf') >= 0; }).join('\\n\\n') + '\\nsome text\\n'")
    t.keys('a')
    sending = by_path(t.received(3), 'downloads')
    t.eq(len(sending), 1, 'one sending')
    if sending:
        t.eq(links_of('\n'.join(sending[0]['json']['links'])),
             {e for e in EXPECTED if 'Paris' in e[0] or 'Conf' in e[0]}, 'the 2 links only')
    t.eq(status_line(t), '2 link(s) added to aMule', 'answer shown')


def test_amuleapi_wrong_password(t):
    """SF-7.10: a refused password is shown, and nothing is sent."""
    t.load(settings=amuleapi_settings(t, emulePwd='wrong'))
    t.keys('a')
    received = t.received(timeout=2)
    t.eq([r['path'] for r in received], ['/__amuleapi/api/v1/auth/login'], 'the login only')
    t.eq(status_line(t), 'aMule refused the password', 'error shown in the popup')
    t.eq(t.dialogs, [], 'no alert while the popup is open')


def test_amuleapi_partial_success(t):
    """SF-7.10: when aMule refuses some links (207), the popup tells how many."""
    t.load(settings=amuleapi_settings(t))
    t.amuleapi(refuse=['example2.avi'])
    t.keys('a')
    t.received(3)
    t.eq(status_line(t), '8 link(s) added to aMule, 1 refused: malformed ed2k link', 'partial result shown')


def test_amuleapi_errors(t):
    """SF-7.10: the other answers of aMule are explained to the user."""
    cases = [({'downloads_status': 503}, None, 'aMule is not connected to its core (amuled)'),
             ({'login_status': 429}, None, 'Too many failed logins to aMule, retry in 30 s'),
             ({'login_status': 403}, None, 'This password can not add downloads: the admin password of aMule is needed'),
             ({}, 'http://127.0.0.1:9/', 'aMule can not be reached at http://127.0.0.1:9/'),
             ({}, 'NOAPI', 'aMule 3.1 or later is needed')]
    for conf, url, expected in cases:
        if url == 'NOAPI':
            url = t.fake_client_url     # a server without the API: every answer is 404... or a page
        t.load(settings=amuleapi_settings(t, **({'emuleUrl': url} if url else {})))
        t.amuleapi(**conf)
        t.keys('a')
        end = time.time() + 8
        while time.time() < end and (status_line(t) or 'Please wait').startswith('Please wait'):
            t.pump(0.2)
        shown = status_line(t) or ''
        t.check(expected in shown, f'{conf or url}: {expected}', shown)


def test_amuleapi_popup_closed(t):
    """SF-7.10 and SF-5.5: with the popup closed, a success is silent, an error is an alert."""
    t.load(settings=amuleapi_settings(t))
    t.keys('c')
    t.keys('a')
    t.eq(len(by_path(t.received(3), 'downloads')), 1, 'the links are sent')
    t.eq(t.dialogs, [], 'success: no alert')
    t.load(settings=amuleapi_settings(t, emulePwd='wrong'), popup_mode=0)
    t.keys('a')
    end = time.time() + 5
    while time.time() < end and not t.dialogs:
        t.pump(0.2)
    t.eq([d for d in t.dialogs], ['Emule Linker: aMule refused the password'], 'error: one alert')


# ---- Test and Import in the settings dialog (amuleapi) ---------------------------------
API_STATUS = ("(function(w){var s=document.getElementById('GM_config_'+w+'Status'); if (!s) return null;"
              "return [['ok','warn','ko'].filter(function(k){return s.classList.contains(k);})[0], s.textContent];})")
API_BUTTONS = ("['GM_config_testBtn','GM_config_importBtn'].map(function(id){var b=document.getElementById(id);"
               "return [b.textContent, b.disabled];})")


def api_status(t, which, timeout=6):
    """The result of Test or Import once shown: [kind, text], kind being ok, warn or ko."""
    end = time.time() + timeout
    while time.time() < end:
        found = t.js(f"{API_STATUS}('{which}')")
        if found:
            return found
        t.pump(0.1)
    return None


def right_edges(t, *selectors):
    return [t.js(f"document.querySelector({s!r}).getBoundingClientRect().right") for s in selectors]


def aligned(*edges):
    """The same edge, within half a pixel: Firefox rounds x.5 positions either way."""
    return max(edges) - min(edges) < 0.5


def test_settings_api_buttons(t):
    """SF-8.16: Test (after Show) and Import (after the Category field) are shown for aMule 3.x
    only, with the style of Show; for the other methods the Category field keeps its whole width."""
    shown = "['GM_config_testBtn','GM_config_importBtn'].map(function(id){return document.getElementById(id).offsetParent != null;})"
    style = ("['.reveal','#GM_config_testBtn','#GM_config_importBtn'].map(function(s){var c=getComputedStyle("
             "document.querySelector('#GM_config '+s));return c.fontSize+' '+c.padding;})")
    t.load(settings=amuleapi_settings(t))
    t.check(t.open_settings(), 'settings dialog opened')
    t.eq(t.js(shown), [True, True], 'aMule 3.x: Test and Import shown')
    t.eq(t.js("[document.getElementById('GM_config_testBtn').title, document.getElementById('GM_config_importBtn').title]"),
         ['Test the server URL and the password', 'Fill the field with the categories of aMule'], 'tooltips')
    t.eq(t.js(style), ['11px 2px 8px'] * 3, 'the style of Show')
    test, imp, url = right_edges(t, '#GM_config_testBtn', '#GM_config_importBtn', '#GM_config_field_emuleUrl')
    t.check(aligned(test, imp, url), 'Test and Import on the right edge of the fields', [test, imp, url])
    t.js("var s = document.getElementById('GM_config_field_serverMethod'); s.value = 'emule'; s.dispatchEvent(new Event('change'))")
    t.eq(t.js(shown), [False, False], 'eMule: no Test, no Import')
    cat, url = right_edges(t, '#GM_config_field_emuleCat', '#GM_config_field_emuleUrl')
    t.check(aligned(cat, url), 'eMule: the Category field as wide as the Server URL', [cat, url])
    t.js("var s = document.getElementById('GM_config_field_serverMethod'); s.value = 'amuleapi'; s.dispatchEvent(new Event('change'))")
    t.eq(t.js(shown), [True, True], 'back to aMule 3.x: shown again')


def test_settings_test_connection(t):
    """SF-8.16 and SF-8.17: Test logs in with the address and the password typed, not saved,
    reads the version and the state of aMule, logs out; the password travels in the login body
    only and nothing is stored. Changing the Server URL or the Password removes the result."""
    t.load(settings=amuleapi_settings(t, emulePwd='old'))
    t.check(t.open_settings(), 'settings dialog opened')
    t.set_field('emulePwd', 'secret')       # typed, not saved
    t.click('#GM_config_testBtn')
    t.eq(api_status(t, 'test'), ['ok', '✔ Connected to aMule 3.1.0 (ed2k: connected, Kad: connected).'], 'connected')
    received = t.received(4)
    t.eq([r['path'].replace('/__amuleapi/api/v1/', '') for r in received], ['auth/login', 'version', 'status', 'auth/logout'],
         'login, version, status, logout')
    t.eq(received[0]['json'], {'password': 'secret'}, 'the password typed, in the login body')
    t.check(not any('secret' in r['path'] or 'secret' in str(r['query']) for r in received), 'never in a url')
    t.eq([t.stored_settings().get('emulePwd'), t.js("JSON.stringify(localStorage).indexOf('fake-token')")], ['old', -1],
         'nothing saved, the token not stored')
    t.eq(t.js(API_BUTTONS), [['Test', False], ['Import', False]], 'buttons enabled again')
    t.js("var f = document.getElementById('GM_config_field_emuleUrl'); f.value += 'x'; f.dispatchEvent(new Event('input'))")
    t.eq(t.js(f"{API_STATUS}('test')"), None, 'Server URL changed: the result removed')


def test_settings_test_answers(t):
    """SF-8.16 and SF-8.17: what Test shows for each answer of aMule; a wrong address is shown
    under the field, without any request."""
    cases = [({}, {'emulePwd': 'wrong'}, ['ko', '✖ aMule refused the password']),
             ({'role': 'guest'}, {}, ['warn', '⚠ Connected to aMule 3.1.0, but this password can not add downloads: '
                                             'the admin password of aMule is needed']),
             ({'ec_connected': False}, {}, ['warn', '⚠ Connected to aMule 3.1.0, but aMule is not connected to its '
                                                    'core (amuled): the links would be refused']),
             ({'login_status': 429}, {}, ['ko', '✖ Too many failed logins to aMule, retry in 30 s']),
             ({}, {'emuleUrl': 'http://127.0.0.1:9/'}, ['ko', '✖ aMule can not be reached at http://127.0.0.1:9/']),
             ({}, {'emuleUrl': 'NOAPI'}, ['ko', '✖ No aMule API at NOAPI (aMule 3.1 or later is needed)']),
             ({}, {'emuleUrl': 'NOSLASH'}, ['ok', '✔ Connected to aMule 3.1.0 (ed2k: connected, Kad: connected).'])]
    for conf, fields, expected in cases:
        t.load(settings=amuleapi_settings(t))
        t.amuleapi(**conf)
        t.check(t.open_settings(), 'settings dialog opened')
        url = {'NOAPI': t.fake_client_url, 'NOSLASH': t.fake_amuleapi_url.rstrip('/')}.get(fields.get('emuleUrl'))
        for key, value in dict(fields, **({'emuleUrl': url} if url else {})).items():
            t.set_field(key, value)
        t.click('#GM_config_testBtn')
        expected = [expected[0], expected[1].replace('NOAPI', t.fake_client_url)]
        t.eq(api_status(t, 'test'), expected, f'{conf or fields}')
    t.load(settings=amuleapi_settings(t))
    t.check(t.open_settings(), 'settings dialog opened')
    t.set_field('emuleUrl', '127.0.0.1:4711')
    t.click('#GM_config_testBtn')
    t.eq(t.js("(document.querySelector('#GM_config_emuleUrl_var .error') || {}).textContent"),
         'An address starting with http:// or https:// is expected, e.g. http://127.0.0.1:4711/', 'wrong address: error under the field')
    t.eq(t.received(timeout=1), [], 'no request')


def test_settings_test_waits(t):
    """SF-8.16: while aMule answers, Test and Import are disabled, the button clicked showing
    "Test..."; an answer that no longer matches the fields is not shown."""
    t.load(settings=amuleapi_settings(t))
    t.amuleapi(login_delay=1.5)
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_testBtn')
    t.eq(t.js(API_BUTTONS), [['Test…', True], ['Import', True]], 'waiting: both disabled')
    t.check(api_status(t, 'test'), 'then the result')
    t.eq(t.js(API_BUTTONS), [['Test', False], ['Import', False]], 'enabled again')
    t.click('#GM_config_testBtn')
    t.js("var f = document.getElementById('GM_config_field_emulePwd'); f.value = 'other'; f.dispatchEvent(new Event('input'))")
    end = time.time() + 5
    while time.time() < end and t.js(API_BUTTONS)[0][1]:
        t.pump(0.1)
    t.eq([t.js(f"{API_STATUS}('test')"), t.js(API_BUTTONS)], [None, [['Test', False], ['Import', False]]],
         'Password changed while waiting: the answer not shown, buttons enabled')


def test_settings_import(t):
    """SF-8.18: Import reads every page of the categories of aMule and fills the field in their
    order, the default one kept; the field is highlighted and the Undo button, under Import with
    the style of Show, puts it back. Save stores the imported categories."""
    t.load(settings=amuleapi_settings(t, emuleCat='*Video=2;Audio=1;Documents=3'))
    t.amuleapi(page_size=2)
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_importBtn')
    t.eq(api_status(t, 'import'), ['ok', '✔ 5 categories imported from aMule: 2 new (Default, Software). '
                                         'Video stays the default (*).'], 'notice')
    t.eq(t.js("document.getElementById('GM_config_field_emuleCat').value"),
         'Default=0;Audio=1;*Video=2;Documents=3;Software=4', 'field filled in the order of aMule')
    pages = [r['query'].get('offset', [''])[0] for r in by_path(t.received(6), 'categories')]
    t.eq(pages, ['0', '2', '4'], 'every page read')
    t.check(t.js("document.getElementById('GM_config_emuleCat_var').classList.contains('changed')"), 'highlighted')
    undo, imp = right_edges(t, '#GM_config_importUndoBtn', '#GM_config_importBtn')
    t.check(aligned(undo, imp), 'Undo under Import', [undo, imp])
    t.eq(t.js("[getComputedStyle(document.getElementById('GM_config_importUndoBtn')).padding,"
              " document.getElementById('GM_config_importUndoBtn').textContent]"), ['2px 8px', '↶ Undo'], 'Undo: style and icon')
    t.click('#GM_config_importUndoBtn')
    t.eq([t.js("document.getElementById('GM_config_field_emuleCat').value"), t.js(f"{API_STATUS}('import')"),
          t.js("document.getElementById('GM_config_emuleCat_var').classList.contains('changed')")],
         ['*Video=2;Audio=1;Documents=3', None, False], 'Undo: the field back, no notice, no highlight')
    t.click('#GM_config_importBtn')
    t.check(api_status(t, 'import'), 'imported again')
    t.click('#GM_config_addServer')
    t.eq(t.js(f"{API_STATUS}('import')"), None, 'the next action removes the notice')
    t.save_settings()
    t.eq([t.stored_settings().get('emuleCat'), json_servers(t)[0].get('emuleCat')],
         ['Default=0;Audio=1;*Video=2;Documents=3;Software=4'] * 2, 'Save: the imported categories stored')


def test_settings_import_answers(t):
    """SF-8.16 and SF-8.18: the field left as it is when the categories can not be read, or
    when it already holds them."""
    cases = [({}, {'emulePwd': 'wrong'}, ['ko', '✖ aMule refused the password']),
             ({'categories_status': 503}, {}, ['ko', '✖ aMule is not connected to its core (amuled)']),
             ({}, {'emuleCat': 'Default=0;Audio=1;*Video=2;Documents=3;Software=4'},
              ['ok', '✔ The field already holds the categories of aMule.'])]
    for conf, fields, expected in cases:
        t.load(settings=amuleapi_settings(t, **dict({'emuleCat': '*Video=2'}, **fields)))
        t.amuleapi(**conf)
        t.check(t.open_settings(), 'settings dialog opened')
        before = t.js("document.getElementById('GM_config_field_emuleCat').value")
        t.click('#GM_config_importBtn')
        t.eq(api_status(t, 'import'), expected, f'{conf or fields}')
        t.eq([t.js("document.getElementById('GM_config_field_emuleCat').value"), t.js("!!document.getElementById('GM_config_importUndoBtn')")],
             [before, False], 'field unchanged, no Undo')


def json_servers(t):
    raw = t.gm('servers')
    return [] if raw is None else json.loads(raw)['list']


# ---- MLDonkey and custom server --------------------------------------------------------
def test_mldonkey(t):
    """SF-7 (mldonkey): one GET on submit, with the multidllink command."""
    t.load(settings=client(t, 'mldonkey'))
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        r = received[0]
        t.eq(r['path'], '/__emule/submit', 'MLDonkey web interface')
        t.eq(param(r, 'jvcmd'), 'multidllink', 'jvcmd=multidllink')
        t.eq(links_of(param(r, 'links')), EXPECTED, 'the 9 links')


def test_custom_server(t):
    """SF-7 (custom) and SF-7.3: a POST form with the category, the page and the links."""
    url = t.base + '/__emule/custom'           # custom: no final / required
    t.load(settings=client(t, 'custom', emuleUrl=url))
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        r = received[0]
        t.eq((r['method'], r['path']), ('POST', '/__emule/custom'), 'POST to the custom URL')
        t.eq(param(r, 'cat', 'form'), '0', 'category field')
        t.eq(param(r, 'ref', 'form'), t.base + '/test_sample.html', 'ref field: the source page')
        t.eq(links_of(param(r, 'ed2k', 'form')), EXPECTED, 'ed2k field: the 9 links')


def custom_settings(t, **changes):
    settings = client(t, 'custom', emuleUrl=t.base + '/__emule/custom')
    settings.update(changes)
    return settings


def test_custom_link_hrefs(t):
    """SF-3.3: with the custom method, the file name links hold the ed2k link, never an empty href."""
    t.load(settings=custom_settings(t))
    hrefs = t.js("[].map.call(document.querySelectorAll('#divBody a.ed2k'), function (a) { return a.getAttribute('href'); })")
    t.eq(len(hrefs), 9, 'popup links')
    t.check(all(h.startswith('ed2k://%7Cfile%7C') for h in hrefs), 'each one holds its encoded ed2k link', hrefs[:1])


def test_custom_single_link_click(t):
    """SF-3.3: with the custom method, clicking a file name sends that file only, by
    POST, and no longer opens a copy of the page."""
    t.load(settings=custom_settings(t))
    mark_link(t, 'Été à Paris (Café).mp3')
    t.click('#__target')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        r = received[0]
        t.eq((r['method'], r['path']), ('POST', '/__emule/custom'), 'POST to the custom URL')
        t.eq(param(r, 'cat', 'form'), '0', 'category field')
        t.eq(param(r, 'ref', 'form'), t.base + '/test_sample.html', 'ref field')
        t.eq(links_of(param(r, 'ed2k', 'form')), {e for e in EXPECTED if e[0] == 'Été à Paris (Café).mp3'}, 'that link only')
    pages = t.open_pages()
    t.eq(sum(u.endswith('/test_sample.html') for u in pages), 1, 'no copy of the page opened')


def test_custom_category_change_then_click(t):
    """SF-6.8 and SF-3.3: after a category change, a click on a file name sends the new category."""
    t.load(settings=custom_settings(t, emuleCat='*Audio=1;Video=2'))
    change_category(t, '2')
    mark_link(t, 'example1.mp3')
    t.click('#__target')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(param(received[0], 'cat', 'form'), '2', 'category sent: Video')


def test_custom_no_form_left(t):
    """The POST forms are removed once sent: they no longer pile up in the page."""
    t.load(settings=custom_settings(t))
    t.keys('a')
    mark_link(t, 'example2.avi')
    t.click('#__target')
    t.eq(len(t.received(2)), 2, 'two requests sent')
    t.eq(t.js("document.querySelectorAll('form').length"), 0, 'no form left in the page')


# ---- nothing to send -----------------------------------------------------------------
def test_nothing_sent_without_links(t):
    """SF-5.6: Ctrl+Alt+A on a page without ed2k links sends nothing."""
    t.load('__nolinks', settings=client(t, 'emule'))
    t.keys('a')
    t.eq(t.received(timeout=2), [], 'no request')
    t.check(t.traced('nothing to send'), 'trace of addButton()')


def test_nothing_sent_when_all_unchecked(t):
    """SF-5.1 and SF-5.6: "check all" unticked, then "Add all links": nothing is sent."""
    t.load(settings=client(t, 'emule'))
    t.js("document.getElementById('checkall').click()")
    t.eq(t.js("document.querySelectorAll('#divBody input:checked').length"), 0, 'every box unchecked')
    click_add_all(t)
    t.eq(t.received(timeout=2), [], 'no request')
