"""Minimal Chrome DevTools Protocol client, Python standard library only.

Every JavaScript dialog (alert, confirm) is accepted automatically and its
message recorded, so that a page blocked by an alert never blocks a test.
Console calls from the page are recorded too: the userscript traces are the
best evidence of which code path actually ran.
"""
import base64
import json
import os
import socket
import struct
import time


class CDP:
    def __init__(self, ws_url):
        host_port, path = ws_url[len('ws://'):].split('/', 1)
        host, port = host_port.split(':')
        self.sock = socket.create_connection((host, int(port)))
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall((f'GET /{path} HTTP/1.1\r\nHost: {host_port}\r\n'
                           'Upgrade: websocket\r\nConnection: Upgrade\r\n'
                           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n').encode())
        answer = b''
        while b'\r\n\r\n' not in answer:
            answer += self.sock.recv(1)
        if b' 101 ' not in answer.split(b'\r\n')[0]:
            raise ConnectionError(answer.decode(errors='replace'))
        self.next_id = 0
        self.dialogs = []       # messages of the dialogs seen
        self.console = []       # console messages seen
        self.errors = []        # uncaught JavaScript exceptions of the page
        self.loaded = 0         # number of load events seen

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass

    # ---- websocket framing --------------------------------------------------
    def _send(self, text):
        data = text.encode()
        head = bytearray([0x81])                    # FIN + text frame
        n = len(data)
        if n < 126:
            head.append(0x80 | n)
        elif n < 65536:
            head.append(0x80 | 126)
            head += struct.pack('>H', n)
        else:
            head.append(0x80 | 127)
            head += struct.pack('>Q', n)
        mask = os.urandom(4)                        # client frames must be masked
        head += mask
        self.sock.sendall(bytes(head) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

    def _read(self, n):
        buf = b''
        while len(buf) < n:
            chunk = self.sock.recv(n - len(buf))
            if not chunk:
                raise ConnectionError('websocket closed')
            buf += chunk
        return buf

    def _recv(self, timeout):
        self.sock.settimeout(timeout)
        try:
            message = b''
            while True:
                b1, b2 = self._read(2)
                n = b2 & 0x7F
                if n == 126:
                    n = struct.unpack('>H', self._read(2))[0]
                elif n == 127:
                    n = struct.unpack('>Q', self._read(8))[0]
                message += self._read(n)
                if b1 & 0x80:                       # last fragment
                    return json.loads(message)
        except socket.timeout:
            return None

    # ---- protocol -----------------------------------------------------------
    def _event(self, msg):
        method = msg.get('method')
        if method == 'Page.javascriptDialogOpening':
            self.dialogs.append(msg['params']['message'])
            self.next_id += 1
            self._send(json.dumps({'id': self.next_id, 'method': 'Page.handleJavaScriptDialog',
                                   'params': {'accept': True}}))
        elif method == 'Runtime.consoleAPICalled':
            self.console.append(' '.join(str(a.get('value', a.get('description', '')))
                                         for a in msg['params']['args']))
        elif method == 'Runtime.exceptionThrown':
            details = msg['params']['exceptionDetails']
            text = details.get('exception', {}).get('description') or details.get('text', '')
            self.errors.append(text.splitlines()[0] if text else '?')
        elif method == 'Page.loadEventFired':
            self.loaded += 1

    def call(self, method, params=None, timeout=20):
        self.next_id += 1
        my_id = self.next_id
        self._send(json.dumps({'id': my_id, 'method': method, 'params': params or {}}))
        end = time.time() + timeout
        while time.time() < end:
            msg = self._recv(max(0.05, end - time.time()))
            if msg is None:
                continue
            if msg.get('id') == my_id:
                if 'error' in msg:
                    raise RuntimeError(f'{method}: {msg["error"]}')
                return msg.get('result', {})
            self._event(msg)
        raise TimeoutError(method)

    def pump(self, seconds):
        """Process the events (dialogs, console, load) for a while."""
        end = time.time() + seconds
        while time.time() < end:
            msg = self._recv(max(0.05, end - time.time()))
            if msg is not None:
                self._event(msg)

    def js(self, expression):
        """Evaluate an expression in the page and return its value."""
        r = self.call('Runtime.evaluate', {'expression': expression, 'returnByValue': True,
                                           'awaitPromise': True})
        if 'exceptionDetails' in r:
            details = r['exceptionDetails']
            raise RuntimeError(details.get('exception', {}).get('description') or details.get('text'))
        return r['result'].get('value')

    def wait_for(self, expression, timeout=10):
        """Wait until a JS expression is truthy, processing the events meanwhile."""
        end = time.time() + timeout
        while time.time() < end:
            if self.js(expression):
                return True
            self.pump(0.1)
        return False

    def wait_load(self, before, timeout=20):
        """Wait for a load event after the count `before`."""
        end = time.time() + timeout
        while self.loaded == before and time.time() < end:
            self.pump(0.1)
        if self.loaded == before:
            raise TimeoutError('page load')

    def click(self, x, y):
        """A real mouse click at viewport coordinates: a trusted event, like a user's."""
        base = {'x': x, 'y': y, 'button': 'left', 'clickCount': 1}
        self.call('Input.dispatchMouseEvent', dict(base, type='mousePressed'))
        self.call('Input.dispatchMouseEvent', dict(base, type='mouseReleased'))

    def ctrl_alt(self, letter):
        """A real keyboard shortcut: a trusted event, as if typed by the user."""
        base = {'modifiers': 3, 'windowsVirtualKeyCode': ord(letter.upper()),
                'key': letter.lower(), 'code': 'Key' + letter.upper()}   # 3 = Alt + Ctrl
        self.call('Input.dispatchKeyEvent', dict(base, type='rawKeyDown'))
        self.call('Input.dispatchKeyEvent', dict(base, type='keyUp'))
