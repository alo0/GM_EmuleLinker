#!/usr/bin/env python3
"""Check by hand, in a real Tampermonkey, that the installations made before 0.10 move on
their own from the former address of the script (GM_EmuleLinker.js) to the new one
(GM_EmuleLinker.user.js) — § 8.3 of SPECIFICATIONS.md.

    python tests/migration_check.py [--port 8765]

A local web server stands for GitHub: every raw.githubusercontent.com address of the
scripts is replaced by its own. It serves
  /install/GM_EmuleLinker.user.js   the 0.9 of the git tag v0.9, to install first
  /GM_EmuleLinker.js                the former address, from the working copy
  /GM_EmuleLinker.user.js           the new address, from the working copy, with a
                                    simulated next version (0.10 -> 0.10.1)
  /test_sample.html                 the test page
and prints every request, so that the path followed by Tampermonkey can be seen.
Tampermonkey cannot be driven by the automated suite: the steps are done by hand.
Python standard library only.
"""
import argparse
import http.server
import os
import re
import subprocess
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RAW = 'https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/'

STEPS = """
Use a browser profile with Tampermonkey but WITHOUT your real Emule Linker: the test
script has the same name, it would replace yours and point its updates to this server.

1. Open {base}install/GM_EmuleLinker.user.js and install the 0.9.
2. Open {base}test_sample.html, set a few settings (category, URL...), save.
3. Tampermonkey dashboard: check for updates of Emule Linker (or "Check for userscript
   updates" in the extension menu). Expected: GET /GM_EmuleLinker.js below,
   Emule Linker becomes 0.10.
4. Check for updates again. Expected: GET /GM_EmuleLinker.user.js below,
   Emule Linker becomes {next}: the installation follows the new address.
5. Open {base}test_sample.html again: the settings of step 2 are still there.
6. Delete the test script from Tampermonkey: it now updates from this server.

Ctrl+C to stop the server.
"""


def git_show(path):
    return subprocess.check_output(['git', '-C', ROOT, 'show', path]).decode('utf-8')


def read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


def bump(script):
    """The script with a simulated next version, to see the update after the migration."""
    return re.sub(r'^(// @version\s+)(\S+)', lambda m: m.group(1) + m.group(2) + '.1', script, count=1, flags=re.M)


def version(script):
    return re.search(r'^// @version\s+(\S+)', script, re.M).group(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--port', type=int, default=8765)
    port = parser.parse_args().port
    base = f'http://127.0.0.1:{port}/'

    def local(script):
        return script.replace(RAW, base)

    new = local(bump(read('GM_EmuleLinker.user.js')))
    pages = {
        '/install/GM_EmuleLinker.user.js': ('0.9, to install', local(git_show('v0.9:GM_EmuleLinker.js'))),
        '/GM_EmuleLinker.js': ('former address', local(read('GM_EmuleLinker.js'))),
        '/GM_EmuleLinker.user.js': ('new address', new),
        '/test_sample.html': ('test page', read('test_sample.html')),
    }

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?')[0]
            if path not in pages:
                self.send_error(404)
                print(f'{time.strftime("%H:%M:%S")}  GET {self.path}  -> 404', flush=True)
                return
            label, text = pages[path]
            body = text.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8' if path.endswith('.html')
                             else 'text/javascript; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)
            served = '' if path.endswith('.html') else f', version {version(text)}'
            print(f'{time.strftime("%H:%M:%S")}  GET {self.path}  -> {label}{served}', flush=True)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), Handler)
    print(STEPS.format(base=base, next=version(new)))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
