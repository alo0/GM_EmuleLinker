"""Bridge between the test suite and the Testing panel of VS Code (Python unittest).

VS Code discovers unittest test cases: this module turns each test function of the suite
into a test method, one class per level (Repository, Units, Scenarios, Sending). As with
run_tests.py, a single web server and a single headless browser serve the whole run: Chrome,
or Firefox when the environment variable TEST_BROWSER is "firefox". Standard library only.
The live tests are left out on purpose: run them with "python tests/run_tests.py --live-emule"
or "--live-amule".

The workspace settings point VS Code to this file:
    "python.testing.unittestArgs": ["-v", "-s", "./tests", "-p", "vscode_tests.py"]
"""
import os
import sys
import unittest

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run_tests as rt              # noqa: E402

session = {}


def setUpModule():
    browser_class = rt.BROWSERS['--' + os.environ.get('TEST_BROWSER', 'chrome').lower()]
    session['server'], session['base'], session['browser'], session['driver'] = rt.start_session(browser_class)


def tearDownModule():
    if not rt.stop_session(session['server'], session['browser'], session['driver']):
        raise RuntimeError(f'the temporary browser profile could not be deleted: {session["browser"].profile}')


def as_test_method(test):
    """Wrap a test function of the suite: it fails with the list of its failed checks."""
    def method(self):
        t = rt.T(session['driver'], session['base'], session['browser'])
        test(t)
        failed = [rt.mask(label + (f': {detail}' if detail else '')) for ok, label, detail in t.checks if not ok]
        if failed:
            self.fail(f'{len(failed)} of {len(t.checks)} checks failed:\n- ' + '\n- '.join(failed))
    method.__name__ = test.__name__
    method.__doc__ = test.__doc__
    return method


# one TestCase class per level: test_units -> Units, test_scenarios -> Scenarios...
for module in rt.TEST_MODULES:
    name = module.__name__.replace('test_', '').title()
    globals()[name] = type(name, (unittest.TestCase,), {
        '__doc__': module.__doc__,
        **{test.__name__: as_test_method(test) for test in rt.tests_of(module)},
    })
