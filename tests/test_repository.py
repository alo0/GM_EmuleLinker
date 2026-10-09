"""Level 0: consistency of the repository files, without the browser (SPECIFICATIONS.md § 3.2).

The version is written by hand in two places only: the @version of GM_EmuleLinker.user.js,
which Tampermonkey reads, and the first entry of CHANGELOG.md, which lists the changes of
every version. These tests make sure that both agree, that the header of the script no
longer holds a list of changes, and that no other file of the repository writes a version
number.

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
CHANGELOG = 'CHANGELOG.md'
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
    """The (version, date) of the entries of CHANGELOG.md ("## [0.11] - 2026-10-09"), latest
    first, as written."""
    return re.findall(r'^## \[(\d+(?:\.\d+)+)\] - (\d{4}-\d{2}-\d{2})\s*$', read(CHANGELOG), re.M)


def test_version_matches_changelog(t):
    """§ 3.2: @version is the version of the latest entry of CHANGELOG.md."""
    entries = changelog()
    t.check(entries, 'CHANGELOG.md entries found')
    if entries:
        t.eq(script_version(), entries[0][0], '@version = version of the first entry of CHANGELOG.md')


def test_changes_listed_in_changelog_md_only(t):
    """§ 3.2: the header of the script no longer lists the changes, it points to CHANGELOG.md:
    a second list would have to be kept in step by hand."""
    old_entries = re.findall(r'^//\s*\d+(?:\.\d+)+ \(\d{4}-\d{2}-\d{2}\)', read(SCRIPT), re.M)
    t.eq(old_entries, [], 'no version entry in the header of the script')
    t.check('CHANGELOG.md' in read(SCRIPT).split('// PARAM')[0], 'the header points to CHANGELOG.md')


def test_changelog_order(t):
    """§ 3.2: CHANGELOG.md goes from the latest version to the oldest, with valid dates."""
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
    """§ 3.2: no other file writes a version number: @version, "Documented version", or a
    screenshot named after a version (historical references such as "0.7 fix" are allowed)."""
    patterns = [r'@version\s+\d', r'Documented version\**\s*\|\s*\d', r'screenshot[\w-]*?-v?\d+\.\d+\.(?:png|jpg)']
    for name in DOCUMENTS:
        text = read(name)
        for pattern in patterns:
            found = re.findall(pattern, text)
            t.eq(found, [], f'{name}: nothing matching {pattern}')


def test_no_dead_code(t):
    """§ 3.6: the code that could not work is gone, its commented-out calls too: silent XHR
    sending (blocked by CORS and mixed content, L-3) and waiting for a child window; the former
    definition of the method field, commented out; leftovers of the settings dialog (a function
    no longer called, the style of the greyed fields, now hidden)."""
    text = read(SCRIPT)
    for name in ('silentPost', 'silentGet', 'loadChildWindow', 'waitReady', 'childWindow', "/*'ed2kDlMethod'",
                 'settingsFieldIds', '.unused'):
        t.check(name not in text, f'{SCRIPT}: no {name}')


def test_settings_fields_keys(t):
    """§ 3.3: no field of the settings dialog declares the same key twice (only the last one
    would count: editCol once had both type 'radio' and type 'int')."""
    text = read(SCRIPT)
    fields = re.findall(r"(?m)^\s*'(\w+)'\s*:\s*\{(.*)\},?\s*(?://.*)?$", text[text.index('GM_config.init(configDiv'):])
    t.check(len(fields) >= 10, 'the fields of the settings dialog found', str(len(fields)))
    for name, body in fields:
        body = re.sub(r"'(?:\\.|[^'\\])*'", "''", body)          # the strings, which may hold : and ,
        body = re.sub(r'\[[^\]]*\]|\{[^}]*\}', '[]', body)        # the nested lists and objects
        keys = re.findall(r'(?:^|,)\s*(\w+)\s*:', body)
        t.eq(sorted(k for k in set(keys) if keys.count(k) > 1), [], f'{name}: each key once')


def test_screenshots(t):
    """§ 3.1: every picture shown by the README or SPECIFICATIONS.md exists, and every picture of
    screenshots/ is shown by one of them (all of them taken by tests/take_screenshots.py)."""
    used = set()
    for name in ('README.md', 'SPECIFICATIONS.md'):
        for path in re.findall(r'!\[[^\]]+\]\(([^)\s]+)\)', read(name)):
            used.add(path)
            t.check(os.path.exists(os.path.join(ROOT, path)), f'{name}: {path} exists')
    folder = os.path.join(ROOT, 'screenshots')
    present = {os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')
               for d, _, files in os.walk(folder) for f in files if f.endswith('.png')}
    t.eq(sorted(present - used), [], 'every picture of screenshots/ shown by a document')
    t.check(any(p.startswith('screenshots/spec/') for p in used), 'SPECIFICATIONS.md shows the pictures of screenshots/spec/')
    script = read('tests/take_screenshots.py')
    t.eq(sorted(p for p in present if os.path.basename(p) not in script), [], 'every picture taken by take_screenshots.py')


def test_repository_address(t):
    """§ 3.2: the address of the repository (links of the settings dialog, SF-8.15) is set in the
    PARAM block, at the top of the script, and is the repository of the update address."""
    text = read(SCRIPT)
    found = re.search(r"(?m)^var REPOSITORY = '([^']+)';", text)
    t.check(found, 'REPOSITORY defined')
    if not found:
        return
    t.check(text.index('PARAM') < found.start() < text.index('\n// \t\t\t\t\t\t\t\tLIB'), 'in the PARAM block')
    owner_repo = re.match(r'https://raw\.githubusercontent\.com/([^/]+/[^/]+)/', meta(SCRIPT, 'updateURL')).group(1)
    t.eq(found.group(1), 'https://github.com/' + owner_repo, 'the repository of @updateURL')


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
