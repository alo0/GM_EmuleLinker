# GM_EmuleLinker — Functional and Technical Specifications

| | |
|---|---|
| **Product** | Emule Linker (Greasemonkey / Tampermonkey userscript) |
| **Documented version** | The one written in `GM_EmuleLinker.user.js`: its `@version` and the first entry of its CHANGELOG, the only places where the version is written (A-12) |
| **Source file** | `GM_EmuleLinker.user.js` (single file, ~2150 lines) |
| **License** | GNU GPL v3 (`LICENSE`) — the embedded GM_config library remains under LGPL |
| **Repository** | <https://github.com/alo0/GM_EmuleLinker> |
| **Document** | Reverse specification, written by analyzing the code and the workspace files |

## Table of contents <!-- omit from toc -->

- [1. Overview](#1-overview)
  - [1.1 Purpose](#11-purpose)
  - [1.2 How it works](#12-how-it-works)
  - [1.3 Actors and environment](#13-actors-and-environment)
  - [1.4 Scope](#14-scope)
- [2. Functional specifications](#2-functional-specifications)
  - [SF-1 — ED2K link detection](#sf-1--ed2k-link-detection)
  - [SF-2 — Display popup](#sf-2--display-popup)
  - [SF-3 — Normal mode (list)](#sf-3--normal-mode-list)
  - [SF-4 — Edit mode](#sf-4--edit-mode)
  - [SF-5 — Selection](#sf-5--selection)
  - [SF-6 — Categories](#sf-6--categories)
  - [SF-7 — Sending the links](#sf-7--sending-the-links)
  - [SF-8 — Configuration](#sf-8--configuration)
  - [SF-9 — Commands and keyboard shortcuts](#sf-9--commands-and-keyboard-shortcuts)
  - [SF-10 — Persistence of the display state](#sf-10--persistence-of-the-display-state)
- [3. Technical specifications](#3-technical-specifications)
  - [3.1 File layout](#31-file-layout)
  - [3.2 Userscript metadata](#32-userscript-metadata)
  - [3.3 Embedded library: GM\_config](#33-embedded-library-gm_config)
  - [3.4 Data model](#34-data-model)
  - [3.5 Execution sequence](#35-execution-sequence)
  - [3.6 Function inventory](#36-function-inventory)
  - [3.7 Key technical choices](#37-key-technical-choices)
- [4. Constraints, limitations and security](#4-constraints-limitations-and-security)
- [5. Known defects and technical debt](#5-known-defects-and-technical-debt)
- [6. Compatibility](#6-compatibility)
- [7. Identified improvements](#7-identified-improvements)
- [8. Tests](#8-tests)
  - [8.1 Test page](#81-test-page)
  - [8.2 Automated test suite](#82-automated-test-suite)
  - [8.3 Manual checks before a release](#83-manual-checks-before-a-release)
  - [8.4 Publishing a version](#84-publishing-a-version)

---

## 1. Overview

### 1.1 Purpose

Emule Linker is a userscript that **detects every ED2K link in a web page** and lets the user **send them in one click** to a file-sharing client: eMule, aMule, MLDonkey (through their web interface, local or remote), the system's default application, or a custom web server.

Without this script, the user has to click each ED2K link one by one — which quickly becomes tedious on forum pages holding dozens of links (historical use case: comic book sharing forums).

### 1.2 How it works

```text
Web page                 Userscript                        ed2k client
┌──────────┐            ┌────────────────────┐            ┌─────────────┐
│ <a href= │  DOM scan  │ 1. getEd2kLinks()  │            │ eMule       │
│  ed2k:// │ ─────────► │ 2. createPopup()   │            │ aMule       │
│  ...     │  (XPath)   │ 3. user selection  │ ─────────► │ MLDonkey    │
│ <a href= │            │ 4. getAddLink()    │  GET/POST  │ local app   │
│  ed2k:// │            │ 5. addButton()     │  / ed2k:   │ custom srv  │
└──────────┘            └────────────────────┘            └─────────────┘
```

### 1.3 Actors and environment

| Actor / component | Role |
|---|---|
| **User** | Browses, selects the links, triggers the sending, configures the script |
| **Browser + userscript manager** | Firefox or Chrome + **Tampermonkey** (recommended); Greasemonkey (historical origin); Violentmonkey not tested |
| **Host page** | Any page (`@include *`) containing `<a href="ed2k://...">` links |
| **ed2k client** | eMule / aMule / MLDonkey with the web interface enabled, or a local `ed2k:` protocol handler, or a custom HTTP endpoint |

### 1.4 Scope

**Included**: detection, deduplication, display, selection, manual editing, categorization, sending, persistent configuration, keyboard shortcuts.

**Excluded**: automatic update from the UI, multiple languages, extension filtering, status feedback from the ed2k client (no acknowledgment is read), queue management.

---

## 2. Functional specifications

### SF-1 — ED2K link detection

| Ref | Rule |
|---|---|
| SF-1.1 | When each page loads, the script goes through **every `<a>` element with a `href` attribute**, using the XPath query `//a[@href]`. |
| SF-1.2 | The test is made on the **raw `href` attribute** (`getAttribute`), trimmed of surrounding spaces, and not on the resolved `href` property: when the scheme itself is encoded, the browser recognizes no scheme, resolves the attribute as a relative URL, and the `ed2k` prefix disappears. |
| SF-1.3 | A link is kept when its `href` starts with `ed2k` followed by the scheme separator, **literal or encoded at any depth**: `ed2k:`, `ed2k%3A`, `ed2k%253A`… The comparison is case-insensitive. |
| SF-1.4 | The `href` is **decoded** in successive passes: `decodeURIComponent()` first, falling back to `unescape()` when an exception is raised (invalid UTF-8 sequences, legacy ISO-Latin encoding). A first pass is always made; further passes are made as long as the scheme is not readable and decoding still changes something, up to 4 passes. |
| SF-1.5 | **Links identical after decoding** are ignored: only one copy is kept. Two links written with different encodings but pointing to the same file are therefore correctly deduplicated. |
| SF-1.6 | The link is split on the `\|` separator to extract the **file name** (field 3) and the **size in bytes** (field 4). |
| SF-1.7 | The link is **structurally validated** before use: at least 5 fields, type `file`, non-empty name, purely numeric size. Any non-compliant link — malformed (`ed2k://xxxx`) or of another type (`\|server\|`, `\|serverlist\|`) — is **silently ignored**, with a console trace. A bad link therefore cannot interrupt the scan of the page. |
| SF-1.8 | If the file name still contains a `%XX` pattern, it is **decoded a second time** (names encoded twice by the source site) and the link is rebuilt. |
| SF-1.9 | If an identical file name has already been met (but with a different link), a **` (n)` suffix** is added, `n` being the index of the link. <!-- markdownlint-disable-line MD038 --> |
| SF-1.10 | The three arrays are filled only **after** validation and fixes, `eLinks` last: its length is authoritative, and no partial entry can be used. |
| SF-1.11 | An unexpected failure of the scan is **contained**: the keyboard shortcuts and the settings dialog keep working, only the popup is not displayed. |
| SF-1.12 | The popup is displayed **only if at least one link** has been found. On a page without ed2k links, no shortcut and no menu entry opens it, and none of them raises an error. |

**Note**: detection requires the scheme separator after `ed2k`. A relative link such as `ed2k-guide.html`, common on forums about the subject, is therefore discarded and cannot produce a ghost entry.

### SF-2 — Display popup

| Ref | Rule |
|---|---|
| SF-2.1 | The popup is injected **as the first child of `<body>`**, at the top left of the page. |
| SF-2.2 | `fixed` positioning (follows scrolling) or `absolute` (stays at the top of the page), chosen in the settings. |
| SF-2.3 | Maximum height and width can be set in pixels; `0` = unlimited. These limits apply **in normal mode only**; in edit mode the popup switches to `max-height/width: 100%`. |
| SF-2.4 | In normal mode, the popup can be **resized** by the user (`resize: both`); in edit mode, it cannot. |
| SF-2.5 | Rendering: white background, 0.97 opacity, 2 px blue border, `z-index: 255`, 10 px font. |
| SF-2.6 | CSS styles are **scoped to the popup** (selectors prefixed with `div#theDiv` / `div#divBody`) so as not to affect the host page (0.7 fix). |
| SF-2.7 | A **toolbar is displayed at the top and at the bottom** of the popup. |
| SF-2.8 | There is **one popup at most**: opening a popup that is already open does nothing, and keeps its checkboxes and its edit box as they are. |
| SF-2.9 | In normal mode the popup is a column: top toolbar, list of links, bottom toolbar. When the links do not fit in the maximum height, **only the list scrolls**: both toolbars always stay visible. With few links nothing scrolls. |

### SF-3 — Normal mode (list)

| Ref | Rule |
|---|---|
| SF-3.1 | A table is displayed, one row per link: `[checkbox] [clickable file name] [readable size]`. |
| SF-3.2 | All boxes are **checked by default**. |
| SF-3.3 | The file name is an **individual link**: a click sends this file only to the ed2k client, with the configured method, in a tab named `emule`. With the `custom` method, whose sending is a POST form that a link cannot make, the link holds the ed2k link itself, and the click sends the POST for this file only. |
| SF-3.4 | The size is converted into readable binary units (`B`, `KiB`, `MiB`, `GiB`…, base 1024, no decimal). |
| SF-3.5 | The hovered row is highlighted (light blue background). |
| SF-3.6 | A tab order is assigned to the checkboxes. |

### SF-4 — Edit mode

| Ref | Rule |
|---|---|
| SF-4.1 | The body of the popup is replaced by a **text area** containing every detected link, **one per line**. |
| SF-4.2 | The content is **selected automatically** when opened (for an immediate copy/paste). |
| SF-4.3 | The user can freely change, delete or add links; the content of the text area is what will be sent. |
| SF-4.4 | The number of columns and the number of rows can be set. |
| SF-4.5 | The edit box has **no maximum length**: the whole list is always displayed and can be edited, whatever its length, and the user can always type in it. Checked on Chrome with 2,000 links (about 216,000 characters); the automated tests check 1,000. |
| SF-4.6 | Switching between normal and edit mode is stored and **persists from one page to the next**. |

### SF-5 — Selection

| Ref | Rule |
|---|---|
| SF-5.1 | A "check all / uncheck all" box in the top toolbar. |
| SF-5.2 | Individual selection, row by row. |
| SF-5.3 | Only checked links are sent by "Add all links" (in normal mode). |
| SF-5.4 | The box of the bottom toolbar is present but **disabled** (visual consistency only). The box of the top toolbar is disabled **in edit mode**, where the list is a text area with no checkboxes. |
| SF-5.5 | **Popup not displayed** (closed, or page without links while edit mode is stored): there is no selection to read, so **every link of the page is sent**. This is what makes `Ctrl+Alt+A` and the "Add links" menu entry usable without opening the popup. |
| SF-5.6 | If the selection is empty — no box checked, or page without any ed2k link — sending is **abandoned without effect** (console trace, no window opened). Required because `@include *` makes the shortcut active on every page. |

### SF-6 — Categories

| Ref | Rule |
|---|---|
| SF-6.1 | A drop-down list lets the user choose the destination category in the ed2k client. |
| SF-6.2 | Categories are entered in the settings as `*label1=value1;label2=value2;`. The `*` prefix marks the **default choice**. |
| SF-6.3 | Meaning of the value: **eMule** = tab index (numeric); **aMule** = category name; `0` is turned into `all` for aMule. |
| SF-6.4 | The list is **disabled** for the `local` and `mldonkey` methods (not supported by these targets). |
| SF-6.5 | Each entry is checked: an entry without a name or a value is **skipped** (console trace) and the other categories are kept. Spaces around names and values are removed. Only when **no valid category** remains does an alert appear, and the setting reverts to `*default=0`. |
| SF-6.6 | The category used for sending is read **from memory** (`emuleCat` array), never from the popup DOM: sending remains possible with the popup closed. |
| SF-6.7 | **Exactly one default category**: the first one marked with `*`; any further `*` is ignored; without any `*`, the first category of the list. The drop-down list and the category actually sent (SF-6.6) therefore always agree. |
| SF-6.8 | Changing the category in the drop-down list **does not rebuild the popup**: only the URL of the file name links is updated, as they carry the category. The checkboxes, the text of the edit box, the size and the scroll of the popup are kept. |
| SF-6.9 | The category chosen in the drop-down list is a **one-off choice, for the current page only** (product decision, consistent with a "one page = one batch of files of the same kind" usage). It is not stored: each new page starts again on the default category (`*`) of the settings, and a sending triggered with the popup closed (SF-5.5) uses that default. To change the category for good, change the default in the settings. |

### SF-7 — Sending the links

Five download methods ("Ed2k Download Method"):

| Method | UI label | Transport | Behavior |
|---|---|---|---|
| `local` | Your system default | `ed2k:` protocol | Each link is handed to the system handler through a **click on a synthetic anchor**, one link after the other. No URL, password or category used. **On Chrome, only one link is sent per user gesture** (see L-9). |
| `emule` | (remote) emule | HTTP **GET**, new `emule` window | `URL?w=password&p=<pwd>&cat=<cat>&c=<links>` |
| `amule` | (remote) amule | HTTP **GET**, new `amule` window | `URL/footer.php?pass=<pwd>&selectcat=<cat>&Submit=Download+link&ed2klink=<links>` |
| `mldonkey` | (remote) mldonkey | HTTP **GET**, new `emule` window | `URL/submit?jvcmd=multidllink&links=<links>` |
| `custom` | custom (experimental) | HTTP **POST** (form), `emule` target | Fields `cat`, `ref` (URL of the source page), `ed2k` (links). The form is removed from the page once sent. A click on a single file name sends the same POST for that file (SF-3.3) |

Cross-cutting rules:

| Ref | Rule |
|---|---|
| SF-7.1 | Several links are joined with a **line feed** `\n` as separator (encoded as `%0A` for the GET methods — required for some links, 0.9 fix). |
| SF-7.2 | For the GET methods, the file name is normalized (`decodeURIComponent` then `encodeURIComponent`) **then the whole link is encoded again**: the name ends up deliberately encoded twice, which is what the eMule/aMule web interfaces expect. |
| SF-7.3 | For `custom`, no additional encoding is applied (the POST takes care of it). |
| SF-7.4 | `amule` mode **with a password**: a first window is opened on `footer.php?pass=<pwd>` to establish the session, followed by a **1-second wait**, before the links are actually sent. This is a workaround for the aMule login page. |
| SF-7.5 | After opening, `blur()` is called on the child window to try to give the focus back to the main page (no longer effective on recent browsers). |
| SF-7.6 | In normal mode, the source is the **selection of checked boxes**; in edit mode, it is the **raw content of the text area**, split by line. |
| SF-7.7 | `local` method: the link is **encoded by the script** (`encodeEd2kLink()`), both in the clickable links of the popup and when sending in batch. `ed2k` is not a *special scheme*: everything after `ed2k://` up to the final `/` is parsed as the host of the URL, where `\|`, space, `#`, `?`, `[`, `]`… are forbidden. Recent Chrome turns such a link into `about:blank` instead of encoding it, as older browsers used to do (0.2 changelog). This whole part therefore goes through `encodeURIComponent`, after a prior decoding so that an already encoded link is not encoded twice; `ed2k://` and the final `/` stay in clear. ed2k handlers decode the link they receive. The other methods are not affected: their `http://` URL already encodes the whole link. |
| SF-7.8 | `local` method: the link is **never passed to `location.replace()`**, which rejects it (`SyntaxError`, the URL degenerating into `ed2k:///`) and would replace the document — only the last link of a batch would be sent. The script clicks one **synthetic anchor** per link. |

### SF-8 — Configuration

| Ref | Rule |
|---|---|
| SF-8.1 | A settings dialog is provided, organized in 3 sections: download method, popup, edit area. |
| SF-8.2 | It opens **automatically on first run** (as long as the `emule_config` flag is 0). |
| SF-8.3 | Each field has an **explanatory tooltip** (`title` attribute). |
| SF-8.4 | **Save** and **Close** buttons, and a **Reset to defaults** link. |
| SF-8.5 | Saving **reloads the page** to apply the new settings. |
| SF-8.6 | Settings are persisted through the userscript manager storage (they survive a browser restart and are shared across all sites). |
| SF-8.7 | When an invalid setting is replaced by a usable value (URL without a final `/`, no valid category, popup too small), the corrected value is **stored**, so the alert is shown once and not again on every page load. Only the corrected settings are stored: the other ones stay exactly as the user saved them. |

#### Fields and validation rules

| Field | Type | Default | Validation |
|---|---|---|---|
| `ed2kDlMethod` | list | `local` | — |
| `emuleUrl` | text | `http://127.0.0.1:4711/` | Final `/` added automatically, **except** in `custom` mode |
| `emulePwd` | text | empty | **Optional**: eMule accepts a web interface without a password; empty, it is sent as `p=` |
| `emuleCat` | text | `*default=0;` | Format `[*]name=value;…`; invalid entries skipped, exactly one default (SF-6.5, SF-6.7); no valid category → alert + revert to `*default=0` |
| `popupPos` | radio | `fixed` | `absolute` \| `fixed` |
| `popupHeight` | integer | `800` | If `0 < h < 40`, forced to `0` (otherwise the Settings button becomes unreachable) |
| `popupWidth` | integer | `800` | If `0 < w < 100`, forced to `0` (same reason) |
| `editCol` | integer | `80` | — |
| `editRow` | integer | `16` | — |

### SF-9 — Commands and keyboard shortcuts

Registered both in the **userscript manager menu** and as global shortcuts (`Ctrl+Alt+…`, without `Shift` or `Meta`):

| Shortcut | Menu entry | Action |
|---|---|---|
| `Ctrl+Alt+A` | Add links | Send the selected links |
| `Ctrl+Alt+M` | Change mode (edit/normal) | Switch between normal and edit mode (opens the popup in normal mode when it is closed) |
| `Ctrl+Alt+C` | Close Popup | Close the popup (state stored) |
| `Ctrl+Alt+O` | Open Popup | Open the popup, in normal mode; nothing if it is already open (SF-2.8) |
| `Ctrl+Alt+S` | Settings | Open the settings dialog |
| `Ctrl+Alt+X` | — | Toggle the popup open / closed, never duplicating it |
| — | Toggle debug traces | Switch the debug traces in the browser console on or off. The choice is stored (`debug_mode`), off by default; a confirmation alert is shown |

### SF-10 — Persistence of the display state

| Ref | Rule |
|---|---|
| SF-10.1 | The popup state is stored globally in `popup_mode`: `0` = closed, `1` = normal mode, `2` = edit mode. |
| SF-10.2 | This state is **global to all pages**: closing the popup on one site keeps it closed on the next ones, even when they hold ed2k links — nothing is displayed, not even the toolbars — until it is explicitly opened again (`Ctrl+Alt+O`, `Ctrl+Alt+X`, `Ctrl+Alt+M` or the menu). |
| SF-10.3 | An unexpected value raises a trace and an error alert. |

---

## 3. Technical specifications

### 3.1 File layout

| File | Role |
|---|---|
| `GM_EmuleLinker.user.js` | **The deliverable**: single-file userscript, with no external dependency. The `.user.js` extension lets Tampermonkey offer the installation when its address is opened |
| `GM_EmuleLinker.js` | **Former address** of the script, up to 0.9: a copy frozen at 0.10, kept so that the older installations find the new address (§ 3.2). Never to be modified nor deleted |
| `README.md` | User documentation (installation, configuration, limitations) |
| `SPECIFICATIONS.md` | This document |
| `test_sample.html` | Test page covering 11 cases (accents, single/double encoding, AICH hash, encoded scheme, malformed link, server link) |
| `test_many_links.html` | Test page generating 2,000 valid ed2k links (`?n=` to change the number), to check by hand that the popup displays them all, on Firefox in particular (§ 8.3) |
| `tests/` | Automated test suite, run in headless Chrome (§ 8.2), the publication check `check_publication.py` (§ 8.4), and the server of the manual migration check `migration_check.py` (§ 8.3) |
| `screenshots/` | Screenshots referenced by the README |
| `LICENSE` | GPL v3 |
| `Bug.txt` | Local bug log, not tracked by Git (listed in `.gitignore`) |
| `GM_EmuleLinker.code-workspace` | VS Code workspace (parent folder, outside the Git repository): Markdown settings and three launch configurations (Chrome with Tampermonkey, blank Chrome, Firefox with the user's profile) |
| `154608.user-0.6.x.js`, `0.7`, earlier 0.1 scripts, `gm_config-2013-01-27.js`, `readme.txt` | Historical archives outside the Git repository (parent folder) |

The source file is organized in three commented blocks: **PARAM** (default values), **LIB** (embedded GM_config), **CODE** (business logic).

### 3.2 Userscript metadata

```text
@include     *              → active on every page
@grant       GM_getValue, GM_setValue, GM_registerMenuCommand, GM_log
@version     <version>      → written here and in the CHANGELOG only (A-12)
@updateURL / @downloadURL   → raw.githubusercontent.com/alo0/GM_EmuleLinker/master/GM_EmuleLinker.user.js
```

No `@require`, no `@resource`, no network resource loaded: the script is self-contained. Users are invited to restrict where it runs with the **User includes** of its Tampermonkey settings: unlike a change of `@include`, they survive the updates.

**Change of address (0.10).** Up to 0.9, the script was `GM_EmuleLinker.js`, and its update URLs pointed to this file. Tampermonkey checks the `@updateURL` of the *installed* script, downloads the new version from its `@downloadURL`, then follows the URLs written in the new version. This gives the migration, without any action of the users:

1. `GM_EmuleLinker.js` stays at its address, frozen at 0.10, with update URLs pointing to `GM_EmuleLinker.user.js`.
2. An installation in 0.9 or before finds the 0.10 at the former address and installs it: from then on, it checks the new address, and gets the next versions from there.
3. `@name` and `@namespace` never change: Tampermonkey identifies the script by them, so it updates the installed script instead of adding a second one, and the stored settings are kept.

The frozen copy never needs to be updated: whatever the version installed, it leads to the new address. Until 0.10 is published, it is kept identical to `GM_EmuleLinker.user.js` (checked by `test_repository.py`). The migration itself is checked by hand, in a real Tampermonkey (§ 8.3).

### 3.3 Embedded library: GM_config

The **GM_config** library (Mike Medley et al., LGPL, 2009-2010 version) is **inlined** in the file instead of being loaded through `@require`, so that local fixes can be applied to it. It provides: dynamic form building, typed fields (`text`, `int`, `radio`, `select`, `checkbox`, `textarea`, `hidden`, `button`), numeric validation, JSON serialization, `onInit/onOpen/onSave/onClose/onReset` callbacks.

**Local fixes applied**:

| Location | Fix |
|---|---|
| `toNode()`, `select` case | `selected: i == value` instead of `options[i] == value` — the default value of a drop-down list was ignored (GM_config issue #30) |
| `open()`, iframe loading | `frame.contentDocument \|\| frame.contentWindow.document` — `contentDocument` can be `null` on Chrome/Tampermonkey |
| `scriptConfig()` | A **`<div>` is passed as container** instead of letting the library create an iframe, which avoids cross-origin restrictions on Chrome/Tampermonkey |

Storage automatically falls back to `localStorage` when the `GM_getValue` API is missing.

### 3.4 Data model

**Global state in memory** — three parallel arrays with consistent indexes:

```js
eLinks[i]  // full ed2k link, decoded       "ed2k://|file|name.mp3|1048576|HASH|/"
eFiles[i]  // displayed file name           "name.mp3"  (suffixed " (i)" if duplicate)
eSizes[i]  // size in bytes, raw            "1048576"
```

**Structure of an ED2K link** after `split('|')`:

| Index | Content | Example |
|---|---|---|
| 0 | scheme | `ed2k://` |
| 1 | type | `file` |
| 2 | **file name** | `example1.mp3` |
| 3 | **size (bytes)** | `1048576` |
| 4 | MD4 hash (32 hexadecimal characters) | `ABCDEF1234567890ABCDEF1234567890` |
| 5+ | optional: AICH hash `h=…`, sources, then `/` | `h=YNCK…` |

**Categories** — array of `{name, value, select}` objects, serialized to a string with `catToStr()` / deserialized with `strToCat()`.

#### Persistent storage keys

| Key | Scope | Values |
|---|---|---|
| `GM_config` | User settings (JSON of all fields) | serialized object |
| `popup_mode` | Popup display state | `0` closed, `1` normal, `2` edit |
| `emule_config` | "Configuration already done" flag | `0` / `1` |
| `debug_mode` | Debug traces in the browser console (menu "Toggle debug traces") | `0` (default) / `1` |

### 3.5 Execution sequence

```text
Page load
  │
  ├─ GM_registerMenuCommand × 5                  (menu entries + accelerators)
  │
  ├─ scriptConfig()
  │    ├─ creates the container <div>, appended to body
  │    ├─ GM_config.init(div, title, fields, {save: () => location.reload()})
  │    │     └─ reads the storage, creates the GM_configField objects
  │    ├─ if emule_config < 1 → GM_config.open()   (first run)
  │    └─ saveConfig()                              (config → global variables + validation)
  │
  ├─ try { getEd2kLinks(eLinks, eFiles, eSizes) } → n   (failure contained, n = 0)
  │    └─ per link: isEd2kLink → decodeEd2kLink → deduplication
  │                → split('|') → isValidEd2kFile → storage
  │
  ├─ if n > 0 and popup_mode != 0 → createPopup()
  │    ├─ builds <div id="theDiv"> + scoped <style>
  │    ├─ addToolbar(container, 0)                (top: checkall, Add, Mode, Category)
  │    ├─ depending on popup_mode:
  │    │     1 → htmlLinkList()  → <div id="divBody"> with the table
  │    │     2 → addEditBox()    → <textarea id="editbox">
  │    └─ addToolbar(container, 1)                (bottom: Add, Mode, Settings, Close)
  │
  └─ installs the global keydown listener
```

**Sending sequence** (`addButton`, asynchronous):

```text
addButton()
  ├─ normal mode → getSelectLink(eLinks)          (checked boxes)
  │  edit mode   → textarea.value.split('\n')
  ├─ getAddLink(links) → href                     (encoding + URL depending on the method)
  └─ dispatch:
       local     → loop openLocalLink(link)       (click on a synthetic anchor)
       custom    → post(emuleUrl, href)           (POST form, target "emule")
       amule     → [if pwd] window.open(footer.php?pass=…) + await sleep(1000)
                   window.open(href, 'amule') ; blur()
       others    → window.open(href, 'emule') ; blur()
```

### 3.6 Function inventory

| Function | Responsibility |
|---|---|
| `getEd2kLinks(links, files, sizes)` | XPath scan, decoding, deduplication, validation, name/size extraction, suffixing |
| `isEd2kLink(href)` | Recognizes the `ed2k` scheme, literal or encoded at any depth |
| `decodeEd2kLink(href)` | Decodes in successive passes until the scheme is readable (max 4) |
| `isValidEd2kFile(tlnk)` | Structural validation of the split link (5 fields, `file` type, name, numeric size) |
| `createPopup(links, files, sizes)` | Builds and injects the popup depending on `popup_mode` |
| `delPopup()` / `updatePopup()` | Removes / rebuilds the popup |
| `htmlLinkList(links, files, sizes)` | Generates the HTML table (normal mode) |
| `addToolbar(container, pos)` | Top (`pos=0`) or bottom (`pos=1`) toolbar |
| `addEditBox(container, txt)` / `delEditBox()` | Text area (edit mode) |
| `concatLinks(links)` | Joins the links, separated by `\n` |
| `getSelectLink(links)` | Extracts the links whose box is checked; every link when the boxes do not exist |
| `getSelectedCat()` | Reads the selected category from `emuleCat` (independent of the DOM) |
| `getAddLink(links)` | **Core of the adaptation**: encoding and building of the URL/payload per method |
| `addButton()` | Triggers the sending (asynchronous) |
| `openButton()` | Opens the popup, unless it is already open or the page has no ed2k link |
| `debugButton()` | Switches the debug traces on or off, and stores the choice |
| `refreshLinkUrls()` | Updates the URL of the file name links after a category change, without rebuilding the popup |
| `editButton()` / `closeButton()` / `setButton()` / `checkButton()` / `changeCat()` | UI action handlers |
| `scriptConfig()` / `saveConfig()` / `resetConfig()` | Configuration lifecycle |
| `catToStr(cat)` / `strToCat(str)` | Category serialization |
| `post(path, params, method)` | Sends through an HTML form (`custom` method), removed from the page once submitted |
| `linkHref(link)` | The href of a file name link of the popup: the URL of the method, or the ed2k link itself with `custom` |
| `clickOneLink(e)` | With `custom`, turns a click on a file name into the POST for that file |
| `humanFileSize(bytes, si, dp)` | Readable size formatting |
| `encodeEd2kLink(lnk)` | Encodes the part between `ed2k://` and the final `/` (`local` method, popup and batch sending) |
| `openLocalLink(lnk)` | Hands a link to the system `ed2k:` handler through a synthetic anchor |
| `sleep(ms)` | Delay (aMule login workaround) |
| `trace(txt)` | Logging in the browser console, when the debug traces are on (`debug_mode` setting) |

**Dead / experimental code kept**: `silentPost()` and `silentGet()` (blocked by CORS and mixed content), `loadChildWindow()` / `waitReady()` (marked "Not working"), commented-out `amule` POST branch.

### 3.7 Key technical choices

| Choice | Rationale | Consequence |
|---|---|---|
| Single-file userscript, no build | Installation by copy/paste, maximum portability | Third-party library duplicated in the source; the tests inject the file unchanged into the pages (§ 8.2) |
| Mostly ES5 JavaScript (`var`, `new Array()`) | Legacy from 2012-2013 | A few modern elements here and there: `async/await`, arrow functions, default parameters, `**` |
| DOM handled by hand (no framework) | No dependency | HTML built by string concatenation for the popup and the table |
| Opening a window (`window.open`) rather than `XMLHttpRequest` | Silent cross-origin calls are blocked by modern browsers (CORS, mixed content) | A visible window at each sending, `blur()` ineffective — see § 4 |
| **GET** transport for eMule/aMule/MLDonkey | The only method requiring neither server configuration nor complex interaction | Password in clear in the URL and the history; limited URL length |
| File name deliberately encoded twice | Expected by the eMule/aMule web interfaces | Delicate encoding logic, the source of most historical fixes |
| XPath rather than `querySelectorAll` | Legacy | Functionally equivalent here |

---

## 4. Constraints, limitations and security

| Ref | Item |
|---|---|
| L-1 | **Password in clear in the URL** (`p=`, `pass=`): visible in the browser history, in the web server logs, and on the network when using HTTP. → The README explicitly recommends HTTPS to access the remote client. |
| L-2 | **Limited URL length** with GET (browser, proxies, eMule/aMule web server). Beyond it, the sending is silently ignored. → Workaround: send the links in batches. |
| L-3 | **Mixed content / CORS**: a silent XHR sending from an HTTPS page to an eMule served over HTTP is blocked. This is why `silentPost()` was abandoned. |
| L-4 | **Popup blockers**: opening a window can be blocked when it is not seen as triggered by a user gesture — especially the second aMule window after `await sleep(1000)`. |
| L-5 | **Deprecated `blur()`**: giving the focus back to the main page no longer works on recent browsers. |
| L-6 | **aMule login workaround based on a fixed delay** (1 s): fragile with a slow server or network latency. |
| L-7 | **`@include *`**: the script runs on every visited page, including sensitive HTTPS pages. The popup only appears when ed2k links are detected, but the DOM scan and the injection of the settings `<div>` always take place. |
| L-8 | No feedback from the ed2k client is used: the script does not know whether the links were added successfully. |
| L-9 | **Chrome: one link per user gesture with the `local` method.** Chrome requires a real user gesture to launch an external application and **consumes it** at the first launch: the following links of a batch are refused (`Not allowed to launch '…' because a user gesture is required`). Firefox is not affected. A gesture cannot be simulated: an event produced by a script (`click()`, `dispatchEvent()`) is flagged `isTrusted === false` and grants no activation. **Validated workaround**: enable the eMule web server, even locally, and choose the `(remote) emule` method with `http://127.0.0.1:4711/` — all links are sent in a single request, hence with a single gesture. |
| L-10 | **aMule 2.x only**: the `(remote) amule` method does not work with the newest aMule versions (3.x). |

---

## 5. Known defects and technical debt

| Ref | Defect | Severity |
|---|---|---|
| ~~A-1~~ | ~~**Malformed ed2k link → script crash** (`Bug.txt`). A `href` such as `ed2k://xxxxxxxx` with no `\|` separator gives `tlnk[2] === undefined`, then a `TypeError` in `getEd2kLinks()`, which interrupts the whole detection.~~ **Fixed**: structural validation before the fields are used (SF-1.7), arrays written only after validation (SF-1.10) and errors contained at the call site (SF-1.11). Validated on the page of the original report. | — |
| ~~A-2~~ | ~~**Detection regex too permissive**: `/^ed2k*/` means "`ed2` followed by zero or more `k`" — a `href` starting with `ed2` is enough.~~ **Fixed**: detection now relies on the raw attribute and on an explicit scheme, encoded or not (SF-1.2 to SF-1.4). Also lifts the former limitation that links with an encoded scheme were not detected. | — |
| ~~A-3~~ | ~~**`getAddLink()`, `getSelectLink()` and `addButton()` depend on the popup DOM** (`#cat`, `#l<i>`, `#editbox`). Triggered with the popup closed, or on a page without links while edit mode is stored, these elements are missing → exception. Same for the "check all" box in edit mode.~~ **Fixed**: category read from memory (SF-6.6), selection tolerant of missing boxes (SF-5.5), edit mode fallback, guard on empty selection (SF-5.6), "check all" box disabled in edit mode (SF-5.4). | — |
| ~~A-4~~ | ~~**`strToCat('')`** accesses `cat[0].name` on an empty array → exception instead of the expected `-1` return.~~ **Fixed**. The actual severity was major: `strToCat()` runs at every page load, outside the containment of SF-1.11, so an emptied Category setting stopped the script on every page, keyboard shortcuts included. Every entry is now validated (SF-6.5), exactly one default category is kept (SF-6.7, which also fixes a mismatch between the category displayed, and the category sent), and corrected settings are stored so that their alert no longer repeats on every page (SF-8.7). | — |
| ~~A-5~~ | ~~**`Ctrl+Alt+O` with the popup already open**: `createPopup()` is called without removing the previous one → duplicated `<div id="theDiv">`.~~ **Fixed**, with the other defects of the same family found while testing it: a normal popup added on top of the edit mode one; a popup closed on a page shown again, reduced to its toolbars, on the next ones; an empty popup opened on a page without ed2k links; `Ctrl+Alt+C`, `M` and `X` raising an exception on such a page (`M` changing the stored mode anyway); the "Open Popup" menu entry not working at all (`location.reload` passed without its object: `Illegal invocation`). A single `openButton()` now opens the popup (SF-2.8, SF-10.2, SF-1.12). | — |
| ~~A-6~~ | ~~**`local` method with several links**: `window.location.replace()` is called in a loop; only the last navigation actually takes effect.~~ **Fixed**, together with a more serious crash that this defect was hiding: `location.replace()` rejects any raw ed2k link (`SyntaxError`), so **no** link was sent on recent browsers. Replaced by a click on a synthetic anchor **with explicit encoding of the link** (see SF-7.7 / SF-7.8) — without this encoding, recent Chrome ends up on `about:blank`. | — |
| ~~A-7~~ | ~~**`changeCat()` rebuilds the popup**: the user's checkbox selection is lost when the category changes.~~ **Fixed**. The loss was wider than the checkboxes: the size and the scroll of the popup, and above all the text typed in the edit box, were lost too. The popup was rebuilt only to update the URL of its links, which carry the category: `refreshLinkUrls()` now updates them alone (SF-6.8). | — |
| ~~A-8~~ | ~~**`editMaxLength` is a ratchet**: validation compares with the current value, so the value can only increase.~~ **Fixed**, after a closer look that corrected this description: the value could go down, but never below the default 16,384, and the real defect was elsewhere. `maxLength` never truncates a text put in the edit box by the script: a list longer than the limit was displayed in full, yet an alert claimed the opposite ("to display the entire list"), and the user could no longer type in the box. The `MaxLength` setting is removed (SF-4.5); a value stored by a previous version is ignored, without any alert. | — |
| ~~A-9~~ | ~~**Recursive `saveConfig()`** when the password is missing (`err < 0` → `GM_config.open()` + `saveConfig()`), possibly in a loop.~~ **Fixed**, after a check that corrected this description: there was no loop, only one useless extra pass, as the password was set to `something` before it. The real defect was the check itself: eMule does **not** require a password (confirmed by hand). With an empty password, an alert and the settings dialog opened on every page visited, even without ed2k links, the dialog showed `something` as if a password were set, and pressing Save stored it, so that sending to an eMule without password then failed. The check, the recursion and the `something` placeholder are removed; the password is empty by default. | — |
| ~~A-10~~ | ~~**`DEBUG_MODE = 1` in production**: console traces active on every page.~~ **Fixed**: the constant had to be set back to 0 by hand before publishing, which was easy to forget. The debug mode is now a stored setting, off by default and switched by the menu entry "Toggle debug traces" (SF-9): the published file no longer holds any debug value, and a user reporting a problem can switch the traces on without editing the script. | — |
| ~~A-11~~ | ~~**CSS typo**: extra `}` braces in the `div#divBody td` / `th` rules of the inline style sheet.~~ **Fixed**. Each extra brace made the browser drop the rule that followed it, silently: `div#divBody th` and `div#divBody tr` were ignored (12 rules kept out of 14). No visible effect, as the table has no header and its cells were already white, but any rule added there later would have been dropped too. The browser now keeps all 14 rules; the popup renders as before. | — |
| ~~A-12~~ | ~~**Duplicated version**: the `@version` variable and the CHANGELOG at the top of the file are maintained by hand, in addition to `readme.txt` (archive) and `README.md`.~~ **Fixed**: the version is written by hand in the header of the script only, `@version` and CHANGELOG, which Tampermonkey reads. This document refers to it instead of repeating it, and the README screenshots are no longer named after a version. A test checks that `@version` and the CHANGELOG agree and that no other file writes a version (§ 8.2), and the publication steps include the date of the CHANGELOG entry (§ 8.4). `readme.txt` is an archive outside the repository, no longer maintained. | — |
| ~~A-13~~ | ~~**Other characters forbidden in the host** not encoded when only the `\|` were: spaces, `#`, `?`, `[`, `]`…~~ **Fixed**: confirmed on Chrome with cases 3 and 4, refused when only the `\|` were encoded. The whole link is now encoded (SF-7.7): validated in eMule on Chrome and Firefox, AICH hash included. | — |
| ~~A-14~~ | ~~**`custom` method: the popup links point to the page itself.**~~ **Fixed**. For `custom`, `getAddLink()` returns the fields of a POST form, in an array used as a dictionary; with no numbered element, it turned into an empty `href`, which leads to the page itself: a click opened a copy of the page in a new tab, where the script ran again, and sent nothing. A link cannot send a POST form: the link now holds the ed2k link, and the click sends the POST for that file (SF-3.3). The POST forms, which piled up in the page at each sending, are removed once sent. | — |
| ~~A-15~~ | ~~**With many links, the toolbars scroll out of sight**: the whole popup scrolled, toolbars included, so the bottom toolbar was hidden at load and the top one once the list scrolled down. The layout dated from version 0.6.~~ **Fixed**: each toolbar is now one block, and the popup a column where only the list scrolls (SF-2.9). With few links the popup is 5 px taller than before. | — |

---

## 6. Compatibility

Support of each download method, with Tampermonkey, on the latest stable version of the browsers:

| Browser | `local` (system default) | `emule` (web interface) | `amule` (web interface) | `mldonkey` (web interface) |
|---|---|---|---|---|
| Chrome | Partial ¹ | Full | Partial ² | Not tested |
| **Firefox** (recommended) | Full | Full | Partial ² | Not tested |

¹ One link per user gesture (L-9). Workaround: the `(remote) emule` method with `http://127.0.0.1:4711/`, which sends all the links at once.

² aMule 2.x only (L-10).

| Item | Support |
|---|---|
| Managers | **Tampermonkey** (recommended and tested), Greasemonkey (origin), Violentmonkey (not tested) |
| ed2k clients tested | eMule (local and remote), aMule 2.x (remote only) |
| `custom` method | Experimental |

---

## 7. Identified improvements

By decreasing value, combining `Bug.txt`, the `readme.txt` roadmap and the code analysis:

1. **Automatic batch sending** when the URL exceeds a length threshold (L-2).
2. **Dynamically disable** the configuration fields that do not apply to the chosen method.
3. **Extension filter** (allow list / block list) in the settings.
4. **Visual feedback on the sending result** in the popup body — including a counter of the links ignored by SF-1.7, currently rejected silently.
5. Multiple languages, online help.
6. **Technical work**: separate the GM_config library from the business script (through `@require` on a frozen copy) and modernize the syntax. The automated test suite (§ 8.2) makes such changes safer.

---

## 8. Tests

### 8.1 Test page

`test_sample.html` covers the following cases, to be run again after any change to the detection/encoding chain:

| # | Case | Expected |
|---|---|---|
| 1-2 | Simple links (audio, video) | Detected, exact name and size |
| 3 | Additional **AICH** hash (`h=…`) | Detected and displayed normally |
| 4 | **Raw** special characters (accents, spaces, parentheses) | Name displayed as is |
| 5 | Name **encoded once** (UTF-8) | Decoded once |
| 6 | Name **encoded twice** (`%25`) | Decoded twice |
| 7 | `ed2k://` kept, **rest encoded** (`%7C`, `%2F`) | Detected, name correctly decoded |
| 8 | **Fully encoded** link (`ed2k%3A%2F%2F`) | Detected after 1 pass, name correctly decoded |
| 9 | Scheme **encoded twice** (`ed2k%253A%252F%252F`) | Detected after 2 passes, name correctly decoded |
| 10 | **Malformed** link `ed2k://xxxxxxxx` | Ignored, **and the 9 valid links are still displayed** (`Bug.txt` non-regression) |
| 11 | **Server** link | Ignored |

All valid links follow the ed2k format: MD4 hash of 32 hexadecimal characters, numeric size. eMule and aMule reject a hash of any other length.

### 8.2 Automated test suite

The `tests/` folder holds a suite run in a real headless Chrome, with the Python standard library only:

```text
python tests/run_tests.py                run every test
python tests/run_tests.py category       run the tests whose name contains "category"
python tests/run_tests.py --live-emule   run the live test against the real eMule (see below)
```

The exit code is 1 when a test fails. Chrome is found automatically, or through the `CHROME_PATH` environment variable. In VS Code, the same tests appear in the Testing panel, one class per level, through the unittest adapter `tests/vscode_tests.py` (the live test is left out of it).

`GM_EmuleLinker.user.js` is injected **unchanged** into the pages served by a local web server, after a small stand-in for the `GM_*` API (`tests/gm_shim.js`, values kept in `localStorage`): Tampermonkey is not needed. Chrome is driven through the DevTools protocol, so the keyboard shortcuts and the mouse clicks are real (trusted) events, and the alerts are caught. Testing in a real browser matters for this script: most of its defects came from browser behavior (URL parsing of `ed2k:` links, user gestures), which a simulated DOM does not reproduce.

**Fake ed2k clients.** The test web server also answers under `/__emule`, standing for the web interface of eMule, aMule, MLDonkey or a custom server. The script really sends its requests there, through the browser, and each test checks what an ed2k client would read in them (password, category, name, size and hash of every link). Nothing reaches a real ed2k client. Only the `local` method cannot be served this way (`ed2k:` links): its anchor clicks are caught and recorded.

| Level | File | Content |
|---|---|---|
| 0 — Repository | `tests/test_repository.py` | Without the browser: `@version` and the CHANGELOG agree, the CHANGELOG is in order, no other file writes a version (A-12); the update URLs, and the former address `GM_EmuleLinker.js` leading to the new one (§ 3.2) |
| 1 — Functions | `tests/test_units.py` | Tables of cases for `isEd2kLink`, `decodeEd2kLink`, `isValidEd2kFile`, `encodeEd2kLink`, `strToCat`, `catToStr`, `humanFileSize` |
| 2 — Scenarios | `tests/test_scenarios.py` | Detection on `test_sample.html`, page without ed2k links, first run, shortcuts, opening and closing the popup, menu entries, a huge number of links, toolbars staying visible, categories, settings saved through the dialog, edit mode, `local` method, corrected settings stored, optional eMule password |
| 2 — Sending | `tests/test_sending.py` | Against the fake clients: `emule` (all links, popup closed, partial selection, category change keeping the popup and the edit box text, edit box text, single link click), `amule` (with and without password, delay between the two requests), `mldonkey`, `custom` (POST form), nothing sent when there is nothing to send |
| 3 — Live | `tests/test_live_emule.py` | Optional, against the running eMule (below) |

Each test names the rule (SF-x) or defect (A-x) it checks. Many checks read the debug traces: the tests switch them on through the `debug_mode` setting, whatever the default of the script.

**Live test against the real eMule** (`--live-emule`), to run before a release, with eMule running and its web server enabled. The web password is read from the `EMULE_PASSWORD` environment variable, the address from `EMULE_URL` (default `http://127.0.0.1:4711/`). The script adds three test files to eMule; the test finds them in the eMule transfer list, with their names intact (spaces, accents, parentheses, `&`, brackets) and their hashes, then **cancels them**, even when the test fails, and checks that they are gone. The test files carry a random marker in their name and random hashes: nothing else in eMule is ever touched. The password never reaches the disk durably: the test sends it to eMule in POST bodies only; the script under test puts it in its GET URL, but inside the temporary Chrome profile, which the runner deletes at the end — the run fails if it cannot; and every message printed is masked. What eMule itself writes in its own log is outside the reach of the tests.

Non-regression cases still to add: two different links with the same file name (SF-1.9), and the known defect A-14.

### 8.3 Manual checks before a release

What depends on elements outside the reach of the suite — the extension, Firefox, the Windows protocol handler — is checked by hand, with the user's own browser profiles:

1. Run `python tests/run_tests.py --live-emule` (§ 8.2): it covers the `(remote) emule` method end to end, eMule included.
2. Install the script in Tampermonkey, on Chrome and on Firefox, and open `test_sample.html`: the popup lists the 9 valid links.
3. `local` method: on Chrome, clicking a file name in the popup adds it to eMule (one link per user gesture, L-9); on Firefox, "Add all links" adds the 9 links.
4. `(remote) emule` method on Firefox: "Add all links" adds the 9 links to eMule, in the selected category.
5. `(remote) amule` method, when an aMule is available: same check, with and without a password.
6. The settings survive a browser restart.
7. On Firefox, open `test_many_links.html`: the popup lists the 2,000 links, and in edit mode the edit box holds them all and still accepts typing (SF-4.5).
8. **Change of address** (§ 3.2), for the 0.10 only: run `python tests/migration_check.py` and follow the steps it prints, in a browser profile with Tampermonkey but without the real Emule Linker. A local server stands for GitHub: Tampermonkey installs the 0.9, updates to 0.10 from the former address, then to a simulated next version from the new one, and the settings are kept.

The test files added by hand to eMule in checks 3 to 5 must then be cancelled by hand.

### 8.4 Publishing a version

The users get a new version through `@updateURL`, which points to the `master` branch on GitHub. To publish one:

1. **Check that nothing personal will be published**: `python tests/check_publication.py`, with `EMULE_PASSWORD` set. It looks at every commit not yet on GitHub (`origin/master..HEAD`): its author and committer e-mail addresses (only no-reply addresses may be published), its message, and every text file it holds. It reports any e-mail address other than the public ones, any local path revealing a user folder, the real eMule password, and the terms listed in `tests/private_terms.txt` — a local file ignored by git, for what cannot be written in the published script itself (names of private machines, of sites...). Findings never show a private value. There must be no finding.
2. In the header of `GM_EmuleLinker.user.js`, check `@version` and set the date of the first CHANGELOG entry to the publication day. For the 0.10 only, copy it then to `GM_EmuleLinker.js` (§ 3.2); from the 0.11 on, this frozen copy is no longer touched.
3. Retake the screenshots of the README from this version: `screenshots/screenshot_main.png` (the popup) and `screenshots/screenshot_settings.png` (the settings dialog). Make sure they show nothing personal: other tabs, bookmarks, addresses, account names.
4. Run `python tests/run_tests.py`, then `python tests/run_tests.py --live-emule`, and the manual checks of § 8.3.
5. Run `python tests/check_publication.py` again: steps 2 and 3 added commits.
6. Merge the version branch into `master`.
7. Tag the merge: `git tag vX.Y`.
8. Push `master` and the tag: `git push origin master vX.Y`.
