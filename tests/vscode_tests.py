"""Bridge between the test suite and the Testing panel of VS Code (Python unittest).

VS Code discovers unittest test cases: this module turns each test function of the suite
into a test method, one class per level (Repository, Units, Scenarios, Sending). As with
run_tests.py, a single web server and a single headless Chrome serve the whole run.
Standard library only. The live test against the real eMule is left out on purpose: run
it with "python tests/run_tests.py --live-emule".

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
    session['server'], session['base'], session['chrome'], session['cdp'] = rt.start_session()


def tearDownModule():
    if not rt.stop_session(session['server'], session['chrome'], session['cdp']):
        raise RuntimeError(f'the temporary Chrome profile could not be deleted: {session["chrome"].profile}')


def as_test_method(test):
    """Wrap a test function of the suite: it fails with the list of its failed checks."""
    def method(self):
        t = rt.T(session['cdp'], session['base'], session['chrome'])
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
