<!-- markdownlint-disable-file MD024 -->
<!-- Keep a Changelog repeats the same headings (Added, Changed...) in every version -->

# Changelog

All notable changes to GM_EmuleLinker are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The version is written in this file and in the `@version` line of [GM_EmuleLinker.user.js](GM_EmuleLinker.user.js) only: the automated tests check that both agree.

Up to 0.7, the script was published on userscripts.org (script 154608). It moved to GitHub in 2014.

## [0.11] - 2026-10-11

### Added

- New download method **aMule 3.x (amuleapi)**, for aMule 3.1 and later, through its REST API: all the links in a single request, the password never in a URL, no window opened, no length limit. At the first sending, Tampermonkey asks to allow the address of aMule.
- The answer of aMule is shown in the popup: links added, links refused, wrong password, aMule unreachable or answering too late. With the popup closed, an error is shown in an alert.
- While aMule answers, the popup shows an animated "Please wait" and the **Add all links** buttons are disabled: the links can not be sent twice. The time limit grows with the number of links.
- Settings dialog: several servers, each one with its own name, download method and settings, several of the same method included (two aMule 3.x for instance): a radio button chooses the one that receives the links, + Add a server, Edit, and Delete with Undo; under a server, only the fields of its method are shown; the password is masked, with a Show button; the values are checked before saving, each wrong value shown in red under its field instead of an alert, the Server URL included: it must start with `http://` or `https://`, for every method (Custom too); the page is dimmed behind the dialog, and Escape closes it; Reset to defaults (every server included) highlights what it changed, says that nothing is saved yet, and can be undone.
- Settings dialog, aMule 3.x: a **Test** button checks the Server URL and the password before saving them (version of aMule and its ed2k and Kad connections, or what goes wrong), and an **Import** button fills the Category field with the categories of aMule, in its order, the default one kept, with Undo.
- This CHANGELOG.md file.
- SPECIFICATIONS.md: pictures of the popup and of the settings dialog, their parts numbered, and of its states (helps, errors, deleted server, reset, Test and Import), taken by `tests/take_screenshots.py` with the README ones.
- Tests: a fake aMule 3.1 REST API in the test server, `GM_xmlhttpRequest` relayed by the test server as Tampermonkey does, and a live test against a real aMule 3.1 (`--live-amule`).
- Tests: the whole suite also runs in Firefox (`--firefox`, or `--chrome --firefox` for both), the live tests included, through WebDriver BiDi; one manual check less before a release.

### Changed

- The download methods are renamed and reordered in the settings: Local (your system default), eMule (web), aMule 3.x (amuleapi), aMule 2.x (amuleweb), MLDonkey (web), Custom (post to your own server). The method already chosen is kept.
- The names eMule, aMule and MLDonkey are written this way in the settings dialog and the documentation.
- The Custom method is no longer experimental.
- Settings dialog redesigned: steel blue border and section titles (the popup border too), half of the window wide (between 640 and 960 px), a height that fits its content, links to report a problem and to the repository at its bottom, aligned fields sized to their content (the long ones as wide as the dialog allows), the explanations of the fields shown under them by a Show help button (or as a tooltip while hidden), rewritten explanations, and the version in its title. The fields "eMule Url" and "eMule Password" are named "Server URL" and "Password", as every client uses them.
- The changes are listed in this file instead of the header of the script.
- `test_sample.html`: an Expected column (Sent or Ignored), the invalid links unnumbered and on a red background, the malformed link placed first to check that the detection goes on after it. `test_many_links.html`: 500 links by default (`?n=` to change).
- Documentation: compatibility table covering every download method; Violentmonkey stated as supported (tested on Chrome); Greasemonkey 4 stated as not supported; SPECIFICATIONS.md reorganized (compatibility before the limitations, the chapter of the defects fixed in 0.10 removed).

### Removed

- Dead code that could not work: `silentPost()` and `silentGet()` (silent sending, blocked by the browsers), `loadChildWindow()` and `waitReady()`, and the commented-out code that used them.

### Fixed

- Settings dialog: in a window too low for it, or made lower once it is open, its bottom and its Save button were out of reach. It is now anchored at the top of the window and scrolls inside.
- Resizing the window raised a JavaScript error, in the settings dialog library (GM_config).

## [0.10] - 2026-10-09

### Added

- Menu entry **Toggle debug traces**. The debug traces are off by default.
- An automated test suite (`tests/`), run in a real headless Chrome with the Python standard library: repository consistency, function tests, page scenarios, and sending checked by fake eMule, aMule, MLDonkey and custom web interfaces. Also shown in the VS Code Testing panel.
- An optional live test against the real eMule (`--live-emule`): test files added, found, then cancelled.
- `tests/check_publication.py`: checks that nothing personal (e-mail address, password, private term) is about to be published.
- SPECIFICATIONS.md: functional and technical specification, with the steps to publish a version.
- `test_many_links.html`, to check by hand that the popup shows many links.

### Changed

- The script file is renamed `GM_EmuleLinker.user.js`, for a one-click installation. Existing installations move to it on their own: `GM_EmuleLinker.js` stays as a copy frozen at 0.10, whose update URLs point to the new file.
- Links that are not files (`server`, `serverlist`) are ignored.
- Categories: invalid entries are skipped and exactly one default is kept, so that the category displayed is the one sent.
- Settings corrected automatically are stored, so that their alert is no longer shown on every page.
- With many links, only the list scrolls in the popup: both toolbars always stay visible.
- README rewritten: installation from the `.user.js` file, usage and keyboard shortcuts, compatibility table, limitations, tests, license.
- `test_sample.html`: valid 32-character ed2k hashes, new encoding and malformed link cases, descriptions in English.

### Removed

- The `MaxLength` setting of the edit box: the list was never truncated, it only blocked typing.

### Fixed

- A malformed ed2k link no longer stops the detection of the other links of the page.
- ed2k links whose scheme is URL-encoded (`ed2k%3A%2F%2F…`) are detected.
- Links can be sent with the popup closed (keyboard shortcut or menu).
- The local method works again on recent Chrome (links are URL-encoded) and sends every selected link. Known limit: on Chrome, it sends one link per user action; to send many links at once, use the web server of eMule.
- An empty or invalid Category setting no longer stops the script on every page.
- The eMule password is optional, as in eMule: no more alert and settings dialog on every page without it.
- The popup can no longer be opened twice, and a popup closed on a page stays closed on the next ones.
- The **Open Popup** menu entry works, and the shortcuts no longer fail on pages without ed2k links.
- Changing the category no longer resets the popup (checkboxes, edit box text, size).
- Custom method: clicking a file name sends it, instead of opening a copy of the page.

## [0.9] - 2025-10-29

### Added

- Password support for the aMule method.
- File size shown in normal mode.
- Check of file names encoded twice.

### Changed

- Better style of the popup.
- Default settings adapted to bigger screen resolutions.
- Code refactoring and cleaning.

### Fixed

- The newline between links is encoded: some ed2k links needed it.

## [0.8] - 2018-11-11

### Changed

- The Custom method sends the links with a POST request, and its URL no longer has to end with a `/`.

### Fixed

- The URL decoding method is detected: `decodeURIComponent()` first, then `unescape()`.

## [0.7] - 2013-01-27

### Added

- Support of the local application handling ed2k links.
- Checkboxes to choose the links to send.
- Category selector.
- Duplicate links check.
- Suffix added to identical file names with different links.
- Keyboard shortcuts (`Ctrl+Alt+` M, A, C, O, S, X).

### Changed

- The GM_config library is integrated into the script, for quick fixes inside it.

### Fixed

- The style of the links was applied to the whole page.

## [0.6] - 2013-01-17

### Added

- aMule support.
- MLDonkey support.
- Focus given back to the main window.

### Changed

- Better switch between edit mode and normal mode.

### Fixed

- Character encoding.

## [0.5] - 2013-01-04

### Added

- Edit mode.

### Changed

- Height and width settings.

### Fixed

- Display of character encoding.

## [0.4] - 2012-12-21

### Added

- Settings dialog.

## [0.3] - 2012-12-20

### Changed

- Script renamed and published on userscripts.org.

## [0.2] - 2012-11-20

### Fixed

- The `|` character escaped as `%7C`.

## [0.1] - 2012-11-18

### Added

- First version.

[0.11]: https://github.com/alo0/GM_EmuleLinker/compare/v0.10...v0.11
[0.10]: https://github.com/alo0/GM_EmuleLinker/compare/v0.9...v0.10
[0.9]: https://github.com/alo0/GM_EmuleLinker/releases/tag/v0.9
