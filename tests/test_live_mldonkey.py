"""Live: links really added to a running MLDonkey (mldonkey method), found, then cancelled.

Run before a release, MLDonkey running with its web interface:

    python tests/run_tests.py --live-mldonkey

MLDONKEY_URL holds its address (e.g. http://127.0.0.1:4080/), MLDONKEY_USER its user (admin when
not set), MLDONKEY_PASSWORD its password, even empty for an MLDonkey without a password (when not
set: AMULE_PASSWORD or EMULE_PASSWORD). The test files carry a random marker in
their name and random hashes, so they cannot be mistaken for real downloads, and they are
cancelled at the end, by their number in its list (cancel, then confirm yes), even when the test
fails. Only they are ever touched. Nothing printed shows the password.
"""
import base64
import gzip
import html
import os
import re
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request


def missing_settings():
    """What prevents the test from running, checked by run_tests.py before it starts."""
    if not os.environ.get('MLDONKEY_URL'):
        return '--live-mldonkey needs the address of MLDonkey in the MLDONKEY_URL environment variable'
    if password() is None:
        return '--live-mldonkey needs the MLDonkey password in MLDONKEY_PASSWORD (or AMULE_PASSWORD, EMULE_PASSWORD)'
    return None


def mldonkey_url():
    url = os.environ['MLDONKEY_URL']
    return url if url.endswith('/') else url + '/'


def user():
    return os.environ.get('MLDONKEY_USER', 'admin')


def password():
    """MLDONKEY_PASSWORD when set, even empty: an MLDonkey without a password (its admin then accepts an
    empty one, checked on MLDonkey 3.2.1); else AMULE_PASSWORD or EMULE_PASSWORD."""
    if 'MLDONKEY_PASSWORD' in os.environ:
        return os.environ['MLDONKEY_PASSWORD']
    return os.environ.get('AMULE_PASSWORD') or os.environ.get('EMULE_PASSWORD')


class Mldonkey:
    """Minimal client of the MLDonkey web interface (MLDonkey 3.2.1): HTTP Basic on every request."""

    def __init__(self, base):
        self.base = base
        self.auth = 'Basic ' + base64.b64encode(f'{user()}:{password()}'.encode('utf-8')).decode()

    def command(self, q):
        req = urllib.request.Request(self.base + 'submit?q=' + urllib.parse.quote(q))
        req.add_header('Authorization', self.auth)
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read()
        return (gzip.decompress(raw) if raw[:2] == b'\x1f\x8b' else raw).decode('utf-8', 'replace')

    def downloads(self):
        """{name: number} of its downloads, read in its list (vd). MLDonkey 3.2.1 escapes the names twice
        there (A&B shows as A&amp;amp;B): they are unescaped twice."""
        page = self.command('vd')
        return {html.unescape(html.unescape(n)): num
                for n, num in re.findall(r"popLayer\(\\'(.*?)&lt;br&gt;File#: (\d+)", page)}

    def cancel(self, marker):
        """Cancel the downloads whose name holds the marker of the test, and only them."""
        numbers = [num for name, num in self.downloads().items() if marker in name]
        for number in numbers:
            self.command(f'cancel {number}')
        if numbers:
            self.command('confirm yes')


def wait_until(condition, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(1)
    return condition()


def test_live_mldonkey(t):
    """SF-7.14: the script really adds the links to MLDonkey, without a window, with HTTP Basic:
    names with spaces, accents, parentheses, & and brackets arrive intact; the popup shows the
    answer; everything is cancelled at the end."""
    marker = f'emulelinker-test-{secrets.token_hex(3)}'
    files = [(f'{marker}-1.mp3', '1048576'),
             (f'{marker}-2 (Été).mp3', '2097152'),
             (f'{marker}-3 [A&B].mp3', '3145728')]
    hashes = [secrets.token_hex(16).upper() for _ in files]
    links = [f'ed2k://|file|{name}|{size}|{h}|/' for (name, size), h in zip(files, hashes)]
    names = [name for name, _ in files]
    t.serve('/__live', '<!doctype html><meta charset="utf-8"><title>live test</title>' +
            ''.join(f'<p><a href="{html.escape(link)}">{html.escape(name)}</a></p>'
                    for link, (name, _) in zip(links, files)))
    web = Mldonkey(mldonkey_url())
    try:
        t.check(not any(n in web.downloads() for n in names), 'test files absent before')
        t.load('__live', settings={'ed2kDlMethod': 'mldonkey', 'emuleUrl': mldonkey_url(), 'emuleUser': user(),
                                   'emulePwd': password(), 'emuleCat': '*default=0;'})
        t.eq(t.js('eLinks.length'), 3, 'the 3 test links detected')
        t.keys('a')
        t.check(wait_until(lambda: all(n in web.downloads() for n in names), 20),
                'the 3 files in the downloads of MLDonkey, their names intact')
        t.check(wait_until(lambda: t.js("(document.getElementById('emlStatus') || {}).textContent") == '3 link(s) added to MLDonkey', 15),
                'the popup shows the answer', t.js("(document.getElementById('emlStatus') || {}).textContent"))
        t.eq(len(t.open_pages()), 1, 'no window opened')
        t.eq(t.dialogs, [], 'no alert')
    finally:
        try:
            web.cancel(marker)
        except Exception:
            pass
        t.check(wait_until(lambda: not any(marker in n for n in web.downloads()), 20),
                'cleanup: the test files are cancelled and gone from MLDonkey')


def test_live_mldonkey_test_button(t):
    """SF-8.17 against a real MLDonkey: Test connects with the right user and password and gives its
    version, refuses a wrong password. Nothing is saved, nothing is sent."""
    status = "(function(){var s=document.getElementById('GM_config_testStatus');return s ? s.textContent : null;})()"
    for secret, start in ((password(), '\u2714 Connected to MLDonkey'),
                          ('wrong-' + secrets.token_hex(3), '\u2716 MLDonkey refused the user or the password')):
        t.load(settings={'ed2kDlMethod': 'mldonkey', 'emuleUrl': mldonkey_url(), 'emuleUser': user(),
                         'emulePwd': secret, 'emuleCat': '*default=0;'})
        t.check(t.open_settings(), 'settings dialog opened')
        t.click('#GM_config_testBtn')
        t.check(wait_until(lambda: t.js(status) is not None, 20), 'Test: a result')
        shown = t.js(status) or ''
        t.check(shown.startswith(start), f'Test: {start}', shown)
        t.eq(t.stored_settings().get('emulePwd'), secret, 'nothing saved')
