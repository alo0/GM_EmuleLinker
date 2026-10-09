#!/usr/bin/env python3
"""Automated test suite of GM_EmuleLinker, run in a real headless Chrome or Firefox.

    python tests/run_tests.py                run every test, in Chrome
    python tests/run_tests.py category       run the tests whose name contains "category"
    python tests/run_tests.py --firefox      run them in Firefox instead
    python tests/run_tests.py --chrome --firefox    in Chrome, then in Firefox
    python tests/run_tests.py --live-emule   run the live test against the real eMule
                                             (EMULE_PASSWORD needed, see test_live_emule.py)
    python tests/run_tests.py --live-amule   run the live test against a real aMule 3.1
                                             (AMULE_URL needed, see test_live_amule.py)

The userscript is injected unchanged into the served pages, after a small
stand-in for the GM_* API (gm_shim.js): Tampermonkey is not needed. Chrome is
driven through the DevTools protocol (cdp.py), Firefox through WebDriver BiDi
(bidi.py): the keyboard shortcuts and the clicks are real (trusted) events, and
the alerts are caught. Python standard library only.

Set CHROME_PATH or FIREFOX_PATH if a browser is not found automatically.
"""
import functools
import http.server
import inspect
import json
import re
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.error
import urllib.request
from urllib.parse import parse_qs, urlsplit

sys.dont_write_bytecode = True      # no __pycache__ in the repository
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cdp import CDP                 # noqa: E402
from bidi import BiDi               # noqa: E402
import test_repository             # noqa: E402
import test_units                   # noqa: E402
import test_scenarios               # noqa: E402
import test_sending                 # noqa: E402
import test_live_emule              # noqa: E402
import test_live_amule              # noqa: E402

TEST_MODULES = [test_repository, test_units, test_scenarios, test_sending]
# the live tests, each only with its option, against a real ed2k client
LIVE_MODULES = {'--live-emule': test_live_emule, '--live-amule': test_live_amule}

# Pages served besides the files of the repository
EXTRA_PAGES = {
    # used to prepare the storage of each test: the script is NOT injected there
    '/__blank': '<!doctype html><meta charset="utf-8"><title>blank</title>',
    # a page without any ed2k link, but with a relative link starting with "ed2k"
    '/__nolinks': ('<!doctype html><meta charset="utf-8"><title>No ed2k link</title>'
                   '<p><a href="https://example.com/">An ordinary link</a> and '
                   '<a href="ed2k-guide.html">a relative link</a></p>'),
}

# Default behavior of the fake amuleapi (Handler._fake_amuleapi), changed by T.amuleapi():
# password expected, token given, forced status of the login or of the sending (None: the
# normal answer), parts of link refused by the sending (207 answer), seconds before the
# answer to the sending (a slow aMule); for Test and Import in the settings dialog: role given by
# the login, seconds before the answer to the login, versions, connection state, categories and
# the most categories per page (the real API answers 100 by default)
AMULEAPI = {'password': 'secret', 'token': 'fake-token', 'login_status': None,
            'downloads_status': None, 'refuse': [], 'delay': 0,
            'role': 'admin', 'login_delay': 0, 'version': '3.1.0', 'ec_connected': True,
            'ed2k_state': 'connected', 'kad_state': 'connected', 'categories_status': None,
            'categories': [{'index': 0, 'name': 'Default'}, {'index': 1, 'name': 'Audio'},
                           {'index': 2, 'name': 'Video'}, {'index': 3, 'name': 'Documents'},
                           {'index': 4, 'name': 'Software'}],
            'page_size': 100}

# Injected in every page except /__blank. The script is added as a <script> element
# so that it runs in the page scope, its functions and variables being reachable by
# the tests, and on DOMContentLoaded, close to when Tampermonkey runs it.
BOOTSTRAP = """(function () {
	if (location.pathname === '/__blank') return;
	document.addEventListener('DOMContentLoaded', function () {
		var s = document.createElement('script');
		s.textContent = __SHIM__ + '\\n' + __SCRIPT__;
		document.documentElement.appendChild(s);
	});
})();"""

# The settings dialog of GM_config is open when its container has content
SETTINGS_OPEN = "(function(){var g=document.getElementById('GM_config');return !!(g && g.childNodes.length)})()"


# ---- local web server ---------------------------------------------------------
class Handler(http.server.SimpleHTTPRequestHandler):
    # Requests received by the fake ed2k clients: every URL under /__emule stands for
    # the web interface of eMule, aMule, MLDonkey or a custom server. The script really
    # sends its requests there, and nothing reaches a real ed2k client.
    received = []

    def _send_html(self, page):
        data = page.encode()
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _fake_client(self, body=''):
        url = urlsplit(self.path)
        Handler.received.append({'method': self.command, 'path': url.path,
                                 'query': parse_qs(url.query, keep_blank_values=True),
                                 'form': parse_qs(body, keep_blank_values=True),
                                 'time': time.time()})
        self._send_html('<!doctype html><title>fake ed2k client</title>ok')

    def _send_json(self, status, answer=None, headers=None):
        data = b'' if answer is None else json.dumps(answer).encode()
        self.send_response(status)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        if answer is not None:
            self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    # The fake aMule 3.1 REST API (amuleapi), under /__amuleapi: login, sending, logout, and
    # for the settings dialog version, status and categories, with the answers seen on a real
    # aMule 3.1.0. Its behavior is set by each test through T.amuleapi(), see AMULEAPI above.
    amuleapi = {}

    def _fake_amuleapi(self, body):
        url = urlsplit(self.path)
        path = url.path[len('/__amuleapi'):]
        try:
            data = json.loads(body) if body else None
        except ValueError:
            data = None
        Handler.received.append({'method': self.command, 'path': url.path,
                                 'query': parse_qs(url.query, keep_blank_values=True), 'form': {},
                                 'json': data, 'auth': self.headers.get('Authorization'),
                                 'time': time.time()})
        conf = Handler.amuleapi
        if path == '/api/v1/version' and self.command == 'GET':     # no session needed
            return self._send_json(200, {'service': 'amuleapi', 'api_version': 'v1',
                                         'amuleapi_version': conf['version'], 'daemon_version': conf['version']})
        if path == '/api/v1/auth/login' and self.command == 'POST':
            time.sleep(conf['login_delay'])
            if conf['login_status']:
                return self._send_json(conf['login_status'], {'error': {'code': 'forced', 'message': 'forced'}},
                                       {'Retry-After': '30'} if conf['login_status'] == 429 else None)
            if not isinstance(data, dict) or data.get('password') != conf['password']:
                return self._send_json(401, {'error': {'code': 'unauthorized', 'message': 'invalid credentials'}})
            answer = {'role': conf['role'], 'expires_at': int(time.time()) + 86400, 'session_id': 'fake'}
            if 'include_token=true' in url.query:
                answer['token'] = conf['token']
            return self._send_json(200, answer)
        if self.headers.get('Authorization') != 'Bearer ' + conf['token']:
            return self._send_json(401, {'error': {'code': 'unauthorized', 'message': 'invalid token'}})
        if path == '/api/v1/downloads' and self.command == 'POST':
            time.sleep(conf['delay'])
            if conf['downloads_status']:
                return self._send_json(conf['downloads_status'],
                                       {'error': {'code': 'ec_unavailable', 'message': 'amuled is not connected'}})
            results = []
            for link in data.get('links', []):
                if any(part in link for part in conf['refuse']):
                    results.append({'id': link, 'ok': False,
                                    'error': {'code': 'amuled_rejected', 'message': 'malformed ed2k link'}})
                else:
                    results.append({'id': link, 'ok': True})
            return self._send_json(202 if all(r['ok'] for r in results) else 207, {'results': results})
        if path == '/api/v1/auth/logout' and self.command == 'POST':
            return self._send_json(204)
        if path == '/api/v1/status' and self.command == 'GET':
            return self._send_json(200, {'ec_connected': conf['ec_connected'], 'ed2k': {'state': conf['ed2k_state']},
                                         'kad': {'state': conf['kad_state']}})
        if path == '/api/v1/categories' and self.command == 'GET':
            if conf['categories_status']:
                return self._send_json(conf['categories_status'], {'error': {'code': 'forced', 'message': 'forced'}})
            query = parse_qs(url.query)
            offset = int(query.get('offset', ['0'])[0])
            limit = min(int(query.get('limit', ['100'])[0]), conf['page_size'])
            page = [dict(c, save_path='', comment='', color='#000000', priority='low')
                    for c in conf['categories'][offset:offset + limit]]
            return self._send_json(200, {'categories': page, 'total': len(conf['categories']),
                                         'offset': offset, 'limit': limit})
        self._send_json(404, {'error': {'code': 'not_found', 'message': 'not found'}})

    # GM_xmlhttpRequest of gm_shim.js: the request is made from here, as Tampermonkey makes
    # it outside the page, so that it is not subject to CORS. Nothing is recorded or printed.
    def _gmxhr(self, body):
        d = json.loads(body)
        data = None if d.get('data') is None else d['data'].encode('utf-8')
        request = urllib.request.Request(d['url'], data=data, method=d.get('method', 'GET'),
                                         headers=d.get('headers') or {})
        timeout = (d.get('timeout') or 15000) / 1000
        try:
            try:
                with urllib.request.urlopen(request, timeout=timeout) as r:
                    status, headers, raw = r.status, r.headers, r.read()
            except urllib.error.HTTPError as e:
                status, headers, raw = e.code, e.headers, e.read()
            answer = {'status': status, 'responseText': raw.decode('utf-8', 'replace'),
                      'responseHeaders': ''.join(f'{k}: {v}\r\n' for k, v in headers.items())}
        except (socket.timeout, TimeoutError):
            answer = {'error': 'timeout'}
        except (urllib.error.URLError, OSError) as e:
            answer = {'error': type(e).__name__}
        self._send_json(200, answer)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path.startswith('/__emule'):
            return self._fake_client()
        if path.startswith('/__amuleapi'):
            return self._fake_amuleapi('')
        page = EXTRA_PAGES.get(path)
        if page is None:
            return super().do_GET()
        self._send_html(page)

    def do_POST(self):
        path = self.path.split('?')[0]
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        if path.startswith('/__emule'):
            return self._fake_client(body)
        if path.startswith('/__amuleapi'):
            return self._fake_amuleapi(body)
        if path == '/__gmxhr':
            return self._gmxhr(body)
        self.send_error(405)

    def log_message(self, *args):
        pass


class Server(http.server.ThreadingHTTPServer):
    def handle_error(self, request, client_address):
        # a request given up by the browser (Firefox asks for a favicon, then closes the
        # connection when the page changes): nothing went wrong, nothing to print
        if not isinstance(sys.exc_info()[1], (ConnectionError, TimeoutError)):
            super().handle_error(request, client_address)


def start_server():
    server = Server(('127.0.0.1', 0), functools.partial(Handler, directory=ROOT))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f'http://127.0.0.1:{server.server_address[1]}'


def stop_server(server):
    server.shutdown()
    server.server_close()       # also release the listening socket


# ---- headless Chrome ----------------------------------------------------------
def find_chrome():
    candidates = [os.environ.get('CHROME_PATH'),
                  r'C:\Program Files\Google\Chrome\Application\chrome.exe',
                  r'C:\Program Files (x86)\Google\Chrome\Application\chrome.exe',
                  '/cygdrive/c/Program Files/Google/Chrome/Application/chrome.exe',
                  '/cygdrive/c/Program Files (x86)/Google/Chrome/Application/chrome.exe',
                  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    for c in candidates:
        if c and sys.platform == 'cygwin' and '\\' in c:
            # Cygwin sees a Windows path but cannot run it: convert it first
            c = subprocess.check_output(['cygpath', '-u', c], text=True).strip()
        if c and os.path.exists(c):
            return c
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser', 'chrome'):
        found = shutil.which(name)
        if found:
            return found
    sys.exit('Chrome not found: set the CHROME_PATH environment variable')


def native_path(path):
    """Chrome is a native program: under Cygwin, hand it a Windows path."""
    if sys.platform == 'cygwin':
        return subprocess.check_output(['cygpath', '-w', path], text=True).strip()
    return path


def remove_profile(path):
    """Delete a temporary browser profile; False if it could not be deleted."""
    for _ in range(20):                         # the browser may hold its files a little longer
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            return True
        time.sleep(0.5)
    return False


class Chrome:
    name = 'Chrome'

    def __init__(self):
        self.profile = tempfile.mkdtemp(prefix='gm-emulelinker-tests-')
        self.proc = subprocess.Popen(
            [find_chrome(), '--headless=new', '--remote-debugging-port=0',
             f'--user-data-dir={native_path(self.profile)}', '--no-first-run',
             '--no-default-browser-check', '--disable-extensions', '--disable-gpu', 'about:blank'],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # with port 0, Chrome picks a free port and writes it in DevToolsActivePort
        port_file = os.path.join(self.profile, 'DevToolsActivePort')
        end = time.time() + 20
        while not os.path.exists(port_file) or os.path.getsize(port_file) == 0:
            if time.time() > end:
                self.close()
                sys.exit('Chrome did not start')
            time.sleep(0.1)
        with open(port_file) as f:
            lines = f.read().split()
        self.port, self.browser_path = int(lines[0]), lines[1]
        version = json.load(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json/version'))
        self.version = version.get('Browser', '').split('/')[-1]

    def targets(self):
        return json.load(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json/list'))

    def page(self):
        main = next(t for t in self.targets() if t['type'] == 'page')
        self.main_id = main['id']
        return CDP(main['webSocketDebuggerUrl'])

    def prepare(self, page, script):
        """Ready the page for the tests: events, and the script injected into every page."""
        for domain in ('Page.enable', 'Runtime.enable'):
            page.call(domain)
        page.call('Emulation.setFocusEmulationEnabled', {'enabled': True})
        page.call('Page.addScriptToEvaluateOnNewDocument', {'source': script})

    def page_urls(self):
        """The addresses of the open tabs and windows, those opened by the script included."""
        return [t['url'] for t in self.targets() if t['type'] == 'page']

    def close_other_tabs(self):
        """Close the windows opened by the script (window.open, form target)."""
        for t in self.targets():
            if t['type'] == 'page' and t['id'] != self.main_id:
                try:
                    urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json/close/{t["id"]}').read()
                except Exception:
                    pass

    def close(self):
        """Stop Chrome and delete its temporary profile. Return False if the profile
        could not be deleted: it may hold what the pages stored (settings, history)."""
        browser = None
        try:
            browser = CDP(f'ws://127.0.0.1:{self.port}{self.browser_path}')
            browser.call('Browser.close', timeout=5)
        except Exception:
            pass
        finally:
            if browser:
                browser.close()
        try:
            self.proc.wait(10)
        except Exception:
            self.proc.kill()
        return remove_profile(self.profile)


# ---- headless Firefox -----------------------------------------------------------
def find_firefox():
    candidates = [os.environ.get('FIREFOX_PATH'),
                  r'C:\Program Files\Mozilla Firefox\firefox.exe',
                  r'C:\Program Files (x86)\Mozilla Firefox\firefox.exe',
                  '/Applications/Firefox.app/Contents/MacOS/firefox']
    for c in candidates:
        if c and os.path.exists(c):
            return c
    found = shutil.which('firefox')
    if found:
        return found
    sys.exit('Firefox not found: set the FIREFOX_PATH environment variable')


# preferences of the temporary Firefox profile: no first-run page, no update, no telemetry
FIREFOX_PREFS = {'browser.shell.checkDefaultBrowser': False, 'browser.aboutwelcome.enabled': False,
                 'browser.startup.homepage_override.mstone': 'ignore', 'app.update.disabledForTesting': True,
                 'datareporting.policy.dataSubmissionEnabled': False, 'toolkit.telemetry.reportingpolicy.firstRun': False}


class Firefox:
    """Headless Firefox, driven through WebDriver BiDi (bidi.py), with a temporary profile."""
    name = 'Firefox'

    def __init__(self):
        self.profile = tempfile.mkdtemp(prefix='gm-emulelinker-tests-')
        with open(os.path.join(self.profile, 'user.js'), 'w', encoding='utf-8') as f:
            f.writelines(f'user_pref({json.dumps(k)}, {json.dumps(v)});\n' for k, v in FIREFOX_PREFS.items())
        with socket.socket() as s:                  # a free port for WebDriver BiDi
            s.bind(('127.0.0.1', 0))
            port = s.getsockname()[1]
        self.proc = subprocess.Popen(
            [find_firefox(), '-headless', '-no-remote', '-profile', native_path(self.profile),
             '--remote-debugging-port', str(port)],
            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
        # Firefox writes the address of WebDriver BiDi on its error output, which must then be
        # read until it stops, or Firefox would block on it once its buffer is full
        self.endpoint = None
        threading.Thread(target=self._read_errors, daemon=True).start()
        end = time.time() + 30
        while self.endpoint is None:
            if time.time() > end or self.proc.poll() is not None:
                self.close()
                sys.exit('Firefox did not start')
            time.sleep(0.1)
        self.bidi = BiDi(self.endpoint.rstrip('/') + '/session')
        caps = self.bidi.call('session.new', {'capabilities': {'alwaysMatch': {
            'unhandledPromptBehavior': {'default': 'ignore'}}}})['capabilities']   # bidi.py accepts them
        self.version = caps.get('browserVersion', '')
        self.bidi.call('session.subscribe', {'events': ['log.entryAdded', 'browsingContext.userPromptOpened',
                                                        'browsingContext.load']})
        self.main_id = self.bidi.contexts()[0][0]
        self.bidi.context = self.main_id

    def _read_errors(self):
        for line in self.proc.stderr:
            if self.endpoint is None and 'WebDriver BiDi listening on' in line:
                self.endpoint = line.split('listening on', 1)[1].strip()

    def page(self):
        return self.bidi

    def prepare(self, page, script):
        page.call('script.addPreloadScript', {'functionDeclaration': '() => { ' + script + ' }'})

    def page_urls(self):
        return [url for _, url in self.bidi.contexts()]

    def close_other_tabs(self):
        """Close the windows opened by the script (window.open, form target)."""
        for context, _ in self.bidi.contexts():
            if context != self.main_id:
                try:
                    self.bidi.call('browsingContext.close', {'context': context}, timeout=5)
                except Exception:
                    pass

    def close(self):
        """Stop Firefox and delete its temporary profile. Return False if the profile
        could not be deleted: it may hold what the pages stored (settings, history)."""
        bidi = getattr(self, 'bidi', None)
        if bidi:
            try:
                bidi.call('browser.close', {}, timeout=5)
            except Exception:
                pass
            bidi.close()
        try:
            self.proc.wait(10)
        except Exception:
            self.proc.kill()
            self.proc.wait(10)
        return remove_profile(self.profile)


BROWSERS = {'--chrome': Chrome, '--firefox': Firefox}


# ---- what a test receives --------------------------------------------------------
class T:
    """Test context: drives the page and records the checks."""

    def __init__(self, driver, base_url, browser):
        self.driver = driver            # the page: cdp.CDP (Chrome) or bidi.BiDi (Firefox)
        self.base = base_url
        self.browser = browser          # Chrome or Firefox
        self.checks = []                # (ok, label, detail)

    # -- checks
    def check(self, ok, label, detail=''):
        self.checks.append((bool(ok), label, detail))
        return ok

    def eq(self, actual, expected, label):
        return self.check(actual == expected, label,
                          '' if actual == expected else f'expected {expected!r}, got {actual!r}')

    # -- page
    def _navigate(self, path):
        self.driver.navigate(self.base + path)
        self.driver.pump(0.2)

    def load(self, page='test_sample.html', settings=None, emule_config=1, popup_mode=1, debug=1):
        """Open a page with a fresh storage. settings: the GM_config values to store
        (None: nothing stored, the script defaults apply). emule_config=None simulates
        the very first run of the script. debug: the debug traces are on by default, as
        many checks read them; None leaves the setting unstored, as on a new installation."""
        self.browser.close_other_tabs()
        Handler.received.clear()
        Handler.amuleapi = dict(AMULEAPI)
        self._navigate('/__blank')
        seed = {'emule_config': emule_config, 'popup_mode': popup_mode, 'debug_mode': debug,
                'GM_config': None if settings is None else json.dumps(settings)}
        self.driver.js('localStorage.clear();' + ''.join(
            f'localStorage.setItem({json.dumps("gm:" + k)}, {json.dumps(json.dumps(v))});'
            for k, v in seed.items() if v is not None))
        self.driver.dialogs.clear()
        self.driver.console.clear()
        self.driver.errors.clear()
        self._navigate('/' + page.lstrip('/'))

    def reload(self):
        self.driver.reload()
        self.driver.pump(0.2)

    def serve(self, path, page):
        """Serve a page made by the test, at the given path."""
        EXTRA_PAGES[path] = page

    def js(self, expression):
        return self.driver.js(expression)

    def call(self, function, *args):
        """Call a function of the script with JSON arguments, return its JSON result."""
        return self.driver.js(f'{function}({", ".join(json.dumps(a) for a in args)})')

    def pump(self, seconds):
        """Let the page run for a while, its events (dialogs, console, load) processed."""
        self.driver.pump(seconds)

    def press(self, key):
        """A key pressed by the user: Escape."""
        self.driver.press(key)
        self.driver.pump(0.2)

    def type_text(self, text):
        """Text typed by the user in the focused field."""
        self.driver.type_text(text)
        self.driver.pump(0.2)

    def set_viewport(self, width, height):
        """The size of the window, in CSS pixels; clear_viewport() goes back to the default one."""
        self.driver.set_viewport(width, height)

    def clear_viewport(self):
        self.driver.clear_viewport()

    def open_pages(self):
        """The addresses of the open tabs and windows, those opened by the script included."""
        return self.browser.page_urls()

    def keys(self, letter):
        """Ctrl+Alt+<letter>, as typed by the user."""
        self.driver.ctrl_alt(letter)
        self.driver.pump(0.2)

    def click(self, selector):
        """A real mouse click on the element, as done by the user."""
        x, y = self.driver.js(
            f"(function(){{var e=document.querySelector({json.dumps(selector)});"
            "e.scrollIntoView({block:'center'});var b=e.getBoundingClientRect();"
            "return [b.left+b.width/2, b.top+b.height/2];})()")
        self.driver.click(x, y)
        self.driver.pump(0.2)

    # -- what the fake ed2k clients received (see Handler)
    @property
    def fake_client_url(self):
        return self.base + '/__emule/'

    @property
    def fake_amuleapi_url(self):
        return self.base + '/__amuleapi/'

    def amuleapi(self, **changes):
        """Change the behavior of the fake amuleapi for this test (see AMULEAPI)."""
        Handler.amuleapi.update(changes)

    def received(self, count=None, timeout=4):
        """The requests received by the fake ed2k clients. With count: wait until that
        many arrived, then a little more to catch an unexpected extra one. Without:
        wait the whole timeout, to make sure that nothing arrives."""
        end = time.time() + timeout
        while time.time() < end and (count is None or len(Handler.received) < count):
            self.driver.pump(0.1)
        if count is not None:
            self.driver.pump(0.3)
        return list(Handler.received)

    @property
    def dialogs(self):
        return self.driver.dialogs

    @property
    def console(self):
        return self.driver.console

    @property
    def errors(self):
        """Uncaught JavaScript exceptions of the page since the last load."""
        return self.driver.errors

    def menu(self, key):
        """Call a userscript manager menu command, the way Tampermonkey does."""
        self.driver.js(f'window.__GM_menu[{json.dumps(key)}]()')
        self.driver.pump(0.2)

    def traced(self, text):
        return any(text in line for line in self.driver.console)

    # -- storage
    def gm(self, name):
        raw = self.driver.js(f'localStorage.getItem({json.dumps("gm:" + name)})')
        return None if raw is None else json.loads(raw)

    def stored_settings(self):
        raw = self.gm('GM_config')
        return {} if raw is None else json.loads(raw)

    # -- settings dialog
    def settings_open(self):
        return bool(self.driver.js(SETTINGS_OPEN))

    def open_settings(self):
        self.keys('s')
        return self.driver.wait_for(SETTINGS_OPEN, 5)

    def close_settings(self):
        self.driver.js("document.getElementById('GM_config_closeBtn').click()")
        self.driver.pump(0.2)

    def set_field(self, field, value):
        self.driver.js(f"document.getElementById('GM_config_field_{field}').value = {json.dumps(value)}")

    def save_settings(self):
        """Press Save: the script reloads the page."""
        self.driver.dialogs.clear()
        self.driver.console.clear()
        before = self.driver.loaded
        self.driver.js("document.getElementById('GM_config_saveBtn').click()")
        self.driver.wait_load(before)
        self.driver.pump(0.2)

    # -- local method: the ed2k: links cannot reach a fake client, the clicks are caught
    def catch_anchor_clicks(self):
        self.driver.js("window.__clicked = []; HTMLAnchorElement.prototype.click = function () "
                    "{ window.__clicked.push(this.getAttribute('href')); }")

    def clicked(self):
        return self.driver.js('window.__clicked')


# ---- runner ----------------------------------------------------------------------
def tests_of(module):
    found = [f for name, f in inspect.getmembers(module, inspect.isfunction)
             if name.startswith('test_') and f.__module__ == module.__name__]
    return sorted(found, key=lambda f: inspect.getsourcelines(f)[1])


def bootstrap_source():
    with open(os.path.join(HERE, 'gm_shim.js'), encoding='utf-8') as f:
        shim = f.read()
    with open(os.path.join(ROOT, 'GM_EmuleLinker.user.js'), encoding='utf-8') as f:
        script = f.read()
    # GM_info, as Tampermonkey gives it: the name and the version read in the header of the script
    info = {key: re.search(r'^// @' + key + r'\s+(.+?)\s*$', script, re.M).group(1) for key in ('name', 'version')}
    shim = f'var GM_info = {{script: {json.dumps(info)}}};\n' + shim
    return BOOTSTRAP.replace('__SHIM__', json.dumps(shim)).replace('__SCRIPT__', json.dumps(script))


def mask(text):
    """Never show the eMule or aMule password, whatever a message may contain."""
    for name in ('EMULE_PASSWORD', 'AMULE_PASSWORD'):
        secret = os.environ.get(name)
        if secret:
            text = text.replace(secret, '***')
    return text


def start_session(browser_class=None):
    """Start the web server and a headless browser (Chrome by default, or Firefox), ready for
    the tests: the script is injected into every served page. Shared by this runner,
    vscode_tests.py and take_screenshots.py.
    Return (server, base_url, browser, driver); stop them with stop_session()."""
    server, base = start_server()
    browser = (browser_class or Chrome)()
    try:
        driver = browser.page()
        browser.prepare(driver, bootstrap_source())
    except Exception:
        browser.close()
        stop_server(server)
        raise
    return server, base, browser, driver


def stop_session(server, browser, driver):
    """Stop what start_session() started. Return False if the temporary browser profile
    could not be deleted: it may hold what the pages stored."""
    driver.close()
    removed = browser.close()
    stop_server(server)
    return removed


def main():
    args = sys.argv[1:]
    live = [option for option in LIVE_MODULES if option in args]
    selection = next((a for a in args if not a.startswith('--')), '')
    modules = [LIVE_MODULES[option] for option in live] if live else TEST_MODULES
    browsers = [BROWSERS[option] for option in BROWSERS if option in args] or [Chrome]
    for module in modules:
        missing = getattr(module, 'missing_settings', lambda: None)()
        if missing:
            sys.exit(missing)
    results = []
    for browser_class in browsers:
        results.append(run(browser_class, modules, selection, live))
    if len(results) > 1:
        print('\n' + '\n'.join(f'{name}: {passed} passed, {failed} failed' for name, passed, failed in results))
    sys.exit(1 if any(failed for _, _, failed in results) else 0)


def run(browser_class, modules, selection, live):
    """Run the tests in one browser; return (its name, passed, failed)."""
    server, base, browser, driver = start_session(browser_class)
    print(f'\n=== {browser.name} {browser.version} ===')
    passed = failed = 0
    start = time.time()
    try:
        for module in modules:
            print(f'\n{module.__name__}  ({(module.__doc__ or "").strip().splitlines()[0]})')
            for test in tests_of(module):
                if selection not in test.__name__:
                    continue
                t = T(driver, base, browser)
                try:
                    test(t)
                except Exception as e:
                    t.checks.append((False, 'unexpected error', ''.join(
                        traceback.format_exception_only(type(e), e)).strip()))
                bad = [c for c in t.checks if not c[0]]
                if bad:
                    failed += 1
                    print(f'  FAIL  {test.__name__}  ({len(t.checks) - len(bad)}/{len(t.checks)} checks)')
                    for _, label, detail in bad:
                        print(mask(f'          - {label}' + (f': {detail}' if detail else '')))
                else:
                    passed += 1
                    print(f'  ok    {test.__name__}  ({len(t.checks)} checks)')
    finally:
        if not stop_session(server, browser, driver):
            failed += 1
            print(f'\nERROR: the temporary {browser.name} profile could not be deleted: {browser.profile}'
                  '\n       It may hold the settings stored by the tests' +
                  (', password included: delete it by hand.' if live else '.'))

    print(f'\n{browser.name}: {passed} passed, {failed} failed  ({time.time() - start:.1f} s)')
    return browser.name, passed, failed


if __name__ == '__main__':
    main()
