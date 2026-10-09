"""Live: links really added to a running aMule 3.1 (amuleapi method), found, then cancelled.

Run before a release, aMule 3.1 or later running with its REST API (amuleapi):

    python tests/run_tests.py --live-amule

AMULE_URL holds its address (e.g. http://192.168.1.10:4711/), AMULE_PASSWORD its admin
password (EMULE_PASSWORD when not set). The test files carry a random marker in their
name and random hashes, so they cannot be mistaken for real downloads, and they are
cancelled at the end, even when the test fails. Only they are ever touched.

The password never reaches the disk durably: it travels in JSON request bodies only,
from this module and from the script under test, whose settings are kept in a temporary
Chrome profile that run_tests.py deletes (and checks) at the end; nothing printed
shows it, nor the session tokens.
"""
import html
import json
import os
import secrets
import time
import urllib.error
import urllib.request


def missing_settings():
    """What prevents the test from running, checked by run_tests.py before it starts."""
    if not os.environ.get('AMULE_URL'):
        return '--live-amule needs the address of aMule 3.1 in the AMULE_URL environment variable'
    if not password():
        return '--live-amule needs the aMule password in AMULE_PASSWORD (or EMULE_PASSWORD)'
    return None


def amule_url():
    url = os.environ['AMULE_URL']
    return url if url.endswith('/') else url + '/'


def password():
    return os.environ.get('AMULE_PASSWORD') or os.environ.get('EMULE_PASSWORD')


class AmuleApi:
    """Minimal client of the aMule REST API (amuleapi, aMule 3.1)."""

    def __init__(self, base, secret):
        self.api = base + 'api/v1'
        status, answer = self._call('POST', '/auth/login?include_token=true', {'password': secret})
        if status != 200 or not answer.get('token'):
            raise RuntimeError(f'aMule REST API: login failed (HTTP {status})')
        self.token = answer['token']

    def _call(self, method, path, body=None, token=None):
        request = urllib.request.Request(self.api + path, method=method,
                                         data=None if body is None else json.dumps(body).encode())
        request.add_header('Accept', 'application/json')
        if body is not None:
            request.add_header('Content-Type', 'application/json')
        if token:
            request.add_header('Authorization', 'Bearer ' + token)
        try:
            with urllib.request.urlopen(request, timeout=10) as r:
                raw = r.read()
                status = r.status
        except urllib.error.HTTPError as e:
            raw, status = e.read(), e.code
        return status, (json.loads(raw) if raw else {})

    def downloads(self):
        """{hash: download} of the whole transfer list. The API answers page by page (100
        downloads by default): every page is read, so that no test file is missed."""
        found, offset = {}, 0
        while True:
            status, answer = self._call('GET', f'/downloads?limit=500&offset={offset}', token=self.token)
            items = answer.get('downloads', [])
            found.update({d['hash'].upper(): d for d in items})
            offset += len(items)
            if not items or offset >= answer.get('total', 0):
                return found

    def categories(self):
        """The categories of aMule, every page of them, in the order of the API."""
        found = []
        while True:
            status, answer = self._call('GET', f'/categories?limit=100&offset={len(found)}', token=self.token)
            items = answer.get('categories', [])
            found += items
            if not items or len(found) >= answer.get('total', 0):
                return found

    def cancel(self, file_hash):
        self._call('DELETE', f'/downloads/{file_hash}', token=self.token)

    def logout(self):
        try:
            self._call('POST', '/auth/logout', token=self.token)
        except Exception:
            pass


def wait_until(condition, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(1)
    return condition()


def test_live_amule(t):
    """The script really adds the links to aMule 3.1 (method amuleapi), in the chosen category:
    names with spaces, accents, parentheses, & and brackets arrive intact; the popup shows the
    answer of aMule; everything is cancelled at the end."""
    marker = f'emulelinker-test-{secrets.token_hex(3)}'
    files = [(f'{marker}-1.mp3', '1048576'),
             (f'{marker}-2 (Été).mp3', '2097152'),
             (f'{marker}-3 [A&B].mp3', '3145728')]
    hashes = [secrets.token_hex(16).upper() for _ in files]
    links = [f'ed2k://|file|{name}|{size}|{h}|/' for (name, size), h in zip(files, hashes)]
    t.serve('/__live', '<!doctype html><meta charset="utf-8"><title>live test</title>' +
            ''.join(f'<p><a href="{html.escape(link)}">{html.escape(name)}</a></p>'
                    for link, (name, _) in zip(links, files)))

    api = AmuleApi(amule_url(), password())
    try:
        t.check(not any(h in api.downloads() for h in hashes), 'test files absent before')
        t.load('__live', settings={'ed2kDlMethod': 'amuleapi', 'emuleUrl': amule_url(),
                                   'emulePwd': password(), 'emuleCat': '*default=0;'})
        t.eq(t.js('eLinks.length'), 3, 'the 3 test links detected')
        t.keys('a')
        t.check(wait_until(lambda: all(h in api.downloads() for h in hashes), 20),
                'the 3 files appear in the aMule transfer list')
        listing = api.downloads()
        for (name, size), file_hash in zip(files, hashes):
            found = listing.get(file_hash, {})
            t.eq(found.get('name'), name, f'name intact in aMule: {name}')
            t.eq(str(found.get('size_bytes')), size, f'size intact in aMule: {name}')
            t.eq(found.get('category_index'), 0, f'default category in aMule: {name}')
        t.eq(t.js("(document.getElementById('emlStatus') || {}).textContent"),
             '3 link(s) added to aMule', 'the popup shows the answer of aMule')
        t.eq(t.dialogs, [], 'no alert')
    finally:
        for file_hash in hashes:
            try:
                api.cancel(file_hash)
            except Exception:
                pass
        t.check(wait_until(lambda: not any(h in api.downloads() for h in hashes), 20),
                'cleanup: the test files are cancelled and gone from aMule')
        api.logout()


def test_live_amule_test_and_import(t):
    """SF-8.17 and SF-8.18 against a real aMule 3.1: Test connects and gives its version; Import
    fills the Category field with every category of aMule, in its order. Nothing is saved, and
    nothing is changed in aMule. The names of the categories are compared, never printed."""
    api = AmuleApi(amule_url(), password())
    try:
        expected = [(c['index'], c['name']) for c in api.categories()]
    finally:
        api.logout()
    status = ("(function(w){var s=document.getElementById('GM_config_'+w+'Status');"
              "return s ? s.textContent : null;})")
    t.load(settings={'ed2kDlMethod': 'amuleapi', 'emuleUrl': amule_url(), 'emulePwd': password(),
                     'emuleCat': '*default=0;'})
    t.check(t.open_settings(), 'settings dialog opened')
    t.click('#GM_config_testBtn')
    t.check(wait_until(lambda: t.js(f"{status}('test')") is not None, 20), 'Test: a result')
    shown = t.js(f"{status}('test')") or ''
    t.check(shown.startswith('✔ Connected to aMule 3.'), 'Test: connected to aMule 3.x',
            shown if not shown.startswith('✔') else '')
    t.click('#GM_config_importBtn')
    t.check(wait_until(lambda: t.js(f"{status}('import')") is not None, 20), 'Import: a result')
    value = t.js("document.getElementById('GM_config_field_emuleCat').value")
    imported = t.call('strToCat', value)
    imported = [] if imported == -1 else [(int(c['value']), c['name']) for c in imported]
    t.eq(len(imported), len(expected), 'Import: every category of aMule')
    t.check([i for i, _ in imported] == [i for i, _ in expected], 'Import: in the order of aMule')
    t.check(all(n == e or e != e.strip() or any(x in e for x in ';=*') for (_, n), (_, e) in zip(imported, expected)),
            'Import: the names of aMule')
    t.eq(t.stored_settings().get('emuleCat'), '*default=0;', 'nothing saved')
