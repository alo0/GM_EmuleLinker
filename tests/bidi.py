"""Minimal WebDriver BiDi client, to drive Firefox; Python standard library only.

Firefox no longer speaks the Chrome DevTools protocol, but WebDriver BiDi, the standard protocol
that replaces it. Both send JSON messages {id, method, params} over a WebSocket: the transport of
cdp.py is reused, and this client offers the operations that the tests use on Chrome (cdp.py), so
that the same tests run on both browsers. As there, every JavaScript dialog is accepted and its
message recorded, and the console messages and the uncaught errors of the page are recorded.
"""
import json

from cdp import CDP

# key values of WebDriver for the special keys
KEYS = {'Control': '', 'Alt': '', 'Escape': ''}


class BiDi(CDP):
    def __init__(self, ws_url):
        super().__init__(ws_url)
        self.context = None     # the browsing context (tab) of the page driven by the tests

    def _event(self, msg):
        method, params = msg.get('method'), msg.get('params', {})
        if method == 'browsingContext.userPromptOpened':
            self.dialogs.append(params.get('message', ''))
            self.next_id += 1
            self._send(json.dumps({'id': self.next_id, 'method': 'browsingContext.handleUserPrompt',
                                   'params': {'context': params['context'], 'accept': True}}))
        elif method == 'log.entryAdded' and params.get('type') == 'console':
            self.console.append(params.get('text', ''))
        elif method == 'log.entryAdded' and params.get('type') == 'javascript':
            text = params.get('text', '')
            self.errors.append(text.splitlines()[0] if text else '?')
        elif method == 'browsingContext.load' and params.get('context') == self.context:
            self.loaded += 1

    def js(self, expression):
        """Evaluate an expression in the page and return its value, as JSON, as cdp.py does: the
        expression is evaluated in the global scope of the page (indirect eval), its promise awaited."""
        code = ('(async () => { const v = await (0, eval)(%s);'
                ' return v === undefined ? undefined : JSON.stringify(v); })()' % json.dumps(expression))
        r = self.call('script.evaluate', {'expression': code, 'target': {'context': self.context},
                                          'awaitPromise': True, 'resultOwnership': 'none'})
        if r.get('type') == 'exception':
            raise RuntimeError(r['exceptionDetails'].get('text'))
        value = r['result']
        return json.loads(value['value']) if value.get('type') == 'string' else None

    def _actions(self, source):
        self.call('input.performActions', {'context': self.context, 'actions': [source]})

    def click(self, x, y):
        """A real mouse click at viewport coordinates: a trusted event, like a user's."""
        self._actions({'type': 'pointer', 'id': 'mouse', 'parameters': {'pointerType': 'mouse'}, 'actions': [
            {'type': 'pointerMove', 'x': int(round(x)), 'y': int(round(y))},
            {'type': 'pointerDown', 'button': 0}, {'type': 'pointerUp', 'button': 0}]})

    def _keys(self, values):
        down = [{'type': 'keyDown', 'value': v} for v in values]
        up = [{'type': 'keyUp', 'value': v} for v in reversed(values)]
        self._actions({'type': 'key', 'id': 'keyboard', 'actions': down + up})

    def ctrl_alt(self, letter):
        """A real keyboard shortcut: a trusted event, as if typed by the user."""
        self._keys([KEYS['Control'], KEYS['Alt'], letter.lower()])

    def press(self, key):
        self._keys([KEYS[key]])

    def type_text(self, text):
        for char in text:
            self._keys([char])

    def navigate(self, url):
        self.call('browsingContext.navigate', {'context': self.context, 'url': url, 'wait': 'complete'})

    def reload(self):
        self.call('browsingContext.reload', {'context': self.context, 'wait': 'complete'})

    def set_viewport(self, width, height):
        self.call('browsingContext.setViewport', {'context': self.context, 'viewport': {'width': width, 'height': height},
                                                  'devicePixelRatio': 1})

    def clear_viewport(self):
        self.call('browsingContext.setViewport', {'context': self.context, 'viewport': None, 'devicePixelRatio': None})

    def contexts(self):
        """The top-level browsing contexts (tabs and windows): [(id, url)]."""
        return [(c['context'], c['url']) for c in self.call('browsingContext.getTree', {'maxDepth': 0})['contexts']]
