"""Level 0: consistency of the repository files, without the browser (A-12).

The version is written by hand in one place only: the header of GM_EmuleLinker.user.js,
its @version and the first entry of its CHANGELOG. These tests make sure that both
agree, and that no other file of the repository writes a version number.

GM_EmuleLinker.js is the former address of the script, up to 0.9: a copy frozen at 0.10,
whose update URLs point to GM_EmuleLinker.user.js. The installations made before 0.10
update from it once, then follow the new address on their own. These tests check that
this path stays open.
"""
import datetime
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCUMENTS = ['README.md', 'SPECIFICATIONS.md', 'test_sample.html', 'test_many_links.html']
SCRIPT = 'GM_EmuleLinker.user.js'
FORMER = 'GM_EmuleLinker.js'
RAW = 'https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/'


def read(name):
    with open(os.path.join(ROOT, name), encoding='utf-8') as f:
        return f.read()


def meta(name, key):
    """The value of a metadata key (@version, @updateURL...) in the header of a script."""
    found = re.search(r'^// @' + key + r'\s+(.+?)\s*$', read(name), re.M)
    return found.group(1) if found else None


def version_tuple(version):
    return tuple(int(n) for n in version.split('.'))


def script_version():
    return meta(SCRIPT, 'version')


def changelog():
    """The (version, date) of the CHANGELOG entries, latest first, as written."""
    return re.findall(r'^// (\d+(?:\.\d+)+) \((\d{4}-\d{2}-\d{2})\)', read(SCRIPT), re.M)


def test_version_matches_changelog(t):
    """A-12: @version is the version of the latest CHANGELOG entry."""
    entries = changelog()
    t.check(entries, 'CHANGELOG entries found')
    if entries:
        t.eq(script_version(), entries[0][0], '@version = version of the first CHANGELOG entry')


def test_changelog_order(t):
    """A-12: the CHANGELOG goes from the latest version to the oldest, with valid dates."""
    entries = changelog()
    versions = [version_tuple(v) for v, _ in entries]
    t.eq(versions, sorted(versions, reverse=True), 'versions in decreasing order')
    t.eq(len(set(versions)), len(versions), 'no version written twice')
    dates = []
    for version, date in entries:
        try:
            dates.append(datetime.date.fromisoformat(date))
        except ValueError:
            t.check(False, f'valid date for {version}', date)
    t.eq(dates, sorted(dates, reverse=True), 'dates in decreasing order')


def test_no_version_elsewhere(t):
    """A-12: no other file writes a version number: @version, "Documented version", or a
    screenshot named after a version (historical references such as "0.7 fix" are allowed)."""
    patterns = [r'@version\s+\d', r'Documented version\**\s*\|\s*\d', r'screenshot[\w-]*?-v?\d+\.\d+\.(?:png|jpg)']
    for name in DOCUMENTS:
        text = read(name)
        for pattern in patterns:
            found = re.findall(pattern, text)
            t.eq(found, [], f'{name}: nothing matching {pattern}')


def test_update_urls(t):
    """§ 3.2: the script updates itself from its own address on GitHub."""
    for key in ('updateURL', 'downloadURL'):
        t.eq(meta(SCRIPT, key), RAW + SCRIPT, f'{SCRIPT}: @{key}')


def test_former_address(t):
    """§ 3.2: the former address leads the installations made before 0.10 to the new one."""
    t.check(os.path.exists(os.path.join(ROOT, FORMER)), f'{FORMER} kept')
    if not os.path.exists(os.path.join(ROOT, FORMER)):
        return
    # same identity: Tampermonkey updates the installed script instead of adding a second one,
    # and its stored settings are kept
    for key in ('name', 'namespace'):
        t.eq(meta(FORMER, key), meta(SCRIPT, key), f'same @{key}')
    for key in ('updateURL', 'downloadURL'):
        t.eq(meta(FORMER, key), RAW + SCRIPT, f'{FORMER}: @{key} leads to {SCRIPT}')
    former, current = version_tuple(meta(FORMER, 'version')), version_tuple(script_version())
    t.check(former >= (0, 10), f'{FORMER} newer than 0.9, so that the old installations take it', meta(FORMER, 'version'))
    t.check(former <= current, f'{FORMER} not newer than {SCRIPT}')
    if former == current:
        # until 0.10 is published, the frozen copy follows every change of the script
        t.check(read(FORMER).replace('\r\n', '\n') == read(SCRIPT).replace('\r\n', '\n'),
                f'{FORMER} identical to {SCRIPT} while both are {script_version()}')
