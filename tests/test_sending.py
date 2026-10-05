"""Level 2: sending, received by fake ed2k clients (eMule, aMule, MLDonkey, custom server).

The script really sends its requests, through the browser, to the local test server,
which stands for the web interface of the ed2k client (see Handler in run_tests.py).
Each test checks what an ed2k client would read in them. Nothing reaches a real one.
The references in the comments (SF-x, A-x) point to SPECIFICATIONS.md.
"""
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
    t.cdp.pump(0.2)


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
    """A-9: without a password, the links are sent all the same, with an empty p="""
    t.load(settings=client(t, 'emule', emulePwd=''))
    t.eq(t.dialogs, [], 'no alert')
    t.keys('a')
    received = t.received(1)
    t.eq(len(received), 1, 'one request')
    if received:
        t.eq(param(received[0], 'p'), '', 'empty password sent')
        t.eq(links_of(param(received[0], 'c')), EXPECTED, 'the 9 links')


def test_emule_popup_closed(t):
    """SF-5.5 (A-3): with the popup closed, Ctrl+Alt+A sends every link of the page."""
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
    """SF-6.8 (A-7): a category change keeps the popup as it is (checkboxes, size), only
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
    """SF-6.8 (A-7): in edit mode, a category change keeps the text typed by the user."""
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
    """A-14: with the custom method, the file name links hold the ed2k link, never an empty href."""
    t.load(settings=custom_settings(t))
    hrefs = t.js("[].map.call(document.querySelectorAll('#divBody a.ed2k'), function (a) { return a.getAttribute('href'); })")
    t.eq(len(hrefs), 9, 'popup links')
    t.check(all(h.startswith('ed2k://%7Cfile%7C') for h in hrefs), 'each one holds its encoded ed2k link', hrefs[:1])


def test_custom_single_link_click(t):
    """SF-3.3 (A-14): with the custom method, clicking a file name sends that file only, by
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
    pages = [x['url'] for x in t.chrome.targets() if x['type'] == 'page']
    t.eq(sum(u.endswith('/test_sample.html') for u in pages), 1, 'no copy of the page opened')


def test_custom_category_change_then_click(t):
    """SF-6.8 and A-14: after a category change, a click on a file name sends the new category."""
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
