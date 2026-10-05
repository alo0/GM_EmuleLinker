#!/usr/bin/env python3
"""Automated test suite of GM_EmuleLinker, run in a real headless Chrome.

    python tests/run_tests.py                run every test
    python tests/run_tests.py category       run the tests whose name contains "category"
    python tests/run_tests.py --live-emule   run the live test against the real eMule
                                             (EMULE_PASSWORD needed, see test_live_emule.py)

The userscript is injected unchanged into the served pages, after a small
stand-in for the GM_* API (gm_shim.js): Tampermonkey is not needed. Chrome is
driven through the DevTools protocol, so the keyboard shortcuts are real
(trusted) events and the alerts are caught. Python standard library only.

Set CHROME_PATH if Chrome is not found automatically.
"""
import functools
import http.server
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import urllib.request
from urllib.parse import parse_qs, urlsplit

sys.dont_write_bytecode = True      # no __pycache__ in the repository
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from cdp import CDP                 # noqa: E402
import test_repository              # noqa: E402
import test_units                   # noqa: E402
import test_scenarios               # noqa: E402
import test_sending                 # noqa: E402
import test_live_emule              # noqa: E402

TEST_MODULES = [test_repository, test_units, test_scenarios, test_sending]
LIVE_MODULES = [test_live_emule]    # only with --live-emule

# Pages served besides the files of the repository
EXTRA_PAGES = {
    # used to prepare the storage of each test: the script is NOT injected there
    '/__blank': '<!doctype html><meta charset="utf-8"><title>blank</title>',
    # a page without any ed2k link, but with a relative link starting with "ed2k"
    '/__nolinks': ('<!doctype html><meta charset="utf-8"><title>No ed2k link</title>'
                   '<p><a href="https://example.com/">An ordinary link</a> and '
                   '<a href="ed2k-guide.html">a relative link</a></p>'),
}

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

    def do_GET(self):
        path = self.path.split('?')[0]
        if path.startswith('/__emule'):
            return self._fake_client()
        page = EXTRA_PAGES.get(path)
        if page is None:
            return super().do_GET()
        self._send_html(page)

    def do_POST(self):
        if self.path.split('?')[0].startswith('/__emule'):
            length = int(self.headers.get('Content-Length', 0))
            return self._fake_client(self.rfile.read(length).decode('utf-8'))
        self.send_error(405)

    def log_message(self, *args):
        pass


def start_server():
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
                                             functools.partial(Handler, directory=ROOT))
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


class Chrome:
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

    def targets(self):
        return json.load(urllib.request.urlopen(f'http://127.0.0.1:{self.port}/json/list'))

    def page(self):
        main = next(t for t in self.targets() if t['type'] == 'page')
        self.main_id = main['id']
        return CDP(main['webSocketDebuggerUrl'])

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
        for _ in range(20):                         # Chrome may hold its files a little longer
            shutil.rmtree(self.profile, ignore_errors=True)
            if not os.path.exists(self.profile):
                return True
            time.sleep(0.5)
        return False


# ---- what a test receives --------------------------------------------------------
class T:
    """Test context: drives the page and records the checks."""

    def __init__(self, cdp, base_url, chrome):
        self.cdp = cdp
        self.base = base_url
        self.chrome = chrome
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
        before = self.cdp.loaded
        self.cdp.call('Page.navigate', {'url': self.base + path})
        self.cdp.wait_load(before)
        self.cdp.pump(0.2)

    def load(self, page='test_sample.html', settings=None, emule_config=1, popup_mode=1, debug=1):
        """Open a page with a fresh storage. settings: the GM_config values to store
        (None: nothing stored, the script defaults apply). emule_config=None simulates
        the very first run of the script. debug: the debug traces are on by default, as
        many checks read them; None leaves the setting unstored, as on a new installation."""
        self.chrome.close_other_tabs()
        Handler.received.clear()
        self._navigate('/__blank')
        seed = {'emule_config': emule_config, 'popup_mode': popup_mode, 'debug_mode': debug,
                'GM_config': None if settings is None else json.dumps(settings)}
        self.cdp.js('localStorage.clear();' + ''.join(
            f'localStorage.setItem({json.dumps("gm:" + k)}, {json.dumps(json.dumps(v))});'
            for k, v in seed.items() if v is not None))
        self.cdp.dialogs.clear()
        self.cdp.console.clear()
        self.cdp.errors.clear()
        self._navigate('/' + page.lstrip('/'))

    def reload(self):
        before = self.cdp.loaded
        self.cdp.call('Page.reload')
        self.cdp.wait_load(before)
        self.cdp.pump(0.2)

    def serve(self, path, page):
        """Serve a page made by the test, at the given path."""
        EXTRA_PAGES[path] = page

    def js(self, expression):
        return self.cdp.js(expression)

    def call(self, function, *args):
        """Call a function of the script with JSON arguments, return its JSON result."""
        return self.cdp.js(f'{function}({", ".join(json.dumps(a) for a in args)})')

    def keys(self, letter):
        """Ctrl+Alt+<letter>, as typed by the user."""
        self.cdp.ctrl_alt(letter)
        self.cdp.pump(0.2)

    def click(self, selector):
        """A real mouse click on the element, as done by the user."""
        x, y = self.cdp.js(
            f"(function(){{var e=document.querySelector({json.dumps(selector)});"
            "e.scrollIntoView({block:'center'});var b=e.getBoundingClientRect();"
            "return [b.left+b.width/2, b.top+b.height/2];})()")
        self.cdp.click(x, y)
        self.cdp.pump(0.2)

    # -- what the fake ed2k clients received (see Handler)
    @property
    def fake_client_url(self):
        return self.base + '/__emule/'

    def received(self, count=None, timeout=4):
        """The requests received by the fake ed2k clients. With count: wait until that
        many arrived, then a little more to catch an unexpected extra one. Without:
        wait the whole timeout, to make sure that nothing arrives."""
        end = time.time() + timeout
        while time.time() < end and (count is None or len(Handler.received) < count):
            self.cdp.pump(0.1)
        if count is not None:
            self.cdp.pump(0.3)
        return list(Handler.received)

    @property
    def dialogs(self):
        return self.cdp.dialogs

    @property
    def console(self):
        return self.cdp.console

    @property
    def errors(self):
        """Uncaught JavaScript exceptions of the page since the last load."""
        return self.cdp.errors

    def menu(self, key):
        """Call a userscript manager menu command, the way Tampermonkey does."""
        self.cdp.js(f'window.__GM_menu[{json.dumps(key)}]()')
        self.cdp.pump(0.2)

    def traced(self, text):
        return any(text in line for line in self.cdp.console)

    # -- storage
    def gm(self, name):
        raw = self.cdp.js(f'localStorage.getItem({json.dumps("gm:" + name)})')
        return None if raw is None else json.loads(raw)

    def stored_settings(self):
        raw = self.gm('GM_config')
        return {} if raw is None else json.loads(raw)

    # -- settings dialog
    def settings_open(self):
        return bool(self.cdp.js(SETTINGS_OPEN))

    def open_settings(self):
        self.keys('s')
        return self.cdp.wait_for(SETTINGS_OPEN, 5)

    def close_settings(self):
        self.cdp.js("document.getElementById('GM_config_closeBtn').click()")
        self.cdp.pump(0.2)

    def set_field(self, field, value):
        self.cdp.js(f"document.getElementById('GM_config_field_{field}').value = {json.dumps(value)}")

    def save_settings(self):
        """Press Save: the script reloads the page."""
        self.cdp.dialogs.clear()
        self.cdp.console.clear()
        before = self.cdp.loaded
        self.cdp.js("document.getElementById('GM_config_saveBtn').click()")
        self.cdp.wait_load(before)
        self.cdp.pump(0.2)

    # -- local method: the ed2k: links cannot reach a fake client, the clicks are caught
    def catch_anchor_clicks(self):
        self.cdp.js("window.__clicked = []; HTMLAnchorElement.prototype.click = function () "
                    "{ window.__clicked.push(this.getAttribute('href')); }")

    def clicked(self):
        return self.cdp.js('window.__clicked')


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
    return BOOTSTRAP.replace('__SHIM__', json.dumps(shim)).replace('__SCRIPT__', json.dumps(script))


def mask(text):
    """Never show the eMule password, whatever a message may contain."""
    secret = os.environ.get('EMULE_PASSWORD')
    return text.replace(secret, '***') if secret else text


def start_session():
    """Start the web server and headless Chrome, ready for the tests: the script is
    injected into every served page. Shared by this runner and vscode_tests.py.
    Return (server, base_url, chrome, cdp); stop with chrome.close() and server.shutdown()."""
    server, base = start_server()
    chrome = Chrome()
    try:
        cdp = chrome.page()
        for domain in ('Page.enable', 'Runtime.enable'):
            cdp.call(domain)
        cdp.call('Emulation.setFocusEmulationEnabled', {'enabled': True})
        cdp.call('Page.addScriptToEvaluateOnNewDocument', {'source': bootstrap_source()})
    except Exception:
        chrome.close()
        stop_server(server)
        raise
    return server, base, chrome, cdp


def stop_session(server, chrome, cdp):
    """Stop what start_session() started. Return False if the temporary Chrome profile
    could not be deleted: it may hold what the pages stored."""
    cdp.close()
    removed = chrome.close()
    stop_server(server)
    return removed


def main():
    args = sys.argv[1:]
    live = '--live-emule' in args
    selection = next((a for a in args if not a.startswith('--')), '')
    modules = LIVE_MODULES if live else TEST_MODULES
    if live and not os.environ.get('EMULE_PASSWORD'):
        sys.exit('--live-emule needs the eMule web password in the EMULE_PASSWORD environment variable')
    server, base, chrome, cdp = start_session()
    passed = failed = 0
    start = time.time()
    try:
        for module in modules:
            print(f'\n{module.__name__}  ({(module.__doc__ or "").strip().splitlines()[0]})')
            for test in tests_of(module):
                if selection not in test.__name__:
                    continue
                t = T(cdp, base, chrome)
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
        if not stop_session(server, chrome, cdp):
            failed += 1
            print(f'\nERROR: the temporary Chrome profile could not be deleted: {chrome.profile}'
                  '\n       It may hold the settings stored by the tests' +
                  (', eMule password included: delete it by hand.' if live else '.'))

    print(f'\n{passed} passed, {failed} failed  ({time.time() - start:.1f} s)')
    sys.exit(1 if failed else 0)


if __name__ == '__main__':
    main()
