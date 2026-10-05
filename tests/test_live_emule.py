"""Live: links really added to the running eMule, found in its transfer list, then cancelled.

Run before a release, eMule running with its web server enabled:

    python tests/run_tests.py --live-emule

EMULE_PASSWORD holds the web interface password; EMULE_URL its address
(default http://127.0.0.1:4711/). The test files carry a random marker in their
name and random hashes, so they cannot be mistaken for real downloads, and they
are cancelled at the end, even when the test fails. Only they are ever touched.

The password never reaches the disk durably: this module sends it to eMule in POST
bodies only; the script under test puts it in its GET URL, but inside a temporary
Chrome profile that run_tests.py deletes (and checks) at the end; nothing printed
shows it.
"""
import gzip
import html
import os
import re
import secrets
import time
import urllib.parse
import urllib.request
import zlib


def emule_url():
    url = os.environ.get('EMULE_URL', 'http://127.0.0.1:4711/')
    return url if url.endswith('/') else url + '/'


class EmuleWeb:
    """Minimal client of the eMule web interface (eMule 0.70b). The password only
    travels in POST bodies; the transfer page comes gzip-compressed."""

    def __init__(self, base, password):
        self.base = base
        page = self._fetch(base, {'w': 'password', 'p': password})
        found = re.search(r'ses=(-?\d+)', page)
        if not found:
            raise RuntimeError('eMule web interface: login failed (password, or web server off?)')
        self.ses = found.group(1)

    @staticmethod
    def _fetch(url, data=None):
        body = None if data is None else urllib.parse.urlencode(data).encode()
        with urllib.request.urlopen(urllib.request.Request(url, data=body), timeout=10) as r:
            raw = r.read()
            encoding = (r.headers.get('Content-Encoding') or '').lower()
        if encoding == 'gzip' or raw[:2] == bytes([0x1f, 0x8b]):
            raw = gzip.decompress(raw)
        elif encoding == 'deflate':
            raw = zlib.decompress(raw, -zlib.MAX_WBITS)
        return raw.decode('utf-8', 'replace')

    def transfers(self):
        return html.unescape(self._fetch(f'{self.base}?ses={self.ses}&w=transfer'))

    def cancel(self, file_hash):
        self._fetch(f'{self.base}?ses={self.ses}&w=transfer&op=cancel&file={file_hash}')

    def logout(self):
        try:
            self._fetch(f'{self.base}?ses={self.ses}&w=logout')
        except Exception:
            pass


def wait_until(condition, timeout):
    end = time.time() + timeout
    while time.time() < end:
        if condition():
            return True
        time.sleep(1)
    return condition()


def test_live_emule(t):
    """The script really adds the links to eMule (method emule): names with spaces, accents,
    parentheses, & and brackets arrive intact; everything is cancelled at the end."""
    password = os.environ['EMULE_PASSWORD']
    marker = f'emulelinker-test-{secrets.token_hex(3)}'
    files = [(f'{marker}-1.mp3', '1048576'),
             (f'{marker}-2 (Été).mp3', '2097152'),
             (f'{marker}-3 [A&B].mp3', '3145728')]
    hashes = [secrets.token_hex(16).upper() for _ in files]
    links = [f'ed2k://|file|{name}|{size}|{h}|/' for (name, size), h in zip(files, hashes)]
    t.serve('/__live', '<!doctype html><meta charset="utf-8"><title>live test</title>' +
            ''.join(f'<p><a href="{html.escape(link)}">{html.escape(name)}</a></p>'
                    for link, (name, _) in zip(links, files)))

    web = EmuleWeb(emule_url(), password)
    try:
        t.check(not any(name in web.transfers() for name, _ in files), 'test files absent before')
        t.load('__live', settings={'ed2kDlMethod': 'emule', 'emuleUrl': emule_url(),
                                   'emulePwd': password, 'emuleCat': '*default=0;'})
        t.eq(t.js('eLinks.length'), 3, 'the 3 test links detected')
        t.keys('a')
        t.check(wait_until(lambda: all(name in web.transfers() for name, _ in files), 20),
                'the 3 files appear in the eMule transfer list')
        listing = web.transfers()
        for (name, _), file_hash in zip(files, hashes):
            t.check(name in listing, f'name intact in eMule: {name}')
            t.check(file_hash in listing, f'hash intact in eMule: {name}')
    finally:
        for file_hash in hashes:
            try:
                web.cancel(file_hash)
            except Exception:
                pass
        t.check(wait_until(lambda: not any(name in web.transfers() for name, _ in files), 20),
                'cleanup: the test files are cancelled and gone from eMule')
        web.logout()
