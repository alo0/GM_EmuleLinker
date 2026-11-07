<!-- markdownlint-disable-file MD024 -->
<!-- Keep a Changelog repeats the same headings (Added, Changed...) in every version -->

# Changelog

All notable changes to GM_EmuleLinker are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). The version is written in this file and in the `@version` line of [GM_EmuleLinker.user.js](GM_EmuleLinker.user.js) only: the automated tests check that both agree.

Up to 0.7, the script was published on userscripts.org (script 154608). It moved to GitHub in 2014.

## [0.14] - 2026-11-07

### Added

- Popup: a **server list** in both toolbars, before the category list, to send the links of the page to another server without opening the settings: Local, then the servers of the settings, in their order. It is shown when it offers two choices at least, Local included. The server chosen applies to the current page only, with its own settings, and the category list offers its categories.
- Popup: a **Help** button (?), `Ctrl+Alt+H` and the menu entry "Help" show a short help built into the script: each control of the toolbars with its shortcut, the list of the links, the next pages, and links to the documentation and to the issues on GitHub. It opens beside the popup, which stays usable, and can be moved by its title bar.
- **French** (I-7): the popup, its messages, the help, the settings dialog, the alerts and the menu, in English or in French. The setting **Language**, first in the General section, follows the language of the browser by default.
- Popup: the **minimized view**, only the top toolbar, at the same width, the checked links and the edit box kept; the Minimize (▲) and Maximize (▼) button; `Ctrl+Alt+X` and the menu entry "Switch view" go from maximized to minimized, then closed, then maximized again.
- Popup: a **counter** in both toolbars, the links that Download sends out of the links of the page (in edit mode, the links of the text).
- Popup: closing it (✕, `Ctrl+Alt+C` or the menu) shows a **message** inside the page, telling how to open it again, and how to keep it closed on every page (the default view Closed, or the script restricted to some sites, with a link to the installation guide); **Don't display again** hides it for good.
- Popup: `Ctrl+Alt+A` and the menu entry "Check or uncheck all links" check or uncheck every link, as the box of the toolbars.
- Popup: a light shadow on the top or bottom edge of the list tells that links are hidden beyond it, whatever the scrollbar (Firefox shows it only under the mouse).
- Settings dialog: the new **General** section, first, with the **Default popup view**: Maximized (default), Minimized or Closed, the view in which each page with ed2k links opens the popup. Its help tells that, with Closed, the popup and the settings dialog open only through the keyboard shortcuts or the menu of Tampermonkey or Violentmonkey.
- Settings dialog, Popup section: **Popup position**, the corner of the window where the popup is shown (top left by default, top right, bottom left, bottom right), and **Popup scrolling**, Stays in view (default) or Scrolls with the page, in place of Popup Position; at the bottom of the window, the popup always stays in view. The former setting is taken over: absolute is Scrolls with the page, fixed is Stays in view.
- Settings dialog: **Disable**, on the row of Local, leaves Local out of the servers that receive the links, for a system without an ed2k application (I-14); **Enable** offers it again. Not while Local is checked; deleting the last server enables it again.
- Settings dialog, Popup section: **Show the server list**, checked by default; unchecked, the toolbars have no server list.
- Settings dialog, Popup section: **Show the category list**, checked by default; unchecked, the toolbars have no category list, and the links are sent to the default category.
- Settings dialog, General section: **Show a message when the popup is closed**, checked by default, to show the message again after "Don't display again".
- Settings dialog: a Close icon (✕) at the right of the title.

### Changed

- Popup: new toolbars. At the top: the box, the counter, the server and the category, **Download**, then Settings (⚙), Help (?), Minimize (▲) and Close (✕) as icons, drawn so that they are centered whatever the fonts; at the bottom: the box, the counter, Edit mode, the server, the category and Download. Each tooltip tells the shortcut.
- Popup: **Add all links** is renamed **Download**, and its shortcut is now `Ctrl+Alt+D` (`Ctrl+Alt+A` up to 0.13, now checking or unchecking every link). Download stands out: white, with a blue border.
- Popup: closing it, or switching it to edit mode, applies to the current page only: the next page opens it in the default view of the settings, where a closed popup used to stay closed on every page. To keep it closed everywhere, choose Closed as the default view.
- Popup: the answer of eMule, aMule or MLDonkey is shown in a colored band over the top of the list, the popup keeping its size; a success goes away after 8 s, an error stays until closed. Links left out by aMule 3.x or MLDonkey (invalid, or already in the list) are a warning, in orange, no longer an error in red: the client received the links. With the popup closed, the band is shown in the corner of the popup, instead of an alert, a success included.
- Popup: larger and evenly spaced toolbars (22 px buttons and lists, 12 px text, 13 px checkboxes), on a light blue background, and 17 px rows. The popup sets these sizes itself: the styles of a page (a forum giving its buttons a large padding, or its text a small line height) no longer change them.
- Popup: the buttons and lists of the toolbars are white, whatever the page and the browser.
- Popup: the checkboxes in one column, the file names aligned on the counters, the sizes aligned to the right, on the right edge of the toolbars.
- Popup: the list is framed by two lines that no longer scroll with it, from one side of the popup to the other.
- Popup: the category list is grayed out when there is only one category, between 100 and 140 px wide (`categoryListMinWidth`, `categoryListMaxWidth`, in the PARAM block): the short categories of another server move nothing, a long name is cut, and shown whole in the tooltip.
- Popup: it can be resized at the top left of the window only; at the bottom, Minimize is ▼ and Maximize ▲, as the popup folds down.
- Settings dialog: its title on the light blue of the toolbars of the popup; the button of the inline help is an icon (?), pressed while the helps are shown; Save stands out, as Download.
- Alerts of the settings stored by an older version (no valid category, popup too small): reworded.
- Menu of Tampermonkey: the access key of "Toggle debug traces" is now `t` (`d` is the one of Download).
- Security: the servers of the settings are read only on a page with ed2k links, and the settings of a server other than the checked one (its password included) only when it is chosen in the popup.
- Documentation (`SPECIFICATIONS.md`, chapter 6): I-1, done in 0.13, removed; the help (I-5) will be built into the script, as GitHub refuses to be shown in an inline frame.
- Code: the script is reorganized, without any change of behavior: the CSS of the popup and of the settings dialog, and the icons, are in the PARAM block, with the default values, for the themes to come; the CODE block is in titled parts (state, startup, detection, popup, selection, sending, settings), the utilities last; an index at the top of the script gives this order.
- Code: every text shown to the user is in the PARAM block, one table per language, read by `tr()`.
- Tests: the state of the popup when a page is loaded is set by the default view of the settings, or by `Ctrl+Alt+M`, as it is no longer stored.
- Tests: the toolbars (controls, sizes on a page with the styles of a forum, alignments, icons, counter, views, lines and shadows of the list, category lists); the sending tests use `Ctrl+Alt+D`.
- Tests: the layout of the script (the look in the PARAM block, the parts of the CODE block in the order of the index).
- Tests: the server list (shown, order, place, width, the server chosen and its categories, the sending to it, nothing stored, its setting); servers stored for a test (`load(servers=…)`).
- Tests: the message shown when the popup is closed (the ways of closing, centered on a backdrop, OK, its Close button, Escape, Don't display again, its setting); the fake `GM_info` gives the name of the userscript manager.
- Tests: the help (its button, its content, its place, moved with the mouse: a new `drag` of the test tools, with Chrome and Firefox); the header of the settings dialog and Save; Local disabled; the corner and the scrolling of the popup, their migration, the arrows at the bottom.
- Tests: the languages (the setting, the French texts, the language chosen, the tables complete); the test tools give the script the language of the browser that a test asks for, English by default.
- Tests: the band of the answers in every view, and the popup closed; the colors of the controls on a page that gives its own.

### Fixed

- Settings dialog: **Reset to defaults** sets a checkbox back to its default value, and highlights it.

## [0.13] - 2026-11-04

### Added

- Settings dialog, Popup section: the new field **Links checked by default**, a regular expression on the file name. The links whose name matches it are checked in the popup, the others are listed in gray, unchecked, and are not sent with the popup closed. It gives a block list, `/^(?!.*\.emulecollection$)/i` (every file but the eMule collections), or an allow list, `/\.(cbz|cbr|rar|zip)$/i` (only these files); `/i` ignores the case. An expression that cannot be read is refused by Save.
- Popup: the box of the bottom toolbar checks or unchecks every link, as the top one; both are shown mixed when only some links are checked, and follow the boxes of the links.
- Settings dialog: the code in the helps (addresses, values, regular expressions) is in a fixed-width font.
- Documentation (`SPECIFICATIONS.md`, section 7.4): the entry of the version in `CHANGELOG.md` is reordered before the push, and a summary of the release is proposed after it.

### Changed

- Documentation (`SPECIFICATIONS.md`, chapter 6): the identified improvements are renumbered, each with its target version, and detailed (views of the popup, message when it is closed, general section of the settings, online help, server chosen from the popup...).
- Test page `test_sample.html`: the links 1 and 9 are now a `.cbz` file and an eMule collection, to try the filter of the links checked by default.
- Tests: every HTTP request of the test tools has a time limit, the requests to the DevTools of Chrome included: a browser that no longer answers stops the run with an error.

### Fixed

- Popup: the tab order of the boxes of the links is 1, 2, 3... instead of 1, 11, 21... (the index and 1 were joined as text); the order of the boxes was already right.

## [0.12] - 2026-10-14

### Added

- Settings dialog, eMule: the **Test** button checks the Server URL and the password before saving them, and gives the version of eMule; the **Import** button fills the Category field with the categories of eMule, in its order, the default one kept, with Undo.
- Settings dialog, aMule 2.x: the **Test** button (with the version of aMule, read in its log) and the **Import** button (its categories, by name).
- Settings dialog, MLDonkey: a **User** field (`admin` by default) and the Password, and the **Test** button.
- Tests: live tests against a real aMule 2.x (`--live-amuleweb`, `AMULEWEB_URL`) and a real MLDonkey (`--live-mldonkey`, `MLDONKEY_URL`).
- `.editorconfig`: the indentation of the files (tabs in the JavaScript, spaces in the other files), checked by the tests.

### Changed

- **eMule (web)**: the links are sent without opening any window, and the answer of eMule is shown in the popup: links added, password refused, eMule unreachable or answering too late. While eMule answers, the popup shows "Please wait" and the **Add all links** buttons are disabled. Nothing is left in the browser history. At the first sending, Tampermonkey asks to allow the address of eMule.
- **aMule 2.x (amuleweb)**: the links are sent without opening any window, and without the fixed wait of 1 second: the login is awaited, then the links are sent in the same session, and looked for in the downloads of aMule, the result shown in the popup (in orange when they are not all found, or when the downloads cannot be read). The category name is now encoded in the request, a name with accents as aMule 2.3.3 reads it: sent otherwise, aMule recognizes no category and drops the links without any message.
- **MLDonkey (web)**: the links are sent without opening any window, with the user and the password of the settings: they are no longer typed in the dialog of the browser at each sending. The answer of MLDonkey is shown in the popup (links added, refused, user or password refused). Only the Custom method still opens a tab, to post its form.
- Tests: a fake eMule that answers as eMule 0.70b does, and the live test checks the answer shown and the Test button.
- Code: one indentation in the whole script, tabs (the embedded GM_config library keeps its own spaces).

### Removed

- Dead code: `sleep()` and `refreshLinkUrls()`, no longer needed once eMule and aMule 2.x are sent without a window.

### Fixed

- Settings dialog and popup: on a page that centers its text, as some forums do, the explanations of the fields, the names and addresses of the servers and the file names of the popup were centered too. The text styles of the page (alignment, line height, letter spacing, capitals, indent, italics) no longer reach them.
- eMule (web): a password holding `&`, `#` or `+` was cut or changed in the request, and refused by eMule: it is now encoded, the category too.
- aMule 2.x: a category whose name holds an equals sign (`=`) or a semicolon (`;`), such as `A=B` or `test;23`, could not be written in the Category field, and once imported it matched no category of aMule, which dropped the links. The value of a category is now everything after its first `=`, a `;` is written `\;` (`A B=A=B`, `test 23=test\;23`), and Import writes them so.

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

[0.14]: https://github.com/alo0/GM_EmuleLinker/compare/v0.13...v0.14
[0.13]: https://github.com/alo0/GM_EmuleLinker/compare/v0.12...v0.13
[0.12]: https://github.com/alo0/GM_EmuleLinker/compare/v0.11...v0.12
[0.11]: https://github.com/alo0/GM_EmuleLinker/compare/v0.10...v0.11
[0.10]: https://github.com/alo0/GM_EmuleLinker/compare/v0.9...v0.10
[0.9]: https://github.com/alo0/GM_EmuleLinker/releases/tag/v0.9
