"""Live: links really added to a running aMule 2.x (amule method, amuleweb), found, then cancelled.

Run before a release, aMule 2.x running with its web server (amuleweb):

    python tests/run_tests.py --live-amuleweb

AMULEWEB_URL holds its address (e.g. http://127.0.0.1:14711/), AMULE_PASSWORD its password
(EMULE_PASSWORD when not set). The test files carry a random marker in their name and random
hashes, so they cannot be mistaken for real downloads, and they are cancelled at the end, even
when the test fails. Only they are ever touched. Nothing printed shows the password.
"""
import gzip
import html
import http.client
import http.cookiejar
import os
import re
import secrets
import time
import urllib.parse
import urllib.request


def missing_settings():
    """What prevents the test from running, checked by run_tests.py before it starts."""
    if not os.environ.get('AMULEWEB_URL'):
        return '--live-amuleweb needs the address of aMule 2.x in the AMULEWEB_URL environment variable'
    if not password():
        return '--live-amuleweb needs the aMule password in AMULE_PASSWORD (or EMULE_PASSWORD)'
    return None


def amuleweb_url():
    url = os.environ['AMULEWEB_URL']
    return url if url.endswith('/') else url + '/'


def password():
    return os.environ.get('AMULE_PASSWORD') or os.environ.get('EMULE_PASSWORD')


class AmuleWeb:
    """Minimal client of amuleweb (aMule 2.3.3): a session kept by its cookie, the pages gzip-compressed."""

    def __init__(self, base, secret):
        self.base = base
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        if 'amuleweb-main' not in self.fetch('?pass=' + urllib.parse.quote(secret)):
            raise RuntimeError('amuleweb: login failed (password, or web server off?)')

    def fetch(self, path, data=None):
        """A page of amuleweb. aMule 2.3.3 now and then cuts an answer short, just after an action
        (seen twice over a few runs): the page is then asked again, three times at most."""
        body = None if data is None else urllib.parse.urlencode(data).encode()
        for attempt in range(3):
            try:
                with self.opener.open(urllib.request.Request(self.base + path, data=body), timeout=15) as r:
                    raw = r.read()
                break
            except http.client.IncompleteRead:
                if attempt == 2:
                    raise
                time.sleep(1)
        return (gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw).decode('utf-8', 'replace')

    def downloads(self):
        return html.unescape(self.fetch('amuleweb-main-dload.php'))

    def cancel(self, hashes):
        self.fetch('amuleweb-main-dload.php', dict([('command', 'cancel')] + [(h, 'on') for h in hashes]))

    def in_category(self, file_hash, name):
        """Whether a download is shown by the category filter of amuleweb. The name is given as
        amuleweb 2.3.3 reads it (its UTF-8 bytes taken as Latin-1), else an accented one shows nothing."""
        page = self.fetch('amuleweb-main-dload.php', {'command': 'filter', 'status': 'all',
                                                      'category': name.encode('utf-8').decode('latin-1')})
        self.fetch('amuleweb-main-dload.php', {'command': 'filter', 'status': 'all', 'category': 'all'})
        return file_hash in page

    def categories(self):
        found = re.search(r'<select name="selectcat".*?</select>', self.fetch('footer.php'), re.S)
        return [html.unescape(n) for n in re.findall(r'<option[^>]*>([^<]*)</option>', found.group(0) if found else '')]


def wait_until(condition, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(1)
    return condition()


def test_live_amuleweb(t):
    """SF-7.13: the script really adds the links to aMule 2.x, without a window: names with spaces,
    accents, parentheses, & and brackets arrive intact; the popup shows the answer; everything is
    cancelled at the end."""
    marker = f'emulelinker-test-{secrets.token_hex(3)}'
    files = [(f'{marker}-1.mp3', '1048576'),
             (f'{marker}-2 (Été).mp3', '2097152'),
             (f'{marker}-3 [A&B].mp3', '3145728')]
    hashes = [secrets.token_hex(16).upper() for _ in files]
    links = [f'ed2k://|file|{name}|{size}|{h}|/' for (name, size), h in zip(files, hashes)]
    t.serve('/__live', '<!doctype html><meta charset="utf-8"><title>live test</title>' +
            ''.join(f'<p><a href="{html.escape(link)}">{html.escape(name)}</a></p>'
                    for link, (name, _) in zip(links, files)))
    web = AmuleWeb(amuleweb_url(), password())
    try:
        t.check(not any(h in web.downloads() for h in hashes), 'test files absent before')
        t.load('__live', settings={'ed2kDlMethod': 'amule', 'emuleUrl': amuleweb_url(),
                                   'emulePwd': password(), 'emuleCat': '*all=all'})
        t.eq(t.js('eLinks.length'), 3, 'the 3 test links detected')
        t.keys('a')
        t.check(wait_until(lambda: all(h in web.downloads() for h in hashes), 20), 'the 3 files in the downloads of aMule')
        listing = web.downloads()
        for name, _ in files:
            t.check(name in listing, f'name intact in aMule: {name}')
        t.check(wait_until(lambda: t.js("(document.getElementById('emlStatus') || {}).textContent") == '3 link(s) added to aMule', 15),
                'the popup shows the answer', t.js("(document.getElementById('emlStatus') || {}).textContent"))
        t.eq(len(t.open_pages()), 1, 'no window opened')
        t.eq(t.dialogs, [], 'no alert')
    finally:
        try:
            web.cancel([h for h in hashes if h in web.downloads()])
        except Exception:
            pass
        t.check(wait_until(lambda: not any(h in web.downloads() for h in hashes), 20),
                'cleanup: the test files are cancelled and gone from aMule')


def test_live_amuleweb_accented_category(t):
    """SF-7.13 against a real aMule 2.x: a link sent to a category whose name has accents lands in it
    (aMule 2.3.3 drops it when the name is sent in plain UTF-8). Needs such a category in aMule."""
    web = AmuleWeb(amuleweb_url(), password())
    accented = [c for c in web.categories() if not c.isascii()]
    if not t.check(accented, 'aMule has a category with accents (create one to run this test)'):
        return
    name, size, file_hash = f'emulelinker-test-{secrets.token_hex(3)} (Été).mp3', '1048576', secrets.token_hex(16).upper()
    link = f'ed2k://|file|{name}|{size}|{file_hash}|/'
    t.serve('/__live', f'<!doctype html><meta charset="utf-8"><p><a href="{html.escape(link)}">{html.escape(name)}</a></p>')
    try:
        t.load('__live', settings={'ed2kDlMethod': 'amule', 'emuleUrl': amuleweb_url(), 'emulePwd': password(),
                                   'emuleCat': f'*{accented[0]}={accented[0]}'})
        t.keys('a')
        t.check(wait_until(lambda: file_hash in web.downloads(), 20), 'the file in the downloads of aMule')
        t.check(web.in_category(file_hash, accented[0]), 'in the accented category')
    finally:
        web.cancel([file_hash])
        t.check(wait_until(lambda: file_hash not in web.downloads(), 20), 'cleanup: the test file is cancelled')


def test_live_amuleweb_category_with_equal_or_semicolon(t):
    """SF-6.5, SF-8.18 against a real aMule 2.x: a link sent to a category whose name holds an = (A=B)
    or a ; (test;23), written as Import writes it (A B=A=B, test 23=test\\;23), lands in it. Needs
    such categories in aMule: each one found is checked."""
    web = AmuleWeb(amuleweb_url(), password())
    special = [c for c in web.categories() if '=' in c or ';' in c]
    if not t.check(special, 'aMule has a category whose name holds an = or a ; (create one, e.g. A=B, to run this test)'):
        return
    for category in special:
        name, size, file_hash = f'emulelinker-test-{secrets.token_hex(3)}.mp3', '1048576', secrets.token_hex(16).upper()
        link = f'ed2k://|file|{name}|{size}|{file_hash}|/'
        t.serve('/__live', f'<!doctype html><meta charset="utf-8"><p><a href="{html.escape(link)}">{html.escape(name)}</a></p>')
        shown = category.replace('=', ' ').replace(';', ' ')
        try:
            t.load('__live', settings={'ed2kDlMethod': 'amule', 'emuleUrl': amuleweb_url(), 'emulePwd': password(),
                                       'emuleCat': f"*{shown}={category.replace(';', chr(92) + ';')}"})
            t.keys('a')
            t.check(wait_until(lambda: file_hash in web.downloads(), 20), 'the file in the downloads of aMule')
            t.check(web.in_category(file_hash, category), 'in the category whose name holds an = or a ;')
        finally:
            web.cancel([file_hash])
            t.check(wait_until(lambda: file_hash not in web.downloads(), 20), 'cleanup: the test file is cancelled')


def test_live_amuleweb_test_and_import(t):
    """SF-8.17 and SF-8.18 against a real aMule 2.x: Test connects and gives its version, refuses a
    wrong password; Import fills the Category field with its categories, by name, in its order,
    accents, = and ; included (in the value, the ; written \\;). Nothing is saved, nothing changed
    in aMule. Names compared, never printed."""
    expected = AmuleWeb(amuleweb_url(), password()).categories()
    status = "(function(w){var s=document.getElementById('GM_config_'+w+'Status');return s ? s.textContent : null;})"
    for secret, start in ((password(), '\u2714 Connected to aMule 2.'), ('wrong-' + secrets.token_hex(3), '\u2716 aMule refused the password')):
        t.load(settings={'ed2kDlMethod': 'amule', 'emuleUrl': amuleweb_url(), 'emulePwd': secret, 'emuleCat': '*all=all'})
        t.check(t.open_settings(), 'settings dialog opened')
        t.click('#GM_config_testBtn')
        t.check(wait_until(lambda: t.js(f"{status}('test')") is not None, 20), 'Test: a result')
        shown = t.js(f"{status}('test')") or ''
        t.check(shown.startswith(start), f'Test: {start}', shown)
    t.load(settings={'ed2kDlMethod': 'amule', 'emuleUrl': amuleweb_url(), 'emulePwd': password(), 'emuleCat': '*all=all'})
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_importBtn')
    t.check(wait_until(lambda: t.js(f"{status}('import')") is not None, 20), 'Import: a result')
    imported = t.call('strToCat', t.js("document.getElementById('GM_config_field_emuleCat').value"))
    imported = [] if imported == -1 else [(c['name'], c['value']) for c in imported]
    t.eq(len(imported), len(expected), 'Import: every category of aMule')
    t.check([v for _, v in imported] == expected, 'Import: each value is the name of aMule, in its order, accents, = and ; included')
    t.check(all(n == v or '=' in v or ';' in v for n, v in imported),
            'Import: each name shown is the name of aMule (an = or a ; taken out of it)')
    t.eq(t.stored_settings().get('emuleCat'), '*all=all', 'nothing saved')
