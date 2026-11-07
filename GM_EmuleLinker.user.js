// ==UserScript==
// @name        Emule Linker
// @namespace   https://github.com/alo0/GM_EmuleLinker
// @description Finds every ed2k link of a page and sends them in one click to eMule, aMule, MLDonkey, the ed2k application of your system, or your own server
// @include     *
// @grant		GM_getValue
// @grant		GM_setValue
// @grant		GM_registerMenuCommand
// @grant 		GM_log
// @grant 		GM_xmlhttpRequest
// @connect     *
// @version     0.14
// @updateURL       https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/GM_EmuleLinker.user.js
// @downloadURL     https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/GM_EmuleLinker.user.js
// ==/UserScript==
// -------------------------------------------------------------------------
// WHAT IT DOES:
// Finds every ed2k link of the page, even URL-encoded ones (invalid links
// are ignored), and lists the files with their size in a popup at the top
// left of the page. Choose the links with the checkboxes, or edit the list
// as text, pick a category, then send them in one click to:
//  - the application of your system that handles ed2k links,
//  - eMule, aMule 2.x or MLDonkey, through their web interface,
//  - aMule 3.1 and later, through its REST API,
//  - or your own server.
// Everything is also available from the Tampermonkey menu and through
// keyboard shortcuts (Ctrl+Alt+D to send the links).
// -------------------------------------------------------------------------
// INSTALLATION
// 1. install this script in the Tampermonkey extension
// 2. (optional) to send the links to eMule, aMule or MLDonkey, activate the web interface of this application
// 3. Navigate to a page with ed2k links
// => The popup should appear at the upper left
// 4. Edit the script params using the settings dialog (ctl+alt+s)
// 5. (optional) restrict the pages where this script is active with the "User includes" of its
//    Tampermonkey settings: unlike a change of the @include variable, they survive the updates
// -------------------------------------------------------------------------
// CHANGELOG: see CHANGELOG.md
// https://github.com/alo0/GM_EmuleLinker/blob/master/CHANGELOG.md
// -------------------------------------------------------------------------
// CONTENTS: Script structure (this file):
//  PARAM      the default values of the settings, then the look: the CSS of the popup, of its boxes and
//             of the settings dialog, the icons of the popup (the themes to come); then the texts, one
//             table per language
//  LIB        GM_config, the library of the settings dialog, embedded with local fixes
//  CODE       State       the links of the page, the state of the popup, of the sending and of the settings dialog
//             Startup     the menus, the settings read, the links found, the popup shown, the keyboard shortcuts
//             Detection   the ed2k links of the page (SF-1)
//             Popup       its toolbars, its views, its list, its edit box and its commands (SF-2 to SF-5, SF-9, SF-10)
//             Selection   the links checked, the server and the category chosen (SF-5, SF-6, I-6)
//             Sending     the links to the method of the settings, and the answer of the client (SF-7)
//             Settings    the settings read and saved, the settings dialog and its servers (SF-8)
//             Utilities   the traces, the requests of the script, the categories as text, the sizes
// -------------------------------------------------------------------------



// -------------------------------------------------------------------------
// 								PARAM
// -------------------------------------------------------------------------
// These are the default values. Use the setting dialog to modify the parameters

// Debug traces in the browser console 0|1: a stored setting, off by default, switched by the
// menu entry "Toggle debug traces". Nothing to change in the code before publishing it.
var DEBUG_MODE = GM_getValue('debug_mode', 0);

// General parameters
var language = 'browser'; // the language of the texts: browser (the one of the browser, when the script has its texts), en or fr (a setting, I-7)
var popupView = 'maximized'; // the view of the popup when a page with ed2k links opens: maximized, minimized or closed
var closeMessage = true; // a message when the popup is closed (its Close button, Ctrl+Alt+C, the menu), telling how to open it again (a setting)

// emule/amule/mldonkey server parameters
var ed2kDlMethod = 'local';
	// local: ed2k default application of your system (default)
	// emule: emule via web url
	// amuleapi: aMule 3.1 and later via its REST API
	// amule: amule via web url
	// mldonkey: mldonkey via web url
	// custom: custom via web url

var emuleUrl = 'http://127.0.0.1:4711/'; 	// the adress and port of your emule web server
var emuleUser = 'admin'; // the user of the web interface of MLDonkey (its default one)
var emulePwd = ''; // the password to access the emule web server (optional)
var emuleCat = [ {name: 'default', value: '0', select: '1'} ]; // Which emule category to assign 0=all (default)

// Popup parameters
var popupCorner = 'top-left'; // the corner of the window where the popup is shown: top-left, top-right, bottom-left or bottom-right
var popupScroll = 'floating'; // floating: the popup stays in view when the page scrolls; static: it scrolls with the page
var popupHeight = 800; // max height in pixel of the popup box
var popupWidth = 800; // max width in pixel of the popup box
var checkFilter = ''; // the links checked in the popup: a regular expression on the file name ('' checks every link)
var showCategories = true; // the category list in the toolbars of the popup (a setting)
var categoryListMinWidth = 100; // min width in pixels of the category list: the short categories of another server (I-6) move nothing
var categoryListMaxWidth = 140; // max width in pixels of the category list: a longer name is cut, the open list and the tooltip show it whole
var showServerList = true; // the server list in the toolbars of the popup, when it offers two choices at least (a setting)
var serverListMaxWidth = 140; // max width in pixels of the server list: a longer name is cut, the open list and the tooltip show it whole
var STATUS_DELAY = 8000; // how long the band of a success (links added) stays, in ms; an error stays until closed (SF-7.10)

// edit box parameters
var editCol = 80; // number of column
var editRow = 16; // number of line

// The GitHub repository of the script, linked from the bottom of the settings dialog: its issues, to
// report a problem, and the repository itself. If it moves, change also @updateURL and @downloadURL
// in the header, but never @namespace: it identifies the installed script (a new one would be added).
var REPOSITORY = 'https://github.com/alo0/GM_EmuleLinker';

// -------------------------------------------------------------------------
// The look: the CSS of the popup, of its message, of its help, of the band of the answers and of the settings
// dialog, the icons of the popup. Gathered here for the themes to come (I-8); the texts of the languages (I-7)
// follow them.
// -------------------------------------------------------------------------

// The CSS of the popup, scoped to it (div#theDiv, div#divBody, SF-2.6): it sets every size of its
// toolbars and of its rows itself, whatever the styles of the page (SF-2.5)
var POPUP_CSS = ' \
		div#theDiv button { \
			font-size:11px;\
		} \
		div#theDiv select { \
			font-size:11px;\
		} \
		div#theDiv input.smallcheck { \
			height: 13px; \
			width: 13px; \
			margin: 0; \
			vertical-align: middle; \
		} \
		div#divBody input.smallcheck { display: block; } \
		div#theDiv .toolbar { \
			display: flex; align-items: center; gap: 6px; flex: none; \
			padding: 5px 9px; \
			margin: 0 -5px; border: 0; height: auto; min-height: 0; width: auto; float: none; position: static; box-sizing: content-box; \
			background: #e8f1fb; box-shadow: none; \
		} \
		div#theDiv .toolbar button, div#theDiv .toolbar select { \
			height: 22px; min-height: 0; max-height: none; box-sizing: border-box; margin: 0; padding: 0 8px; \
			font-size: 12px; font-weight: normal; line-height: normal; vertical-align: middle; \
		} \
		div#theDiv .toolbar select.emlCat { min-width: ' + categoryListMinWidth + 'px; max-width: ' + categoryListMaxWidth + 'px; } \
		div#theDiv .toolbar select.emlSrv { max-width: ' + serverListMaxWidth + 'px; } \
		div#theDiv .toolbar button, div#theDiv .toolbar select { \
			background-color: #ffffff; color: #000000; border: 1px solid #8f8f9d; border-radius: 3px; \
		} \
		div#theDiv .toolbar button:hover, div#theDiv .toolbar select:hover { background-color: #f3f8fd; } \
		div#theDiv .toolbar button:disabled, div#theDiv .toolbar select:disabled { \
			background-color: #f5f5f5; color: #8a8a8a; border-color: #c8c8c8; \
		} \
		div#theDiv .toolbar button.emlIcon { \
			width: 22px; padding: 0; display: inline-flex; align-items: center; justify-content: center; color: #333333; \
		} \
		div#theDiv .toolbar button.emlIcon svg { display: block; } \
		div#theDiv .toolbar button#emlMin { color: #0075ff; } \
		div#theDiv .toolbar button#emlClose { color: #d00000; } \
		div#theDiv .toolbar button.emlAdd { border: 2px solid #0075ff; border-radius: 3px; background: #ffffff; color: #000; } \
		div#theDiv .toolbar button.emlAdd:hover { background: #f3f8fd; } \
		div#theDiv .toolbar button.emlAdd:disabled { border-color: #bbbbbb; color: #888888; background: #efefef; } \
		div#theDiv .toolbar .emlRight { margin-left: auto; } \
		div#theDiv .emlCount { text-align: left; font-size: 12px; font-variant-numeric: tabular-nums; font-weight: bold; color: #0075ff; white-space: nowrap; } \
		div#theDiv .emlCount span { color: #bababa; font-weight: normal; } \
		div#divBody a {font-size: 10px;} \
		div#divBody a.ed2k:link       { color: #000000; text-decoration: none } \
		div#divBody a.ed2k:visited    { color: #000000; text-decoration: none } \
		div#divBody a.ed2k:hover      { color: #0000FF; text-decoration: underline; font-weight: normal } \
		div#divBody a.ed2k:active     { color: #0000FF; text-decoration: underline; font-weight: normal } \
		div#divBody tr.filtered td, div#divBody tr.filtered a.ed2k { color: #999999 } \
		div#divBody tr.filtered a.ed2k:hover { color: #0000FF } \
		div#divBody input.bigcheck { \
			height: 16px; \
			width: 16px; \
		} \
		div#divBody table { \
			all: revert; \
			margin: 0px auto; \
			font-size: 10px; \
			border-collapse: collapse; \
			width: 100%; \
		} \
		div#divBody td { \
			background: #FFFFFF; padding: 1px 4px; line-height: 15px;} \
		div#divBody td:first-child { padding: 1px 0 1px 4px; width: 13px; } \
		div#divBody td:nth-child(2) { padding-left: 6px; } \
		div#divBody td:last-child { text-align: right; width: 1px; white-space: nowrap; } \
		div#theDiv > div#divBody.emlList { \
			margin: 0 -5px; padding: 0 5px; border-top: 1px solid #a0a0a0; border-bottom: 1px solid #a0a0a0; \
		} \
		div#theDiv .emlShadow { position: absolute; height: 7px; margin: 0; padding: 0; border: 0; pointer-events: none; display: none; } \
		div#theDiv .emlShadow.top { background: linear-gradient(rgba(0,0,0,0.3), rgba(0,0,0,0)); } \
		div#theDiv .emlShadow.bottom { background: linear-gradient(rgba(0,0,0,0), rgba(0,0,0,0.3)); } \
		div#divBody th { \
			background: #FFFFFF; padding: 0px 4px;} \
		div#divBody tr { \
			background: #FFFFFF; \
		} \
		div#divBody tr:hover td { \
			background: #e3f0fa; \
		} \
		div#theDiv div, div#divBody td, div#divBody th { text-align: left; } \
		div#theDiv, div#theDiv * { letter-spacing: normal; word-spacing: normal; text-transform: none; \
			text-indent: 0; font-style: normal; } \
';

// The CSS of the message shown when the popup is closed (I-3), scoped to it (div#emlMsg): the look of
// the popup, every size set whatever the styles of the page, as the popup (SF-2.6); centered in the
// window, on a backdrop as the settings dialog (div#emlMsgBackdrop)
var MESSAGE_CSS = ' \
		div#emlMsgBackdrop { position: fixed; top: 0; left: 0; right: 0; bottom: 0; z-index: 998; margin: 0; padding: 0; \
			background: rgba(0,0,0,.35); } \
		div#emlMsg { \
			position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); z-index: 999; \
			width: 380px; max-width: calc(100vw - 4px); box-sizing: border-box; \
			margin: 0; padding: 0; background: #ffffff; opacity: 1; color: #000000; border: 2px solid #2b5c8a; \
			font-size: 12px; line-height: 1.4; text-align: left; \
		} \
		div#emlMsg, div#emlMsg * { letter-spacing: normal; word-spacing: normal; text-transform: none; \
			text-indent: 0; font-style: normal; } \
		div#emlMsg .emlMsgBar { display: flex; align-items: center; gap: 6px; margin: 0; padding: 5px 9px; background: #e8f1fb; } \
		div#emlMsg .emlMsgBar.bottom { border-top: 1px solid #a0a0a0; } \
		div#emlMsg .emlMsgTitle { font-weight: bold; color: #2b5c8a; } \
		div#emlMsg .emlMsgText { margin: 0; padding: 8px 9px; } \
		div#emlMsg .emlMsgText ul { margin: 4px 0 8px; padding: 0 0 0 22px; list-style: disc; } \
		div#emlMsg .emlMsgText li { margin: 0; padding: 0; } \
		div#emlMsg .emlMsgText a { color: #0075ff; text-decoration: underline; } \
		div#emlMsg b { font-weight: bold; } \
		div#emlMsg button { \
			height: 22px; min-height: 0; max-height: none; box-sizing: border-box; margin: 0 0 0 auto; padding: 0 8px; \
			font-size: 12px; font-weight: normal; line-height: normal; \
		} \
		div#emlMsg button#emlMsgOk { border: 2px solid #0075ff; border-radius: 3px; background: #ffffff; color: #000000; } \
		div#emlMsg button#emlMsgOk:hover { background: #f3f8fd; } \
		div#emlMsg button#emlMsgClose { \
			width: 22px; padding: 0; display: inline-flex; align-items: center; justify-content: center; color: #d00000; \
		} \
		div#emlMsg button svg { display: block; } \
		div#emlMsg label { \
			display: inline-flex; align-items: center; gap: 4px; margin: 0; padding: 0; white-space: nowrap; \
			font-size: 12px; font-weight: normal; \
		} \
		div#emlMsg input { width: 13px; height: 13px; margin: 0; } \
';

// The CSS of the help (I-5), scoped to it (div#emlHelp): the look of the popup, every size set whatever
// the styles of the page, as the popup (SF-2.6); placed by placeHelp()
var HELP_CSS = ' \
		div#emlHelp { \
			position: fixed; top: 0; left: 0; z-index: 256; width: 560px; max-width: calc(100vw - 20px); max-height: calc(100vh - 20px); \
			display: flex; flex-direction: column; box-sizing: border-box; margin: 0; padding: 0; \
			background: #ffffff; opacity: 1; color: #000000; border: 2px solid #2b5c8a; box-shadow: 0 4px 18px rgba(0,0,0,0.25); \
			font-size: 12px; line-height: 1.4; text-align: left; \
		} \
		div#emlHelp, div#emlHelp * { letter-spacing: normal; word-spacing: normal; text-transform: none; \
			text-indent: 0; font-style: normal; } \
		div#emlHelp .emlHelpBar { display: flex; align-items: center; gap: 6px; flex: none; margin: 0; padding: 5px 9px; background: #e8f1fb; } \
		div#emlHelp .emlHelpBar.bottom { border-top: 1px solid #a0a0a0; } \
		div#emlHelp .emlHelpHead { cursor: move; user-select: none; touch-action: none; } \
		div#emlHelp .emlHelpHead button { cursor: default; } \
		div#emlHelp .emlHelpTitle { font-weight: bold; color: #2b5c8a; } \
		div#emlHelp .emlHelpBody { overflow: auto; margin: 0; padding: 4px 12px 10px; } \
		div#emlHelp p { margin: 8px 0 0; padding: 0; } \
		div#emlHelp h4 { margin: 10px 0 4px; padding: 0; border: 0; background: none; font-size: 12px; font-weight: bold; color: #2b5c8a; } \
		div#emlHelp ul { margin: 2px 0; padding: 0 0 0 20px; list-style: disc; } \
		div#emlHelp li { margin: 0; padding: 0; } \
		div#emlHelp table { border-collapse: collapse; width: 100%; margin: 0; border: 0; box-shadow: none; background: none; } \
		div#emlHelp tr, div#emlHelp td { background: none; box-shadow: none; } \
		div#emlHelp td { padding: 3px 6px; vertical-align: middle; border: 0; border-top: 1px solid #e3e3e3; font-size: 12px; } \
		div#emlHelp td:first-child { white-space: nowrap; width: 1px; } \
		div#emlHelp td:last-child { white-space: nowrap; width: 1px; color: #333333; font-weight: bold; } \
		div#emlHelp b { font-weight: bold; } \
		div#emlHelp a { color: #0075ff; text-decoration: underline; } \
		div#emlHelp .emlHelpSep { color: #a0a0a0; } \
		div#emlHelp .emlChip { \
			display: inline-flex; align-items: center; justify-content: center; height: 20px; min-width: 20px; box-sizing: border-box; \
			margin: 0; padding: 0 6px; border: 1px solid #767676; border-radius: 3px; background: #efefef; color: #000000; \
			font-size: 11px; font-weight: normal; vertical-align: middle; \
		} \
		div#emlHelp .emlChip.icon { width: 20px; padding: 0; } \
		div#emlHelp .emlChip.add { border: 2px solid #0075ff; background: #ffffff; } \
		div#emlHelp .emlChip.count { border: 0; background: none; padding: 0; color: #0075ff; font-weight: bold; } \
		div#emlHelp .emlChip.count span { color: #808080; } \
		div#emlHelp .emlChip.min { color: #0075ff; } \
		div#emlHelp .emlChip.close { color: #d00000; } \
		div#emlHelp .emlChip svg { display: block; } \
		div#emlHelp .emlChip input { width: 13px; height: 13px; margin: 0; pointer-events: none; } \
		div#emlHelp button { \
			height: 22px; min-height: 0; max-height: none; box-sizing: border-box; margin: 0 0 0 auto; padding: 0 8px; \
			font-size: 12px; font-weight: normal; line-height: normal; \
		} \
		div#emlHelp button#emlHelpOk { border: 2px solid #0075ff; border-radius: 3px; background: #ffffff; color: #000000; } \
		div#emlHelp button#emlHelpOk:hover { background: #f3f8fd; } \
		div#emlHelp button#emlHelpClose { \
			width: 22px; padding: 0; display: inline-flex; align-items: center; justify-content: center; color: #d00000; \
		} \
		div#emlHelp button svg { display: block; } \
';

// The CSS of the band of the answer of a client (SF-7.10), scoped to it (div#emlStatus): under the top
// toolbar, over the list; the popup closed, alone in the corner of the popup (.toast). Every size set
// whatever the styles of the page, as the popup (SF-2.6); placed by placeStatus()
var STATUS_CSS = ' \
		div#emlStatus { \
			position: absolute; left: 0; right: 0; z-index: 3; display: flex; align-items: center; gap: 6px; \
			margin: 0; padding: 4px 9px; box-sizing: border-box; border: 0; border-top: 1px solid; border-bottom: 1px solid; \
			font-size: 12px; font-weight: bold; line-height: 16px; text-align: left; letter-spacing: normal; text-transform: none; \
		} \
		div#emlStatus.wait { background: #f2f2f2; border-color: #d0d0d0; } \
		div#emlStatus.ok { background: #e6f4ea; border-color: #b7dfc3; } \
		div#emlStatus.ko { background: #fdecea; border-color: #f3c0c0; } \
		div#emlStatus.doubt { background: #fff4e5; border-color: #f0d2a6; } \
		div#emlStatus.toast { \
			position: fixed; left: auto; right: auto; top: auto; bottom: auto; z-index: 255; max-width: calc(100vw - 4px); \
			border-width: 1px; border-style: solid; box-shadow: 0 2px 8px rgba(0,0,0,0.2); \
		} \
		div#emlStatus svg { display: block; flex: none; } \
		div#emlStatus .emlStatusIcon:empty { display: none; } \
		div#emlStatus button { \
			display: flex; margin: 0 0 0 auto; padding: 2px; width: auto; height: auto; min-height: 0; \
			border: 0; background: none; color: inherit; cursor: pointer; \
		} \
';

// The icons of the top toolbar, drawn: centered in their buttons whatever the fonts of the system (I-2)
var ICON_SVG = '<svg width="12" height="12" viewBox="0 0 12 12" aria-hidden="true" focusable="false">';
var ICONS = {
	settings: ICON_SVG + '<path fill="currentColor" fill-rule="evenodd" d="M10.00,5.11 L11.55,5.27 L11.55,6.73 L10.00,6.89 L9.46,8.20 L10.44,9.41 L9.41,10.44 L8.20,9.46 L6.89,10.00 L6.73,11.55 L5.27,11.55 L5.11,10.00 L3.80,9.46 L2.59,10.44 L1.56,9.41 L2.54,8.20 L2.00,6.89 L0.45,6.73 L0.45,5.27 L2.00,5.11 L2.54,3.80 L1.56,2.59 L2.59,1.56 L3.80,2.54 L5.11,2.00 L5.27,0.45 L6.73,0.45 L6.89,2.00 L8.20,2.54 L9.41,1.56 L10.44,2.59 L9.46,3.80 Z M7.90,6.0 A1.9,1.9 0 1,0 4.10,6.0 A1.9,1.9 0 1,0 7.90,6.0 Z"/></svg>',
	minimize: ICON_SVG + '<path fill="currentColor" d="M1,9.5 L11,9.5 L6,2.5 Z"/></svg>',
	maximize: ICON_SVG + '<path fill="currentColor" d="M1,2.5 L11,2.5 L6,9.5 Z"/></svg>',
	help: ICON_SVG + '<path fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" d="M3.8,4.2 A2.3,2.2 0 1,1 7.2,6.1 C6.4,6.6 6,7 6,7.9"/><circle cx="6" cy="10.4" r="1.05" fill="currentColor"/></svg>',
	ok: ICON_SVG + '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M2,6.5 L5,9.2 L10,3"/></svg>',
	warn: ICON_SVG + '<circle cx="6" cy="6" r="5.2" fill="none" stroke="currentColor" stroke-width="1.6"/><path stroke="currentColor" stroke-width="1.8" stroke-linecap="round" d="M6,3 L6,6.6 M6,8.6 L6,8.7"/></svg>',
	close: ICON_SVG + '<path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" d="M2.5,2.5 L9.5,9.5 M9.5,2.5 L2.5,9.5"/></svg>'
};


// Settings dialog, see settingsDialogOpened()
// Same colors as the popup (steel blue border, white, light blue). The rows are a grid: label, field,
// then the help of the row under the field, all the helps being shown or hidden together by the
// Help button of the title (not on mouse over: the fields would move under the mouse). The width
// and height set inline by GM_config are overridden.
// The dialog is anchored at the top of the window, centered in width, and never higher than the
// window: it scrolls inside, so that its bottom (Save) is always reachable, even in a low window.
// Its width follows the screen: half of the window, between 640 and 960 px (95 % at most, set by GM_config).
var SETTINGS_CSS = "#GM_config { width: clamp(640px, 50vw, 960px) !important; height: auto !important; max-height: calc(100% - 20px) !important;"
	+ " top: 10px !important; left: 0 !important; right: 0 !important; margin: 0 auto !important; overflow-y: auto !important;"
	+ " border: 2px solid #2b5c8a !important; box-shadow: 0 6px 24px rgba(0,0,0,.35); border-radius: 4px; }"
	+ "\n#GM_config * { font-family: Arial, Tahoma, sans-serif; }"
	// the dialog is built inside the page (GM_config): the text styles of the page must not reach it. A page
	// that centers its text would otherwise center the helps and the servers. The buttons keep their text
	// centered, and the rules of the dialog that align something on purpose (labels) are more specific.
	+ "\n#GM_config, #GM_config *:not(button) { text-align: left; }"
	+ "\n#GM_config, #GM_config * { line-height: normal; letter-spacing: normal; word-spacing: normal;"
	+ " text-transform: none; text-indent: 0; font-style: normal; }"
	+ "\n#GM_config_wrapper { padding: 0 0 6px; }"
	+ "\n#GM_config .config_header { font-size: 15px; font-weight: bold; padding: 10px 14px; text-align: left; background: #e8f1fb;"	// as the toolbars of the popup
	+ " border-bottom: 1px solid #ccd; display: flex; align-items: center; gap: 6px; }"
	// at the right of the title: the [?] of the inline help, pressed while the helps are shown, and the Close icon,
	// drawn and sized as the icons of the popup (see addHelpButton())
	+ "\n#GM_config .config_header button { width: 22px; height: 22px; margin: 0; padding: 0; box-sizing: border-box;"
	+ " display: inline-flex; align-items: center; justify-content: center; color: #333333; }"
	+ "\n#GM_config .config_header button svg { display: block; }"
	+ "\n#GM_config .helpbtn { margin-left: auto !important; }"
	+ "\n#GM_config .helpbtn[aria-pressed=\"true\"] { background: #d6e6f7; border: 1px solid #0075ff; border-radius: 2px; color: #0075ff; }"
	+ "\n#GM_config #GM_config_closeIcon { color: #d00000; }"
	+ "\n#GM_config .section_header_holder { margin: 10px 14px 0; }"
	+ "\n#GM_config .section_header { background: #e4eef7; color: #2b5c8a; border: none; border-left: 4px solid #2b5c8a;"
	+ " font-size: 13px; font-weight: bold; padding: 4px 8px; text-align: left; }"
	+ "\n#GM_config .section_desc { background: none; border: none; color: #555; text-align: left;"
	+ " margin: 3px 0 4px 12px; }"
	+ "\n#GM_config .config_var { display: grid; grid-template-columns: 170px auto 1fr; align-items: center;"
	+ " column-gap: 8px; margin: 0; padding: 4px 6px; }"
	+ "\n#GM_config .config_var:hover, #GM_config .config_var:focus-within { background: #f3f8fd; }"
	+ "\n#GM_config .field_label { font-size: 12px; font-weight: bold; text-align: right; margin: 0; }"
	+ "\n#GM_config .config_var span { font-size: 12px; }"
	+ "\n#GM_config input[type=text], #GM_config input[type=password], #GM_config select { font-size: 12px;"
	+ " padding: 3px 5px; border: 1px solid #99a; border-radius: 3px; }"
	+ "\n#GM_config input:focus, #GM_config select:focus { outline: 2px solid #00f; outline-offset: 0; }"
	// the long values (address, categories, filter) take the whole width of the column, as their help
	+ "\n#GM_config #GM_config_field_emuleUrl, #GM_config #GM_config_field_emuleCat, #GM_config #GM_config_field_checkFilter {"
	+ " grid-column: 2 / -1; width: 100%; box-sizing: border-box; }"
	// a regular expression, and the code in the helps, in a monospace font
	+ "\n#GM_config #GM_config_field_checkFilter, #GM_config .help code { font-family: Consolas, \"Courier New\", monospace; }"
	+ "\n#GM_config .pwdbox { grid-column: 2 / -1; display: flex; column-gap: 8px; }"	// password and its Show button
	+ "\n#GM_config .pwdbox input { flex: 1; min-width: 0; }"
	+ "\n#GM_config .reveal { justify-self: start; font-size: 11px; padding: 2px 8px; }"
	+ "\n#GM_config .help { display: none; grid-column: 2 / -1; font-size: 11px; color: #123; white-space: pre-line;"
	+ " background: #e4eef7; border-left: 3px solid #2b5c8a; padding: 5px 8px; margin: 4px 0 2px; }"
	+ "\n#GM_config.helps .help { display: block; }"		// all the helps shown by the Help button
	+ "\n#GM_config .error { grid-column: 2 / -1; font-size: 11px; font-weight: bold; color: #c00; margin: 3px 0 0; }"
	+ "\n#GM_config input.invalid { border-color: #c00; outline: 1px solid #c00; }"
	+ "\n#GM_config_buttons_holder { margin: 8px 14px 0; border-top: 1px solid #ccd; padding-top: 6px;"
	+ " display: flex; flex-wrap: wrap; align-items: center; }"
	+ "\n#GM_config .saveclose_buttons { margin: 4px 0 4px 8px; padding: 4px 16px; }"
	// Save stands out, as Download and OK in the popup
	+ "\n#GM_config #GM_config_saveBtn { border: 2px solid #0075ff; border-radius: 3px; background: #ffffff; color: #000000; padding: 3px 15px; }"
	+ "\n#GM_config #GM_config_saveBtn:hover { background: #f3f8fd; }"
	+ "\n#GM_config .reset_holder { display: none; }"		// replaced by the Reset button, see addResetButton()
	// the links to the repository, at the bottom (see addFooter())
	+ "\n#GM_config .footer { margin: 4px 14px 0; padding: 6px 0 2px; border-top: 1px solid #e3e8ef; font-size: 11px;"
	+ " display: flex; justify-content: space-between; }"
	+ "\n#GM_config .footer a { color: #2b5c8a; text-decoration: none; }"
	+ "\n#GM_config .footer a:hover { text-decoration: underline; }"
	+ "\n#GM_config .resetbtn { margin-right: auto; font-size: 12px; padding: 4px 12px; }"
	+ "\n#GM_config .notice { flex-basis: 100%; order: 3; font-size: 11px; color: #123; text-align: left;"
	+ " background: #fff8e1; border-left: 3px solid #f0a000; padding: 5px 8px; margin: 6px 0 0;"
	+ " display: flex; align-items: center; column-gap: 8px; }"
	// its Undo button: the style of Show, always on the right of the notice whatever the length of its text
	+ "\n#GM_config .notice button { font-size: 11px; margin: 0 0 0 auto; padding: 2px 8px; white-space: nowrap; }"
	+ "\n#GM_config .config_var.changed { background: #fff8e1; }"
	+ "\n#GM_config .config_var.changed .field_label::after { content: ' \\2022'; color: #f0a000; }"
	// the servers as a list (see setupServers()): the select of GM_config stays hidden
	+ "\n#GM_config #GM_config_ed2kDlMethod_var { grid-template-columns: 1fr; }"
	+ "\n#GM_config #GM_config_ed2kDlMethod_var > label, #GM_config #GM_config_ed2kDlMethod_var > select { display: none; }"
	+ "\n#GM_config #GM_config_ed2kDlMethod_var > .help, #GM_config #GM_config_ed2kDlMethod_var > .error { grid-column: 1 / -1; }"
	+ "\n#GM_config .slist { border: 1px solid #b8c6d6; border-radius: 4px; }"
	+ "\n#GM_config .srow { display: grid; grid-template-columns: 26px 150px 150px 1fr auto; align-items: center;"
	+ " column-gap: 6px; padding: 5px 8px; border-top: 1px solid #e3e8ef; font-size: 12px; }"
	+ "\n#GM_config .srow:first-child { border-top: none; }"
	+ "\n#GM_config .srow.sel { background: #e4eef7; }"
	+ "\n#GM_config .srow label { font-weight: bold; cursor: pointer; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }"
	+ "\n#GM_config .srow .method { color: #2b5c8a; font-size: 11px; background: #eef3f9; border: 1px solid #c9d6e6;"
	+ " border-radius: 10px; padding: 1px 7px; justify-self: start; white-space: nowrap;"
	+ " max-width: 100%; box-sizing: border-box; overflow: hidden; text-overflow: ellipsis; }"	// a long name cut by "..."
	// a deleted server, in its place; its Undo on the right edge of the fields and their buttons (Show)
	+ "\n#GM_config .slist .notice { margin: 0; border-top: 1px solid #e3e8ef; padding-right: 6px; }"
	+ "\n#GM_config .srow .sum { color: #555; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }"
	+ "\n#GM_config .srow .sum.none { color: #999; font-style: italic; }"
	+ "\n#GM_config .srow .acts button { background: none; border: none; color: #2b5c8a; font-size: 11px;"
	+ " text-decoration: underline; cursor: pointer; padding: 0 2px; margin-left: 6px; }"
	+ "\n#GM_config .srow .acts button.del { color: #a33; }"
	+ "\n#GM_config .srow .acts button:disabled { color: #999999; text-decoration: none; cursor: default; }"
	// Local disabled (I-14): its row grayed out, but its Enable link
	+ "\n#GM_config .srow.off > :not(.acts) { opacity: 0.45; }"
	+ "\n#GM_config .srow.off label { cursor: default; }"
	+ "\n#GM_config .sfields { background: #f7f9fc; border-top: 1px solid #e3e8ef; padding: 4px 0 6px; }"
	+ "\n#GM_config .sadd { border-top: 1px solid #e3e8ef; padding: 6px 8px; }"
	+ "\n#GM_config .sadd button { font-size: 12px; padding: 3px 10px; }"
	+ "\n#GM_config #GM_config_field_serverName { grid-column: 2 / -1; width: 100%; box-sizing: border-box; }"
	// Test and Import (emule, amule, amuleapi), see addApiButtons(): the style of Show. Import and the Undo of an
	// import share a column on the right of the Category field and of the result of the import.
	+ "\n#GM_config .apibtn { font-size: 11px; padding: 2px 8px; white-space: nowrap; }"
	+ "\n#GM_config .sfields.notest #GM_config_testBtn, #GM_config .sfields.noimport #GM_config_importBtn { display: none; }"
	+ "\n#GM_config .catbox { grid-column: 2 / -1; display: grid; grid-template-columns: 1fr auto; column-gap: 8px;"
	+ " row-gap: 4px; align-items: center; }"
	+ "\n#GM_config .sfields.noimport .catbox { grid-template-columns: 1fr; }"
	+ "\n#GM_config .catbox #GM_config_field_emuleCat { grid-column: 1; min-width: 0; }"
	+ "\n#GM_config #GM_config_emuleCat_var > .field_label { align-self: start; margin-top: 4px; }"
	// their result, under the field: green, orange (connected, but the links would be refused) or red
	+ "\n#GM_config .apistatus { grid-column: 2 / -1; font-size: 11px; margin: 4px 0 0; padding: 3px 8px; border-radius: 3px; }"
	+ "\n#GM_config .catbox .apistatus { grid-column: 1; margin: 0; align-self: stretch; }"
	+ "\n#GM_config .catbox .apistatus.wide { grid-column: 1 / -1; }"
	+ "\n#GM_config .apistatus.ok { color: #1d6b2a; background: #e8f5ea; border-left: 3px solid #2e8b3d; }"
	+ "\n#GM_config .apistatus.warn { color: #7a4b00; background: #fff4e0; border-left: 3px solid #f0a000; }"
	+ "\n#GM_config .apistatus.ko { color: #a00; background: #fdecec; border-left: 3px solid #c00; }";

// -------------------------------------------------------------------------
// The texts: one table per language (I-7), read by tr(); English is the reference, a text missing
// in another language is taken from it. {name} is replaced by a value; in a label, & marks the letter
// of its keyboard shortcut, underlined when the label holds it (trLabel())
// -------------------------------------------------------------------------

var TEXTS = {
	en: {
		// the menu of the userscript manager
		menuSettings: 'Emule Linker: Settings',
		menuHelp: 'Emule Linker: Help',
		menuDownload: 'Emule Linker: Download',
		menuCheckAll: 'Emule Linker: Check or uncheck all links',
		menuMode: 'Emule Linker: Change mode (edit/normal)',
		menuView: 'Emule Linker: Switch view (maximized/minimized/closed)',
		menuClose: 'Emule Linker: Close Popup',
		menuOpen: 'Emule Linker: Open Popup',
		menuDebug: 'Emule Linker: Toggle debug traces',
		debugOn: 'Emule Linker: debug traces on (see the browser console)',
		debugOff: 'Emule Linker: debug traces off',
		// the popup: its toolbars (& marks the letter of a shortcut, underlined when the label holds it), its list
		checkAllTitle: 'Check or uncheck every link (Ctrl+Alt+A)',
		editMode: 'Edit &mode',
		editModeTitle: 'Edit the links as text (Ctrl+Alt+M)',
		normalMode: 'Normal &mode',
		normalModeTitle: 'Back to the list (Ctrl+Alt+M)',
		download: '&Download',
		downloadTitle: 'Download the checked links (Ctrl+Alt+D)',
		settingsTitle: 'Settings (Ctrl+Alt+S)',
		helpTitle: 'Help (Ctrl+Alt+H)',
		minimizeTitle: 'Minimize (Ctrl+Alt+X)',
		maximizeTitle: 'Maximize (Ctrl+Alt+X)',
		closeTitle: 'Close (Ctrl+Alt+C)',
		categoryTip: 'Category: {name}\nThe category of the downloads, for this page only',
		serverTip: 'Server: {name}\nThe server that receives the links, for this page only',
		local: 'Local',
		countTitle: '{count} link(s) checked out of {total}',
		countTextTitle: '{count} link(s) in the text, sent by Download',
		filteredTitle: 'Not checked by default: its name does not match the filter of the settings',
		filterFlags: 'The flags g and y are not allowed: each test would depend on the previous one',
		filterInvalid: 'Not a valid regular expression: {reason}',
		// the message shown when the popup is closed (I-3)
		closedTitle: 'Emule Linker \u2014 Popup closed',
		closedText: 'You have closed the popup on this page. To open it again:<ul><li>press <b>Ctrl+Alt+O</b>, or</li><li>press <b>Ctrl+Alt+X</b>, or</li><li>choose <b>Open Popup</b> in the menu of {manager}.</li></ul>To keep the popup closed on every page, choose <b>Closed</b> as the <b>Default popup view</b> in the settings, or restrict this script to some sites (see the {link}installation guide{end}).',
		dontDisplay: 'Don\'t display again',
		closeMessageTitle: 'Close this message (Escape)',
		statusCloseTitle: 'Close this message',
		ok: 'OK',
		userscriptManager: 'your userscript manager',
		// the help (I-5)
		help: 'Help',
		helpCloseTitle: 'Close the help (Escape)',
		helpIntro: 'Emule Linker lists the ed2k links of the page in the popup, and sends the ones you check to your ed2k client.',
		helpToolbars: 'The toolbars',
		helpCheckAll: 'Checks or unchecks every link',
		helpCount: 'The links that Download sends, out of the links of the page',
		helpServerChip: 'Server ▾',
		helpServer: 'The server that receives the links, for this page only (the list appears when at least two choices are available)',
		helpCategoryChip: 'Category ▾',
		helpCategory: 'The category of the downloads, for this page only',
		helpDownload: 'Sends the checked links to the server',
		helpEditMode: 'Shows the links as text, to edit them; Normal mode goes back to the list',
		helpSettings: 'Opens the settings: your servers, the look of the popup',
		helpHelp: 'Shows or hides this help',
		helpView: 'Keeps only the top toolbar / shows the whole popup again',
		helpClose: 'Closes the popup on this page; Ctrl+Alt+O opens it again',
		helpList: 'The list of the links',
		helpListClick: 'Click a file name to download this file only (to the chosen server and category).',
		helpListGray: 'Links in gray are not checked by default: see <b>Links checked by default</b> in the settings.',
		helpListShadow: 'A shadow on an edge of the list tells that more links are hidden beyond it.',
		helpNext: 'The popup on the next pages',
		helpNextView: 'Each page opens the popup in the <b>Default popup view</b> of the settings: Maximized, Minimized or Closed.',
		helpNextMenu: 'Every command is also in the menu of {manager}, under <b>Emule Linker</b>.',
		helpDoc: 'Full documentation on GitHub',
		helpIssues: 'Report a problem',
		// the sending, and the answers of the clients ({client}: eMule, aMule, MLDonkey)
		noLink: 'No ed2k link to send',
		pleaseWait: 'Please wait',
		alert: 'Emule Linker: {message}',
		notAnswered: '{client} has not answered within {seconds} s: the links may still be added, check {client}',
		notReached: '{client} can not be reached at {url}',
		linksAdded: '{count} link(s) added to {client}',
		linksAddedRefused: '{added} link(s) added to {client}, {refused} refused{why}',
		refusedPassword: '{client} refused the password',
		emuleRefusedLinks: 'eMule refused the links{why}',
		emuleNotUnderstood: 'Links sent, but the answer of eMule is not understood: check its transfer list',
		amuleListUnread: 'Links sent, but the transfer list of aMule could not be read: check it',
		amuleFound: '{found} of {count} link(s) found in the transfer list of aMule: check it',
		noAmuleWeb: 'No aMule 2.x web interface at {url}',
		mldonkeyRefused: 'MLDonkey refused the user or the password',
		noMldonkey: 'No MLDonkey web interface at {url}',
		noEmule: 'No eMule web interface at {url}',
		mldonkeyNotUnderstood: 'Links sent, but the answer of MLDonkey is not understood: check its downloads',
		amuleAdmin: 'This password can not add downloads: the admin password of aMule is needed',
		noAmuleApi: 'No aMule API at {url} (aMule 3.1 or later is needed)',
		amuleTooMany: 'Too many failed logins to aMule{retry}',
		retryIn: ', retry in {seconds} s',
		amuleNoCore: 'aMule is not connected to its core (amuled)',
		amuleHttp: 'aMule answered HTTP {status}{detail}',
		// the settings dialog
		settings: 'Settings',
		save: 'Save',
		saveTitle: 'Save settings',
		close: 'Close',
		closeWindowTitle: 'Close window',
		closeDialogTitle: 'Close (Escape)',
		helpShow: 'Display inline help',
		helpHide: 'Hide inline help',
		reset: '\u21ba Reset to defaults',
		resetTitle: 'Set every setting back to its default value (not saved until you press Save)',
		resetNone: 'Every setting already has its default value.',
		resetOne: '1 setting set back to its default value (highlighted), not saved yet.',
		resetMany: '{count} settings set back to their default value (highlighted), not saved yet.',
		undo: '\u21b6 Undo',
		reportProblem: 'Report a problem ↗',
		repository: 'Emule Linker on GitHub ↗',
		serversHelp: 'The checked server receives the links: Local, or one of your servers.\nEach server has a name, a download method and its own settings, shown by Edit: several servers of the same kind are possible.\nDelete removes a server, + Add a server adds one. Save stores all of them.\nDisable leaves Local out, for a system without an ed2k application: it is no longer offered in the popup. Enable offers it again.',
		serverNameLabel: 'Name',
		serverNameHelp: 'A name to tell your servers apart, required and different for each server.',
		addServer: '+ Add a server',
		newServer: 'New server',
		newServerN: 'New server {n}',
		serverDeleted: 'Server "{name}" deleted, not saved yet.',
		localBadge: 'your system default',
		nothingToConfigure: 'nothing to configure',
		edit: 'Edit',
		delete: 'Delete',
		enable: 'Enable',
		disable: 'Disable',
		enableTitle: 'Offer Local again among the servers that receive the links',
		disableTitle: 'Leave Local out of the servers that receive the links',
		disableBlocked: 'Check another server first',
		show: 'Show',
		hide: 'Hide',
		test: 'Test',
		testTitle: 'Test the server URL and the password',
		testing: 'Test…',
		import: 'Import',
		importTitle: 'Fill the field with the categories of eMule or aMule',
		importing: 'Import…',
		notAnsweredShort: '{client} has not answered within {seconds} s',
		connectedTo: 'Connected to {name}.',
		connectedNotAdmin: 'Connected to {name}, but this password can not add downloads: the admin password of aMule is needed',
		connectedNoCore: 'Connected to {name}, but aMule is not connected to its core (amuled): the links would be refused',
		importAlready: 'The field already holds the categories of {client}.',
		importNone: '{client} has no category: Default=0 is used.',
		importOne: '{count} category imported from {client}{parts}.',
		importMany: '{count} categories imported from {client}{parts}.',
		importNew: '{count} new ({names})',
		importRemoved: '{count} removed ({names})',
		importStays: '{name} stays the default (*).',
		importIsNow: '{name} is now the default (*).',
		categoryN: 'Category {index}',
		nameRequired: 'A name is required',
		nameTaken: 'Another server already has this name',
		serverUrlError: 'An address starting with http:// or https:// is expected, e.g. http://127.0.0.1:4711/',
		categoryError: 'No valid category: write them as name=value, separated by ; (e.g. *default=0;Video=2)',
		wholeNumber: 'A whole number is expected',
		wholeAtLeast1: 'A whole number, at least 1, is expected',
		heightMin: 'At least 40 px, or 0 for unlimited: a smaller popup would hide its Settings button',
		widthMin: 'At least 100 px, or 0 for unlimited: a smaller popup would hide its Settings button',
		alertCategory: 'No valid category: the default value (*default=0) is used instead.',
		alertHeight: 'A maximum popup height between 1 and 39 px would hide the Settings button: 0 (unlimited) is used instead.',
		alertWidth: 'A maximum popup width between 1 and 99 px would hide the Settings button: 0 (unlimited) is used instead.',
		// the fields of the settings dialog: {id}Label, {id}Help, {id}.{option}
		section0: 'General',
		section0Help: 'How the script behaves on every page',
		languageLabel: 'Language',
		languageHelp: 'The language of the script: the popup, its messages, its help and this dialog.\nBrowser language: French when the browser is in French, English otherwise.',
		'language.browser': 'Browser language (default)',
		'language.en': 'English',
		'language.fr': 'Français',
		popupViewLabel: 'Default popup view',
		popupViewHelp: 'The view of the popup when a page with ed2k links opens. What you change in the popup applies to this page only: the next page opens in this view again.\nMaximized: the list of the links (default).\nMinimized: only the top toolbar, with the number of links.\nClosed: no popup. The popup, and this dialog too, can then be opened only with the keyboard shortcuts (`Ctrl+Alt+O` or `Ctrl+Alt+X`: the popup, `Ctrl+Alt+S`: this dialog) or the menu of Tampermonkey or Violentmonkey (Emule Linker: Open Popup, Emule Linker: Settings).',
		'popupView.maximized': 'Maximized (default)',
		'popupView.minimized': 'Minimized',
		'popupView.closed': 'Closed',
		closeMessageLabel: 'Show a message when the popup is closed',
		closeMessageHelp: 'When you close the popup (its ✕ button, `Ctrl+Alt+C` or the menu), a message tells how to open it again.\nIts box "Don\'t display again" unchecks this setting.',
		section1: 'Servers',
		section1Help: 'Where the ed2k links are sent: the servers you use, and the one that receives the links',
		ed2kDlMethodLabel: 'Ed2k Download Method',
		ed2kDlMethodHelp: 'How the links are sent:\nLocal: to the application of your system that handles ed2k links (default)\neMule (web): to eMule, on this computer or another one, through its web interface\naMule 3.x (amuleapi): to aMule 3.1 or later, through its REST API\naMule 2.x (amuleweb): to aMule 2.x, through its web interface\nMLDonkey (web): to MLDonkey, through its web interface\nCustom: posted to your own server',
		'ed2kDlMethod.local': 'Local (your system default)',
		'ed2kDlMethod.emule': 'eMule (web)',
		'ed2kDlMethod.amuleapi': 'aMule 3.x (amuleapi)',
		'ed2kDlMethod.amule': 'aMule 2.x (amuleweb)',
		'ed2kDlMethod.mldonkey': 'MLDonkey (web)',
		'ed2kDlMethod.custom': 'Custom (post to your own server)',
		emuleUrlLabel: 'Server URL',
		emuleUrlHelp: 'The address of the web interface of eMule, aMule or MLDonkey, or of your own server.\nFor instance `http://127.0.0.1:4711/` (a final `/` is added when missing).',
		emuleUserLabel: 'User',
		emuleUserHelp: 'The user of the web interface of MLDonkey (`admin` by default).',
		emulePwdLabel: 'Password',
		emulePwdHelp: 'The password of the web interface. Optional: leave it empty if it has none.\nFor aMule 3.x, its admin password. Test (eMule, aMule, MLDonkey) checks the Server URL and the password, without saving them.',
		emuleCatLabel: 'Category',
		emuleCatHelp: 'The categories offered in the popup, as `name=value`, separated by `;`\nA `*` before a name makes it the default one.\neMule and aMule 3.x: the value is the number of the category (`0`: the default category), e.g. `*default=0;Video=2`\neMule and aMule: Import fills the field with their categories, in their order.\naMule 2.x: the value is the name of the category, e.g. `*Audio=audio;Video=Video` (a `;` in a name is written `\\;`)',
		section2: 'Popup',
		section2Help: 'How the popup is displayed, and the links it checks',
		showCategoriesLabel: 'Show the category list',
		showCategoriesHelp: 'Shows the list of the categories in the toolbars of the popup, to choose the category of the downloads of the page. It is grayed out when the server has fewer than two categories.\nUnchecked: the links are sent to the default category of the server.',
		showServerListLabel: 'Show the server list',
		showServerListHelp: 'Shows the list of the servers in the toolbars of the popup, to send the links of the page to another server: Local, then your servers. It is shown when it offers two choices at least, Local included. The server chosen applies to this page only.\nUnchecked: the links are sent to the server checked above.',
		popupCornerLabel: 'Popup position',
		popupCornerHelp: 'The corner of the window where the popup is shown.\nIt can be resized at the top left only: elsewhere, it keeps the size given by the maximum height and width below.',
		'popupCorner.top-left': 'Top left (default)',
		'popupCorner.top-right': 'Top right',
		'popupCorner.bottom-left': 'Bottom left',
		'popupCorner.bottom-right': 'Bottom right',
		popupScrollLabel: 'Popup scrolling',
		popupScrollHelp: 'Stays in view: the popup stays in its corner of the window when the page scrolls (default).\nScrolls with the page: it stays at its place in the page, and goes out of view when the page scrolls.\nAt the bottom of the window, the popup always stays in view: this choice is then grayed out.',
		'popupScroll.floating': 'Stays in view (default)',
		'popupScroll.static': 'Scrolls with the page',
		popupHeightLabel: 'Max Popup Height in px (0=unlimited)',
		popupHeightHelp: 'The maximum height of the popup, in pixels: at least 40, or 0 for unlimited.',
		popupWidthLabel: 'Max Popup Width in px (0=unlimited)',
		popupWidthHelp: 'The maximum width of the popup, in pixels: at least 100, or 0 for unlimited.',
		checkFilterLabel: 'Links checked by default',
		checkFilterHelp: 'A regular expression on the file name: the links whose name matches it are checked in the popup, the others are listed, unchecked. Empty: every link is checked.\nThe filter is case-sensitive. To make it case-insensitive: `/expression/i`.\nExamples:\n(Blacklist) Every file but the eMule collections: `/^(?!.*\\.emulecollection$)/i`\n(Whitelist) Only the cbz, cbr, rar and zip files: `/\\.(cbz|cbr|rar|zip)$/i`',
		section3: 'Edit box',
		section3Help: 'The size of the text box of the edit mode',
		editColLabel: 'Number of columns',
		editColHelp: 'The width of the edit box, in characters.',
		editRowLabel: 'Number of rows',
		editRowHelp: 'The height of the edit box, in lines.'
	},
	fr: {
		// le menu du gestionnaire de scripts
		menuSettings: 'Emule Linker : Réglages',
		menuHelp: 'Emule Linker : Aide',
		menuDownload: 'Emule Linker : Télécharger',
		menuCheckAll: 'Emule Linker : Cocher ou décocher tous les liens',
		menuMode: 'Emule Linker : Changer de mode (édition/normal)',
		menuView: 'Emule Linker : Changer de vue (agrandie/réduite/fermée)',
		menuClose: 'Emule Linker : Fermer la popup',
		menuOpen: 'Emule Linker : Ouvrir la popup',
		menuDebug: 'Emule Linker : Activer ou désactiver les traces de débogage',
		debugOn: 'Emule Linker : traces de débogage activées (voir la console du navigateur)',
		debugOff: 'Emule Linker : traces de débogage désactivées',
		// la popup : ses barres d'outils (& marque la lettre d'un raccourci), sa liste
		checkAllTitle: 'Cocher ou décocher tous les liens (Ctrl+Alt+A)',
		editMode: '&Mode édition',
		editModeTitle: 'Modifier les liens sous forme de texte (Ctrl+Alt+M)',
		normalMode: '&Mode normal',
		normalModeTitle: 'Revenir à la liste (Ctrl+Alt+M)',
		download: 'Télécharger',
		downloadTitle: 'Télécharger les liens cochés (Ctrl+Alt+D)',
		settingsTitle: 'Réglages (Ctrl+Alt+S)',
		helpTitle: 'Aide (Ctrl+Alt+H)',
		minimizeTitle: 'Réduire (Ctrl+Alt+X)',
		maximizeTitle: 'Agrandir (Ctrl+Alt+X)',
		closeTitle: 'Fermer (Ctrl+Alt+C)',
		categoryTip: 'Catégorie : {name}\nLa catégorie des téléchargements, pour cette page seulement',
		serverTip: 'Serveur : {name}\nLe serveur qui reçoit les liens, pour cette page seulement',
		local: 'Local',
		countTitle: '{count} lien(s) coché(s) sur {total}',
		countTextTitle: '{count} lien(s) dans le texte, envoyé(s) par Télécharger',
		filteredTitle: 'Non coché par défaut : son nom ne correspond pas au filtre des réglages',
		filterFlags: 'Les drapeaux g et y ne sont pas permis : chaque test dépendrait du précédent',
		filterInvalid: 'Expression régulière non valide : {reason}',
		// le message affiché à la fermeture de la popup (I-3)
		closedTitle: 'Emule Linker — Popup fermée',
		closedText: 'Vous avez fermé la popup sur cette page. Pour la rouvrir :<ul><li>appuyez sur <b>Ctrl+Alt+O</b>, ou</li><li>appuyez sur <b>Ctrl+Alt+X</b>, ou</li><li>choisissez <b>Ouvrir la popup</b> dans le menu de {manager}.</li></ul>Pour garder la popup fermée sur toutes les pages, choisissez <b>Fermée</b> comme <b>Vue par défaut de la popup</b> dans les réglages, ou limitez ce script à certains sites (voir le {link}guide d\'installation{end}).',
		dontDisplay: 'Ne plus afficher',
		closeMessageTitle: 'Fermer ce message (Échap)',
		statusCloseTitle: 'Fermer ce message',
		ok: 'OK',
		userscriptManager: 'votre gestionnaire de scripts',
		// l'aide (I-5)
		help: 'Aide',
		helpCloseTitle: 'Fermer l\'aide (Échap)',
		helpIntro: 'Emule Linker affiche les liens ed2k de la page dans la popup, et envoie ceux que vous cochez à votre client ed2k.',
		helpToolbars: 'Les barres d\'outils',
		helpCheckAll: 'Coche ou décoche tous les liens',
		helpCount: 'Le nombre de liens envoyés par Télécharger, sur le nombre de liens de la page',
		helpServerChip: 'Serveur ▾',
		helpServer: 'Le serveur qui reçoit les liens, pour cette page seulement (la liste apparaît quand au moins deux choix sont possibles)',
		helpCategoryChip: 'Catégorie ▾',
		helpCategory: 'La catégorie des téléchargements, pour cette page seulement',
		helpDownload: 'Envoie les liens cochés au serveur',
		helpEditMode: 'Affiche les liens sous forme de texte, pour les modifier ; Mode normal revient à la liste',
		helpSettings: 'Ouvre les réglages : vos serveurs, l\'aspect de la popup',
		helpHelp: 'Affiche ou masque cette aide',
		helpView: 'Ne garde que la barre du haut / réaffiche toute la popup',
		helpClose: 'Ferme la popup sur cette page ; Ctrl+Alt+O la rouvre',
		helpList: 'La liste des liens',
		helpListClick: 'Cliquez sur un nom de fichier pour télécharger ce fichier seulement (vers le serveur et la catégorie choisis).',
		helpListGray: 'Les liens en gris ne sont pas cochés par défaut : voir <b>Liens cochés par défaut</b> dans les réglages.',
		helpListShadow: 'Une ombre sur un bord de la liste indique que d\'autres liens sont cachés au-delà.',
		helpNext: 'La popup sur les pages suivantes',
		helpNextView: 'Chaque page ouvre la popup dans la <b>Vue par défaut de la popup</b> des réglages : Agrandie, Réduite ou Fermée.',
		helpNextMenu: 'Chaque commande est aussi dans le menu de {manager}, sous <b>Emule Linker</b>.',
		helpDoc: 'Documentation complète sur GitHub',
		helpIssues: 'Signaler un problème',
		// l'envoi, et les réponses des clients ({client} : eMule, aMule, MLDonkey)
		noLink: 'Aucun lien ed2k à envoyer',
		pleaseWait: 'Veuillez patienter',
		alert: 'Emule Linker : {message}',
		notAnswered: '{client} n\'a pas répondu dans les {seconds} s : les liens peuvent encore être ajoutés, vérifiez {client}',
		notReached: '{client} est injoignable à l\'adresse {url}',
		linksAdded: '{count} lien(s) ajouté(s) à {client}',
		linksAddedRefused: '{added} lien(s) ajouté(s) à {client}, {refused} refusé(s){why}',
		refusedPassword: '{client} a refusé le mot de passe',
		emuleRefusedLinks: 'eMule a refusé les liens{why}',
		emuleNotUnderstood: 'Liens envoyés, mais la réponse d\'eMule n\'est pas comprise : vérifiez sa liste de transferts',
		amuleListUnread: 'Liens envoyés, mais la liste de transferts d\'aMule n\'a pas pu être lue : vérifiez-la',
		amuleFound: '{found} lien(s) sur {count} trouvé(s) dans la liste de transferts d\'aMule : vérifiez-la',
		noAmuleWeb: 'Aucune interface web d\'aMule 2.x à l\'adresse {url}',
		mldonkeyRefused: 'MLDonkey a refusé l\'utilisateur ou le mot de passe',
		noMldonkey: 'Aucune interface web de MLDonkey à l\'adresse {url}',
		noEmule: 'Aucune interface web d\'eMule à l\'adresse {url}',
		mldonkeyNotUnderstood: 'Liens envoyés, mais la réponse de MLDonkey n\'est pas comprise : vérifiez ses téléchargements',
		amuleAdmin: 'Ce mot de passe ne peut pas ajouter de téléchargements : il faut le mot de passe d\'administration d\'aMule',
		noAmuleApi: 'Aucune API aMule à l\'adresse {url} (aMule 3.1 ou plus récent est nécessaire)',
		amuleTooMany: 'Trop d\'échecs de connexion à aMule{retry}',
		retryIn: ', réessayez dans {seconds} s',
		amuleNoCore: 'aMule n\'est pas connecté à son noyau (amuled)',
		amuleHttp: 'aMule a répondu HTTP {status}{detail}',
		// les réglages
		settings: 'Réglages',
		save: 'Enregistrer',
		saveTitle: 'Enregistrer les réglages',
		close: 'Fermer',
		closeWindowTitle: 'Fermer les réglages',
		closeDialogTitle: 'Fermer (Échap)',
		helpShow: 'Afficher l\'aide des champs',
		helpHide: 'Masquer l\'aide des champs',
		reset: '↺ Valeurs par défaut',
		resetTitle: 'Remettre chaque réglage à sa valeur par défaut (rien n\'est enregistré avant Enregistrer)',
		resetNone: 'Chaque réglage a déjà sa valeur par défaut.',
		resetOne: '1 réglage remis à sa valeur par défaut (surligné), pas encore enregistré.',
		resetMany: '{count} réglages remis à leur valeur par défaut (surlignés), pas encore enregistrés.',
		undo: '↶ Annuler',
		reportProblem: 'Signaler un problème ↗',
		repository: 'Emule Linker sur GitHub ↗',
		serversHelp: 'Le serveur coché reçoit les liens : Local, ou l\'un de vos serveurs.\nChaque serveur a un nom, une méthode de téléchargement et ses propres réglages, affichés par Modifier : plusieurs serveurs du même type sont possibles.\nSupprimer retire un serveur, + Ajouter un serveur en ajoute un. Enregistrer les conserve tous.\nDésactiver écarte Local, pour un système sans application ed2k : il n\'est plus proposé dans la popup. Activer le propose de nouveau.',
		serverNameLabel: 'Nom',
		serverNameHelp: 'Un nom pour distinguer vos serveurs, obligatoire et différent pour chaque serveur.',
		addServer: '+ Ajouter un serveur',
		newServer: 'Nouveau serveur',
		newServerN: 'Nouveau serveur {n}',
		serverDeleted: 'Serveur « {name} » supprimé, pas encore enregistré.',
		localBadge: 'défaut du système',
		nothingToConfigure: 'rien à configurer',
		edit: 'Modifier',
		delete: 'Supprimer',
		enable: 'Activer',
		disable: 'Désactiver',
		enableTitle: 'Proposer de nouveau Local parmi les serveurs qui reçoivent les liens',
		disableTitle: 'Écarter Local des serveurs qui reçoivent les liens',
		disableBlocked: 'Cochez d\'abord un autre serveur',
		show: 'Afficher',
		hide: 'Masquer',
		test: 'Tester',
		testTitle: 'Tester l\'adresse du serveur et le mot de passe',
		testing: 'Test…',
		import: 'Importer',
		importTitle: 'Remplir le champ avec les catégories d\'eMule ou d\'aMule',
		importing: 'Import…',
		notAnsweredShort: '{client} n\'a pas répondu dans les {seconds} s',
		connectedTo: 'Connecté à {name}.',
		connectedNotAdmin: 'Connecté à {name}, mais ce mot de passe ne peut pas ajouter de téléchargements : il faut le mot de passe d\'administration d\'aMule',
		connectedNoCore: 'Connecté à {name}, mais aMule n\'est pas connecté à son noyau (amuled) : les liens seraient refusés',
		importAlready: 'Le champ contient déjà les catégories de {client}.',
		importNone: '{client} n\'a aucune catégorie : Default=0 est utilisé.',
		importOne: '{count} catégorie importée de {client}{parts}.',
		importMany: '{count} catégories importées de {client}{parts}.',
		importNew: '{count} nouvelle(s) ({names})',
		importRemoved: '{count} retirée(s) ({names})',
		importStays: '{name} reste la catégorie par défaut (*).',
		importIsNow: '{name} est maintenant la catégorie par défaut (*).',
		categoryN: 'Catégorie {index}',
		nameRequired: 'Un nom est obligatoire',
		nameTaken: 'Un autre serveur a déjà ce nom',
		serverUrlError: 'Une adresse commençant par http:// ou https:// est attendue, par exemple http://127.0.0.1:4711/',
		categoryError: 'Aucune catégorie valide : écrivez-les sous la forme nom=valeur, séparées par ; (par exemple *default=0;Video=2)',
		wholeNumber: 'Un nombre entier est attendu',
		wholeAtLeast1: 'Un nombre entier, au moins 1, est attendu',
		heightMin: 'Au moins 40 px, ou 0 pour illimitée : une popup plus petite cacherait son bouton Réglages',
		widthMin: 'Au moins 100 px, ou 0 pour illimitée : une popup plus petite cacherait son bouton Réglages',
		alertCategory: 'Aucune catégorie valide : la valeur par défaut (*default=0) est utilisée.',
		alertHeight: 'Une hauteur maximale entre 1 et 39 px cacherait le bouton Réglages : 0 (illimitée) est utilisé à la place.',
		alertWidth: 'Une largeur maximale entre 1 et 99 px cacherait le bouton Réglages : 0 (illimitée) est utilisé à la place.',
		// les champs des réglages : {id}Label, {id}Help, {id}.{option}
		section0: 'Général',
		section0Help: 'Le comportement du script sur toutes les pages',
		languageLabel: 'Langue',
		languageHelp: 'La langue du script : la popup, ses messages, son aide et ces réglages.\nLangue du navigateur : le français quand le navigateur est en français, l\'anglais sinon.',
		'language.browser': 'Langue du navigateur (par défaut)',
		'language.en': 'English',
		'language.fr': 'Français',
		popupViewLabel: 'Vue par défaut de la popup',
		popupViewHelp: 'La vue de la popup à l\'ouverture d\'une page qui contient des liens ed2k. Ce que vous changez dans la popup ne vaut que pour cette page : la page suivante s\'ouvre de nouveau dans cette vue.\nAgrandie : la liste des liens (par défaut).\nRéduite : seulement la barre du haut, avec le nombre de liens.\nFermée : pas de popup. La popup, et ces réglages aussi, ne s\'ouvrent alors que par les raccourcis clavier (`Ctrl+Alt+O` ou `Ctrl+Alt+X` : la popup, `Ctrl+Alt+S` : ces réglages) ou le menu de Tampermonkey ou de Violentmonkey (Emule Linker : Ouvrir la popup, Emule Linker : Réglages).',
		'popupView.maximized': 'Agrandie (par défaut)',
		'popupView.minimized': 'Réduite',
		'popupView.closed': 'Fermée',
		closeMessageLabel: 'Afficher un message à la fermeture de la popup',
		closeMessageHelp: 'Quand vous fermez la popup (son bouton ✕, `Ctrl+Alt+C` ou le menu), un message indique comment la rouvrir.\nSa case « Ne plus afficher » décoche ce réglage.',
		section1: 'Serveurs',
		section1Help: 'Où les liens ed2k sont envoyés : les serveurs que vous utilisez, et celui qui reçoit les liens',
		ed2kDlMethodLabel: 'Méthode de téléchargement ed2k',
		ed2kDlMethodHelp: 'Comment les liens sont envoyés :\nLocal : à l\'application de votre système qui gère les liens ed2k (par défaut)\neMule (web) : à eMule, sur cet ordinateur ou un autre, par son interface web\naMule 3.x (amuleapi) : à aMule 3.1 ou plus récent, par son API REST\naMule 2.x (amuleweb) : à aMule 2.x, par son interface web\nMLDonkey (web) : à MLDonkey, par son interface web\nPersonnalisée : envoyés à votre propre serveur',
		'ed2kDlMethod.local': 'Local (défaut du système)',
		'ed2kDlMethod.emule': 'eMule (web)',
		'ed2kDlMethod.amuleapi': 'aMule 3.x (amuleapi)',
		'ed2kDlMethod.amule': 'aMule 2.x (amuleweb)',
		'ed2kDlMethod.mldonkey': 'MLDonkey (web)',
		'ed2kDlMethod.custom': 'Personnalisée (envoi à votre propre serveur)',
		emuleUrlLabel: 'Adresse du serveur',
		emuleUrlHelp: 'L\'adresse de l\'interface web d\'eMule, d\'aMule ou de MLDonkey, ou de votre propre serveur.\nPar exemple `http://127.0.0.1:4711/` (un `/` final est ajouté s\'il manque).',
		emuleUserLabel: 'Utilisateur',
		emuleUserHelp: 'L\'utilisateur de l\'interface web de MLDonkey (`admin` par défaut).',
		emulePwdLabel: 'Mot de passe',
		emulePwdHelp: 'Le mot de passe de l\'interface web. Facultatif : laissez-le vide s\'il n\'y en a pas.\nPour aMule 3.x, son mot de passe d\'administration. Tester (eMule, aMule, MLDonkey) vérifie l\'adresse du serveur et le mot de passe, sans les enregistrer.',
		emuleCatLabel: 'Catégorie',
		emuleCatHelp: 'Les catégories proposées dans la popup, sous la forme `nom=valeur`, séparées par `;`\nUne `*` devant un nom en fait la catégorie par défaut.\neMule et aMule 3.x : la valeur est le numéro de la catégorie (`0` : la catégorie par défaut), par exemple `*default=0;Video=2`\neMule et aMule : Importer remplit le champ avec leurs catégories, dans leur ordre.\naMule 2.x : la valeur est le nom de la catégorie, par exemple `*Audio=audio;Video=Video` (un `;` dans un nom s\'écrit `\\;`)',
		section2: 'Popup',
		section2Help: 'L\'affichage de la popup, et les liens qu\'elle coche',
		showCategoriesLabel: 'Afficher la liste des catégories',
		showCategoriesHelp: 'Affiche la liste des catégories dans les barres d\'outils de la popup, pour choisir la catégorie des téléchargements de la page. Elle est grisée quand le serveur a moins de deux catégories.\nDécoché : les liens sont envoyés dans la catégorie par défaut du serveur.',
		showServerListLabel: 'Afficher la liste des serveurs',
		showServerListHelp: 'Affiche la liste des serveurs dans les barres d\'outils de la popup, pour envoyer les liens de la page à un autre serveur : Local, puis vos serveurs. Elle apparaît quand elle offre au moins deux choix, Local compris. Le serveur choisi ne vaut que pour cette page.\nDécoché : les liens sont envoyés au serveur coché plus haut.',
		popupCornerLabel: 'Position de la popup',
		popupCornerHelp: 'Le coin de la fenêtre où la popup s\'affiche.\nElle ne se redimensionne qu\'en haut à gauche : ailleurs, elle garde la taille donnée par la hauteur et la largeur maximales ci-dessous.',
		'popupCorner.top-left': 'En haut à gauche (par défaut)',
		'popupCorner.top-right': 'En haut à droite',
		'popupCorner.bottom-left': 'En bas à gauche',
		'popupCorner.bottom-right': 'En bas à droite',
		popupScrollLabel: 'Défilement de la popup',
		popupScrollHelp: 'Reste visible : la popup reste dans son coin de la fenêtre quand la page défile (par défaut).\nDéfile avec la page : elle reste à sa place dans la page, et sort de la vue quand la page défile.\nEn bas de la fenêtre, la popup reste toujours visible : ce choix est alors grisé.',
		'popupScroll.floating': 'Reste visible (par défaut)',
		'popupScroll.static': 'Défile avec la page',
		popupHeightLabel: 'Hauteur max. de la popup en px (0=illimitée)',
		popupHeightHelp: 'La hauteur maximale de la popup, en pixels : au moins 40, ou 0 pour illimitée.',
		popupWidthLabel: 'Largeur max. de la popup en px (0=illimitée)',
		popupWidthHelp: 'La largeur maximale de la popup, en pixels : au moins 100, ou 0 pour illimitée.',
		checkFilterLabel: 'Liens cochés par défaut',
		checkFilterHelp: 'Une expression régulière sur le nom du fichier : les liens dont le nom y correspond sont cochés dans la popup, les autres sont listés, décochés. Vide : tous les liens sont cochés.\nLe filtre tient compte de la casse. Pour l\'ignorer : `/expression/i`.\nExemples :\n(Liste d\'exclusion) Tous les fichiers sauf les collections eMule : `/^(?!.*\\.emulecollection$)/i`\n(Liste d\'autorisation) Seulement les fichiers cbz, cbr, rar et zip : `/\\.(cbz|cbr|rar|zip)$/i`',
		section3: 'Zone d\'édition',
		section3Help: 'La taille de la zone de texte du mode édition',
		editColLabel: 'Nombre de colonnes',
		editColHelp: 'La largeur de la zone d\'édition, en caractères.',
		editRowLabel: 'Nombre de lignes',
		editRowHelp: 'La hauteur de la zone d\'édition, en lignes.'
	}
};


// -------------------------------------------------------------------------
// 								LIB
// -------------------------------------------------------------------------

/*
Copyright 2009-2010, GM_config Contributors
All rights reserved.

GM_config Contributors:
    Mike Medley <medleymind@gmail.com>
    Joe Simmons
    Izzy Soft
    Marti Martz

GM_config is distributed under the terms of the GNU Lesser General Public License.

    GM_config is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
*/

// The GM_config constructor
function GM_configStruct() {
  // call init() if settings were passed to constructor
  if (arguments.length) {
    GM_configInit(this, arguments);
  }
}

// This is the initializer function
function GM_configInit(config, args) {
  // Initialize instance variables
  if (typeof config.fields == "undefined") {
    config.fields = {};
    config.onInit = function() {};
    config.onOpen = function() {};
    config.onSave = function() {};
    config.onClose = function() {};
    config.onReset = function() {};
    config.isOpen = false;
    config.title = 'User Script Settings';
    config.css = {
      basic: "#GM_config * { font-family: arial,tahoma,myriad pro,sans-serif; }"
             + '\n' + "#GM_config { background: #FFF; }"
             + '\n' + "#GM_config input[type='radio'] { margin-right: 8px; }"
             + '\n' + "#GM_config .indent40 { margin-left: 40%; }"
             + '\n' + "#GM_config .field_label { font-weight: bold; font-size: 12px; margin-right: 6px; }"
             + '\n' + "#GM_config .block { display: block; }"
             + '\n' + "#GM_config .saveclose_buttons { margin: 16px 10px 10px; padding: 2px 12px; }"
             + '\n' + "#GM_config .reset, #GM_config .reset a,"
             + '\n' + "#GM_config_buttons_holder { text-align: right; color: #000; }"
             + '\n' + "#GM_config .config_header { font-size: 20pt; margin: 0; }"
             + '\n' + "#GM_config .config_desc, #GM_config .section_desc, #GM_config .reset { font-size: 9pt; }"
             + '\n' + "#GM_config .center { text-align: center; }"
             + '\n' + "#GM_config .section_header_holder { margin-top: 8px; }"
             + '\n' + "#GM_config .config_var { margin: 0 0 4px; }"
             + '\n' + "#GM_config .section_header { font-size: 13pt; background: #414141; color: #FFF;"
             + '\n' +  "border: 1px solid #000; margin: 0; }"
             + '\n' + "#GM_config .section_desc { font-size: 9pt; background: #EFEFEF; color: #575757;"
             + '\n' + "border: 1px solid #CCC; margin: 0 0 6px; }",
      stylish: ""
    };
  }

  // Set a default id
  if (typeof config.id == "undefined")
    config.id = 'GM_config';

  var settings = null;
  // If the id has changed we must modify the default style
  if (config.id != 'GM_config')
    config.css.basic = config.css.basic.replace(/#GM_config/gm, '#' + config.id);

  // Save the previous initialize callback
  var oldInitCb = config.onInit;

  // loop through GM_config.init() arguments
  for (var i = 0, l = args.length, arg; i < l; ++i) {
    arg = args[i];

    // An element to use as the config window
    if (typeof arg.appendChild == "function") {
      config.frame = arg;
      continue;
    }

    switch (typeof arg) {
      case 'object':
        for (var j in arg) { // could be a callback functions or settings object
          if (typeof arg[j] != "function") { // we are in the settings object
            settings = arg; // store settings object
            break; // leave the loop
          } // otherwise it must be a callback function
          config["on" + j.charAt(0).toUpperCase() + j.slice(1)] = arg[j];
        }
        break;
      case 'function': // passing a bare function is set to open callback
        config.onOpen = arg;
        break;
      case 'string': // could be custom CSS or the title string
        if (arg.indexOf('{') != -1 && arg.indexOf('}') != -1)
          config.css.stylish = arg;
        else
          config.title = arg;
        break;
    }
  }

  if (settings) {
    var stored = config.read(); // read the stored settings

    for (var id in settings) // for each setting create a field object
      config.fields[id] = new GM_configField(settings[id], stored[id], id);
  }

  // Prevent infinite loops
  if (config.onInit === oldInitCb)
    config.onInit = function() {};

  // Call the previous init() callback function
  oldInitCb();
}

GM_configStruct.prototype = {
  // Support old method of initalizing
  init: function() { GM_configInit(this, arguments); },

  // call GM_config.open() from your script to open the menu
  open: function () {
    // Die if the menu is already open on this page
    // You can have multiple instances but they can't be open at the same time
    var match = document.getElementById(this.id);
    if (match && (match.tagName == "IFRAME" || match.childNodes.length > 0)) return;

    // Sometimes "this" gets overwritten so create an alias
    var config = this;

    // Function to build the mighty config window :)
    function buildConfigWin (body, head) {
      var create = config.create,
          fields = config.fields,
          configId = config.id,
          bodyWrapper = create('div', {id: configId + '_wrapper'});

      // Append the style which is our default style plus the user style
      head.appendChild(
        create('style', {
        type: 'text/css',
        textContent: config.css.basic + config.css.stylish
      }));

      // Add header and title
      bodyWrapper.appendChild(create('div', {
        id: configId + '_header',
        className: 'config_header block center',
        innerHTML: config.title
      }));

      // Append elements
      var section = bodyWrapper,
          secNum = 0; // Section count

      // loop through fields
      for (var id in fields) {
        var field = fields[id].settings;

        if (field.section) { // the start of a new section
          section = bodyWrapper.appendChild(create('div', {
              className: 'section_header_holder',
              id: configId + '_section_' + secNum
            }));

          if (typeof field.section[0] == "string")
            section.appendChild(create('div', {
              className: 'section_header center',
              id: configId + '_section_header_' + secNum,
              innerHTML: field.section[0]
            }));

          if (typeof field.section[1] == "string")
            section.appendChild(create('p', {
              className: 'section_desc center',
              id: configId + '_section_desc_' + secNum,
              innerHTML: field.section[1]
            }));
          ++secNum;
        }

        // Create field elements and append to current section
        section.appendChild(fields[id].toNode(configId));
      }

      // Add save and close buttons
      bodyWrapper.appendChild(create('div',
        {id: configId + '_buttons_holder'},

        create('button', {
          id: configId + '_saveBtn',
          textContent: 'Save',
          title: 'Save settings',
          className: 'saveclose_buttons',
          onclick: function () { config.save() }
        }),

        create('button', {
          id: configId + '_closeBtn',
          textContent: 'Close',
          title: 'Close window',
          className: 'saveclose_buttons',
          onclick: function () { config.close() }
        }),

        create('div',
          {className: 'reset_holder block'},

          // Reset link
          create('a', {
            id: configId + '_resetLink',
            textContent: 'Reset to defaults',
            href: '#',
            title: 'Reset fields to default values',
            className: 'reset',
            onclick: function(e) { e.preventDefault(); config.reset() }
          })
      )));

      body.appendChild(bodyWrapper); // Paint everything to window at once
      config.center(); // Show and center iframe
      // Center frame on resize, while it is open (passed alone, center lost its "this" and failed)
      window.addEventListener('resize', function () { if (config.isOpen) config.center(); }, false);

      // Call the open() callback function
      config.onOpen(config.frame.contentDocument || config.frame.ownerDocument,
                    config.frame.contentWindow || window,
                    config.frame);

      // Close frame on window close
      window.addEventListener('beforeunload', function () {
          config.close();
      }, false);

      // Now that everything is loaded, make it visible
      config.frame.style.display = "block";
      config.isOpen = true;
    }

    // Either use the element passed to init() or create an iframe
    var defaultStyle = 'position:fixed; top:0; left:0; opacity:0; display:none; z-index:999;' +
                       'width:75%; height:75%; max-height:95%; max-width:95%;' +
                       'border:1px solid #000000; overflow:auto; bottom: auto;' +
                       'right: auto; margin: 0; padding: 0;';
    if (this.frame) {
      this.frame.id = this.id;
      this.frame.setAttribute('style', defaultStyle);
      buildConfigWin(this.frame, this.frame.ownerDocument.getElementsByTagName('head')[0]);
    } else {
      // Create frame
      document.body.appendChild((this.frame = this.create('iframe', {
        id: this.id,
        style: defaultStyle
      })));

      this.frame.src = 'about:blank'; // In WebKit src can't be set until it is added to the page
      // we wait for the iframe to load before we can modify it
      this.frame.addEventListener('load', function(e) {
          var frame = config.frame;
          var doc = frame.contentDocument || frame.contentWindow.document; // Chrome/Tampermonkey: contentDocument can be null
          var body = doc.getElementsByTagName('body')[0];
          body.id = config.id; // Allows for prefixing styles with "#GM_config"
          buildConfigWin(body, doc.getElementsByTagName('head')[0]);
      }, false);
    }
  },

  save: function () {
    var fields = this.fields;
    var id = null;
    for (id in fields)
      if (fields[id].toValue() === null) // invalid value encountered
        return;

    this.write();
    this.onSave(); // Call the save() callback function
  },

  close: function() {
    // If frame is an iframe then remove it
    if (this.frame.contentDocument) {
      this.remove(this.frame);
      this.frame = null;
    } else { // else wipe its content
      this.frame.innerHTML = "";
      this.frame.style.display = "none";
    }

    // Null out all the fields so we don't leak memory
    var fields = this.fields;
    for (var id in fields)
      fields[id].node = null;

    this.onClose(); //  Call the close() callback function
    this.isOpen = false;
  },

  set: function (name, val) {
    this.fields[name].value = val;
  },

  get: function (name) {
    return this.fields[name].value;
  },

  write: function (store, obj) {
    if (!obj) {
      var values = {},
          fields = this.fields;

      for (var id in fields) {
        var field = fields[id];
        if (field.settings.type != "button")
          values[id] = field.value;
      }
    }
    try {
      this.setValue(store || this.id, this.stringify(obj || values));
    } catch(e) {
      this.log("GM_config failed to save settings!");
    }
  },

  read: function (store) {
    try {
      var rval = this.parser(this.getValue(store || this.id, '{}'));
    } catch(e) {
      this.log("GM_config failed to read saved settings!");
      rval = {};
    }
    return rval;
  },

  reset: function () {
    var fields = this.fields,
        doc = this.frame.contentDocument || this.frame.ownerDocument,
        type;

    for (id in fields) {
      var node = fields[id].node,
          field = fields[id].settings,
          noDefault = typeof field['default'] == "undefined",
          type = field.type;

      switch (type) {
        case 'checkbox':
          node.checked = noDefault ? GM_configDefaultValue(type) : field['default'];
          break;
        case 'select':
          if (field['default']) {
            for (var i = 0, len = node.options.length; i < len; ++i)
              if (node.options[i].value == field['default'])
                node.selectedIndex = i;
          } else
            node.selectedIndex = 0;
          break;
        case 'radio':
          var radios = node.getElementsByTagName('input');
          for (var i = 0, len = radios.length; i < len; ++i)
            if (radios[i].value == field['default'])
              radios[i].checked = true;
          break;
        case 'button' :
          break;
        default:
          node.value = noDefault ? GM_configDefaultValue(type) : field['default'];
          break;
      }
    }

    this.onReset(); // Call the reset() callback function
  },

  create: function () {
    switch(arguments.length) {
      case 1:
        var A = document.createTextNode(arguments[0]);
        break;
      default:
        var A = document.createElement(arguments[0]),
            B = arguments[1];
        for (var b in B) {
          if (b.indexOf("on") == 0)
            A.addEventListener(b.substring(2), B[b], false);
          else if (",style,accesskey,id,name,src,href,which,for".indexOf("," +
                   b.toLowerCase()) != -1)
            A.setAttribute(b, B[b]);
          else
            A[b] = B[b];
        }
        for (var i = 2, len = arguments.length; i < len; ++i)
          A.appendChild(arguments[i]);
    }
    return A;
  },

  center: function () {
    var node = this.frame,
        style = node.style,
        beforeOpacity = style.opacity;
    if (style.display == 'none') style.opacity = '0';
    style.display = '';
    style.top = Math.floor((window.innerHeight / 2) - (node.offsetHeight / 2)) + 'px';
    style.left = Math.floor((window.innerWidth / 2) - (node.offsetWidth / 2)) + 'px';
    style.opacity = '1';
  },

  remove: function (el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }
};

// Define a bunch of API stuff
(function() {
  var isGM = typeof GM_getValue != 'undefined' &&
             typeof GM_getValue('a', 'b') != 'undefined',
      setValue, getValue, stringify, parser;

  // Define value storing and reading API
  if (!isGM) {
    setValue = function (name, value) {
      return localStorage.setItem(name, value);
    };
    getValue = function(name, def){
      var s = localStorage.getItem(name);
      return s == null ? def : s
    };

    // We only support JSON parser outside GM
    stringify = JSON.stringify;
    parser = JSON.parse;
  } else {
    setValue = GM_setValue;
    getValue = GM_getValue;
    stringify = typeof JSON == "undefined" ?
      function(obj) {
        return obj.toSource();
    } : JSON.stringify;
    parser = typeof JSON == "undefined" ?
      function(jsonData) {
        return (new Function('return ' + jsonData + ';'))();
    } : JSON.parse;
  }

  GM_configStruct.prototype.isGM = isGM;
  GM_configStruct.prototype.setValue = setValue;
  GM_configStruct.prototype.getValue = getValue;
  GM_configStruct.prototype.stringify = stringify;
  GM_configStruct.prototype.parser = parser;
  GM_configStruct.prototype.log = isGM ? GM_log : (window.opera ? opera.postError : console.log);
})();

function GM_configDefaultValue(type) {
  var value;

  if (type.indexOf('unsigned ') == 0)
    type = type.substring(9);

  switch (type) {
    case 'radio': case 'select':
      value = settings.options[0];
      break;
    case 'checkbox':
      value = false;
      break;
    case 'int': case 'integer':
    case 'float': case 'number':
      value = 0;
      break;
    default:
      value = '';
  }

  return value;
}

function GM_configField(settings, stored, id) {
  // Store the field's settings
  this.settings = settings;
  this.id = id;

  // if a setting was passed to init but wasn't stored then
  //      if a default value wasn't passed through init() then
  //      use default value for type
  //      else use the default value passed through init()
  // else use the stored value
  var value = typeof stored == "undefined" ?
                typeof settings['default'] == "undefined" ?
                  GM_configDefaultValue(settings.type)
                : settings['default']
              : stored;

  // Store the field's value
  this.value = value;
}

GM_configField.prototype = {
  create: GM_configStruct.prototype.create,

  node: null,

  toNode: function(configId) {
    var field = this.settings,
        value = this.value,
        options = field.options,
        id = this.id,
        create = this.create;

    var retNode = create('div', { className: 'config_var',
          id: configId + '_' + this.id + '_var',
          title: field.title || '' }),
        firstProp;

    // Retrieve the first prop
    for (var i in field) { firstProp = i; break; }

    var label = create('label', {
      innerHTML: field.label,
      id: configId + '_' + this.id +'_field_label',
      for: configId + '_field_' + this.id,
      className: 'field_label'
    });

    switch (field.type) {
      case 'textarea':
        retNode.appendChild((this.node = create('textarea', {
          id: configId + '_field_' + this.id,
          innerHTML: value,
          cols: (field.cols ? field.cols : 20),
          rows: (field.rows ? field.rows : 2)
        })));
        break;
      case 'radio':
        var wrap = create('div', {
          id: configId + '_field_' + id
        });
        this.node = wrap;

        for (var i = 0, len = options.length; i < len; ++i) {
          var radLabel = wrap.appendChild(create('span', {
            innerHTML: options[i]
          }));

          var rad = wrap.appendChild(create('input', {
            value: options[i],
            type: 'radio',
            name: id,
            checked: options[i] == value ? true : false
          }));

          if (firstProp == "options")
            wrap.insertBefore(radLabel, rad);
          else
            wrap.appendChild(radLabel);
        }

        retNode.appendChild(wrap);
        break;
      case 'select':
        var wrap = create('select', {
          id: configId + '_field_' + id
        });
        this.node = wrap;

        for (var i in options)
          wrap.appendChild(create('option', {
            innerHTML: options[i],
            value: i,
            selected: i == value ? true : false
            //selected: options[i] == value ? true : false	// bug: doesn't take into account the default value (https://github.com/sizzlemctwizzle/GM_config/issues/30)
          }));

        retNode.appendChild(wrap);
        break;
      case 'checkbox':
        retNode.appendChild((this.node = create('input', {
          id: configId + '_field_' + id,
          type: 'checkbox',
          value: value,
          checked: value
        })));
        break;
      case 'button':
        var btn = create('input', {
          id: configId + '_field_' + id,
          type: 'button',
          value: field.label,
          size: (field.size ? field.size : 25),
          title: field.title || ''
        });
        this.node = btn;

        if (field.script)
          btn.addEventListener('click', function () {
            var scr = field.script;
            typeof scr == 'function' ? setTimeout(scr, 0) : eval(scr);
          }, false);

        retNode.appendChild(btn);
        break;
      case 'hidden':
        retNode.appendChild((this.node = create('input', {
          id: configId + '_field_' + id,
          type: 'hidden',
          value: value
        })));
        break;
      default:
        // type = text, int, or float
        retNode.appendChild((this.node = create('input', {
          id: configId + '_field_' + id,
          type: 'text',
          value: value,
          size: (field.size ? field.size : 25)
        })));
    }

    // If the label is passed first, insert it before the field
    // else insert it after
    if (field.type != "hidden" &&
        field.type != "button" &&
        typeof field.label == "string") {
      if (firstProp == "label")
        retNode.insertBefore(label, retNode.firstChild);
      else
        retNode.appendChild(label);
    }

    return retNode;
  },

  toValue: function() {
    var node = this.node,
        field = this.settings,
        type = field.type,
        unsigned = false,
        rval;

    if (type.indexOf('unsigned ') == 0) {
      type = type.substring(9);
      unsigned = true;
    }

    switch (type) {
      case 'checkbox':
        this.value = node.checked;
        break;
      case 'select':
        this.value = node[node.selectedIndex].value;
        break;
      case 'radio':
        var radios = node.getElementsByTagName('input');
        for (var i = 0, len = radios.length; i < len; ++i)
          if (radios[i].checked)
            this.value = radios[i].value;
        break;
      case 'button':
        break;
      case 'int': case 'integer':
        var num = Number(node.value);
        var warn = 'Field labeled "' + field.label + '" expects a' +
          (unsigned ? ' positive ' : 'n ') + 'integer value';
        if (isNaN(num) || Math.ceil(num) != Math.floor(num) ||
            (unsigned && num < 0)) {
          alert(warn + '.');
          return null;
        }
        if (!this._checkNumberRange(num, warn))
          return null;
        this.value = num;
        break;
      case 'float': case 'number':
        var num = Number(node.value);
        var warn = 'Field labeled "' + field.label + '" expects a ' +
          (unsigned ? 'positive ' : '') + 'number value';
        if (isNaN(num) || (unsigned && num < 0)) {
          alert(warn + '.');
          return null;
        }
        if (!this._checkNumberRange(num, warn))
          return null;
        this.value = num;
        break;
      default:
        this.value = node.value;
        break;
    }

    return this.value; // value read successfully
  },

  _checkNumberRange: function(num, warn) {
    var field = this.settings;
    if (typeof field.min == "number" && num < field.min) {
      alert(warn + ' greater than or equal to ' + field.min + '.');
      return null;
    }

    if (typeof field.max == "number" && num > field.max) {
      alert(warn + ' less than or equal to ' + field.max + '.');
      return null;
    }
    return true;
  }
};

// Create default instance of GM_config
var GM_config = new GM_configStruct();



// -------------------------------------------------------------------------
// 								CODE
// -------------------------------------------------------------------------
// -------------------------------------------------------------------------
// State: the links of the page, the state of the popup, of the sending and of the settings dialog
// -------------------------------------------------------------------------
var eLinks=new Array();
var eFiles=new Array();
var eSizes=new Array();
var eNames=new Array();		// the decoded file names, without the suffix of a duplicate name (SF-5.7)
var checkRegExp = null;		// checkFilter read by saveConfig(): null checks every link (SF-5.7)

var textLanguage = scriptLanguage();	// the language of the texts (I-7), before the menus and the settings

var sendingBusy = false;	// a sending (aMule, eMule, MLDonkey) waits for its answer, see setSending()
var statusTimer = null;		// animation of the "Please wait" message, see showStatus()
var statusHide = null;		// the band of a success, removed after STATUS_DELAY, see showStatus()

// The fields that each download method uses: only them are shown in the settings of a server
var METHOD_FIELDS = {
	'local': [],
	'emule': ['emuleUrl', 'emulePwd', 'emuleCat'],
	'amuleapi': ['emuleUrl', 'emulePwd', 'emuleCat'],
	'amule': ['emuleUrl', 'emulePwd', 'emuleCat'],
	'mldonkey': ['emuleUrl', 'emuleUser', 'emulePwd'],
	'custom': ['emuleUrl', 'emuleCat']
};
var METHOD_SETTINGS = ['emuleUrl', 'emuleUser', 'emulePwd', 'emuleCat'];	// the settings of a server, besides its name and method
// The Test and Import buttons of the methods that have them (SF-8.16 to SF-8.18): the function of each
// one, called by testServer() and importCategories(); the buttons of the other methods are hidden
var TEST_ACTIONS = {'amuleapi': testAmuleApi, 'emule': testEmule, 'amule': testAmuleWeb, 'mldonkey': testMldonkey};
var IMPORT_ACTIONS = {'amuleapi': importAmuleCategories, 'emule': importEmuleCategories, 'amule': importAmuleWebCategories};
var dialogServers = null;	// in the settings dialog: {active: id or null for Local, list: [{id, name, method, emuleUrl, emuleUser, emulePwd, emuleCat}], localDisabled: Local left out (I-14)}
var dialogEdited = null;	// in the settings dialog: the id of the server whose settings are displayed, or null
var SERVER_URL = /^https?:\/\/[^\/\s]+/i;	// the Server URL of every method: http or https only

// The state of the popup on this page: 0 = closed, 1 = normal mode, 2 = edit mode. It is not stored:
// each page starts in the default view of the settings (popupView, SF-10)
var popupMode = 1;
// The popup is minimized on this page: only its top toolbar is shown (I-2), its list or its edit box
// and its bottom toolbar are hidden, and kept as they are
var popupMinimized = false;
// The servers that the popup offers (I-6): Local, then the servers of the settings, in their order
// (readServers()): the checked one with its settings, the others with their name and method only, their
// settings (their password included) read when one is chosen (useServer()). The one chosen applies to this page only (SF-6.9):
// each page starts on the server checked in the settings
var pageServers = [];
var pageServer = 'local';	// the id of the server chosen
// The place of the help once moved by the user on this page, {left, top} in the window, or null: placed
// beside the popup (placeHelp()). Not stored: each page places it automatically again
var helpPlace = null;

// -------------------------------------------------------------------------
// Startup: the menus, the settings read, the links found, the popup shown, the keyboard shortcuts
// -------------------------------------------------------------------------
// add Emule Linker settings dialog to Greasemonkey Menu
GM_registerMenuCommand(tr('menuSettings'), setButton, 's');
GM_registerMenuCommand(tr('menuHelp'), helpButton, 'h');
GM_registerMenuCommand(tr('menuDownload'), addButton, 'd');
GM_registerMenuCommand(tr('menuCheckAll'), checkAllButton, 'a');
GM_registerMenuCommand(tr('menuMode'), editButton, 'm');
GM_registerMenuCommand(tr('menuView'), cycleView, 'x');
GM_registerMenuCommand(tr('menuClose'), closeButton, 'c');
GM_registerMenuCommand(tr('menuOpen'), openButton, 'o');
GM_registerMenuCommand(tr('menuDebug'), debugButton, 't');

// configuring the settings dialog & display it if it is the first time
scriptConfig();

// the popup starts in the default view of the settings
popupMode = (popupView == 'closed') ? 0 : 1;

// if ed2k links, display the popup
var n = 0;
try {
	n = getEd2kLinks(eLinks, eFiles, eSizes, eNames);
}
catch (e) {
	// whatever happens during the scan, the keyboard shortcuts installed below
	// must stay available and the page must not be left half processed
	trace("getEd2kLinks() failed: " + e);
}
// the servers offered by the popup, the one checked in the settings chosen: only on a page with ed2k links,
// where the popup can show them
if (n>0) {
	readServers();
}
// with the default view Closed, only a shortcut or the menu opens the popup
if (n>0 && popupMode != 0) {
	createPopup(eLinks, eFiles, eSizes);
	if (popupView == 'minimized') {
		setMinimized(true);
	}
}

// Add key accelerator shortcuts
(function(d){
	d.addEventListener('keydown', function(e) {
		// pressed ctl+alt
		if (e.keyCode == 65 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { checkAllButton(); }	// ctl+alt+a
		if (e.keyCode == 68 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { addButton(); }	// ctl+alt+d
		if (e.keyCode == 67 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { closeButton(); } // ctl+alt+c
		if (e.keyCode == 77 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { editButton(); } // ctl+alt+m
		if (e.keyCode == 79 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { openButton(); } // ctl+alt+o
		if (e.keyCode == 83 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { setButton(); } // ctl+alt+s
		if (e.keyCode == 72 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { helpButton(); } // ctl+alt+h
		if (e.keyCode == 88 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { cycleView(); } // ctl+alt+x
	}, false);
})(document);

// -------------------------------------------------------------------------
// Detection: the ed2k links of the page (SF-1)
// -------------------------------------------------------------------------

/**
* Get ed2k links in the page
* @param links array to stock the ed2k links
* @param files array to stock the ed2k file names
* @param names array to stock the decoded file names, without the suffix of a duplicate name
* @return number of ed2k links
*/
function getEd2kLinks(links, files, sizes, names) {
	var allLinks, thisLink;
	var i, href, lnk, tlnk;
	var idx=0; // index of array

	trace("getEd2kLinks()");
	allLinks = document.evaluate(
		'//a[@href]',
		document,
		null,
		XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE,
		null);

	for (i=0; i<allLinks.snapshotLength; i++) {
		thisLink = allLinks.snapshotItem(i);

		// We read the raw attribute and not thisLink.href: when the scheme itself is
		// encoded (ed2k%3A%2F%2F...) the browser sees no scheme at all and resolves
		// the href as a relative url, which hides the ed2k prefix.
		href = thisLink.getAttribute('href');
		if (href == null) {
			continue;
		}
		href = href.trim();

		if (isEd2kLink(href)) {
			lnk = decodeEd2kLink(href);

			// ingore duplicates links
			if (links.indexOf(lnk)>=0) {
				continue;
			}

			// we split the ed2k link to retrieve the filename and size
			tlnk = lnk.split('|');

			// a malformed link must not break the scan of the whole page
			if (!isValidEd2kFile(tlnk)) {
				trace("getEd2kLinks() ignoring malformed ed2k link: " + lnk);
				continue;
			}

			// Store the size
			sizes[idx]=tlnk[3];

			// Check if the filename has been encoded twice
			if(tlnk[2].search(/%(?:[0-9A-Fa-f]{2})/)>-1) {
				// Sometimes names are encoded twice. Therefore we do it a second time. It may cause problems with filename using % followed by chars but it should be rare for Comics name.
				try {
					tlnk[2]=decodeURIComponent(tlnk[2]);
				}
				catch (e) {
					trace("Error in decoding filename a second time");
				}
			}

			// the name tested by the filter of the links checked by default (SF-5.7)
			names[idx]=tlnk[2];

			// check if the filename doesn't already exist
			if (files.indexOf(tlnk[2])>=0) {
				// storing the filename with a suffix
				tlnk[2] += ' (' + idx + ')';
			}

			// storing the filename and the link, both with the fixes applied
			files[idx]=tlnk[2];
			links[idx]=tlnk.join('|');

			idx++;
		}
	}

	trace("getEd2kLinks() ed2k links found: "+links.length);
	return links.length;
}

/**
* Check if a href is an ed2k link
* We accept the plain scheme (ed2k://) as well as links whose scheme has been
* url-encoded once or several times (ed2k%3A%2F%2F, ed2k%253A%252F%252F, ...)
* @param href the raw href attribute
* @return true if this is an ed2k link
*/
function isEd2kLink(href) {
	return /^ed2k(:|%(25)*3a)/i.test(href);
}

/**
* Decode an ed2k href
* The link is decoded at least once (some sites encode the filename twice, the
* second pass is done later on the filename only). When the scheme itself was
* encoded, more passes are needed before the link becomes usable.
* @param href the raw href attribute
* @return the decoded ed2k link
*/
function decodeEd2kLink(href) {
	var lnk = href;
	var prev;

	// 4 passes is far above any realistic encoding depth and can not loop forever
	for (var pass = 0; pass < 4; pass++) {
		prev = lnk;

		// to detect if the url encoding has produced ISO Latin or UTF8 encoding.
		// decodeURIComponent throws an exception on invalid UTF8 sequences.
		try {
			lnk = decodeURIComponent(lnk);	// block on certain char (example: %E0 which is à)
		}
		catch (e) {
			lnk = unescape(lnk);
			// The unescape() function was deprecated in JavaScript version 1.5
			// But some of the links has been encoded using escape and some encoded
			// char can not be decoded with the new method decodeURIComponent()
		}

		// stop as soon as the scheme is readable, or when there is nothing left to decode
		if (lnk == prev || /^ed2k:/i.test(lnk)) {
			break;
		}
	}

	return lnk;
}

/**
* Check the structure of a decoded ed2k link
* A downloadable link looks like: ed2k://|file|<name>|<size>|<hash>|...|/
* Malformed links (ed2k://xxxx) and links that are not files (ed2k://|server|...,
* ed2k://|serverlist|...) are rejected here, so that a single bad link in a page
* can not break the scan of the whole page.
* @param tlnk the decoded ed2k link, already split on |
* @return true if the link can be used
*/
function isValidEd2kFile(tlnk) {
	return tlnk.length >= 5			// scheme, type, name, size, hash
		&& tlnk[1].toLowerCase() == 'file'
		&& tlnk[2] != ''			// an empty name would display an empty row
		&& /^\d+$/.test(tlnk[3]);	// the size is mandatory to download the file
}

// -------------------------------------------------------------------------
// Popup: its toolbars, its views, its list, its edit box and its commands (SF-2 to SF-5, SF-9, SF-10)
// -------------------------------------------------------------------------

/**
* Creating the Popup
* @param links array filled with ed2k links
* @param files array filled with ed2k file names
*/
function createPopup(links, files, sizes) {
	var theDiv;		// the popup
	var divBody;	// The popup body
	var container; 	// the popup inserted in the page

	trace("createPopup");
	delCloseMessage();	// the popup opened again: the message of its closing is no longer needed (I-3)
	// First the Div
	theDiv=document.createElement('div');
	divBody = '<div id="theDiv" style="\
					'+ popupPlace() + ' \
					background-color:white; \
					opacity:0.97; \
					color:black;\
					margin:0;\
					border:2px solid #2b5c8a;\
					z-index:255;\
					text-align:left;\
					font-size:10px;\
					line-height:90%;\
					padding-left:5px;\
					padding-right:5px;';
	if (popupHeight != 0 && popupMode==1) {
		divBody += 'max-height:'+ popupHeight +'px;';
	}
	else {
		divBody += 'max-height:100%;';
	}
	if (popupWidth != 0 && popupMode==1) {
		divBody += 'max-width:'+ popupWidth +'px;';
	}
	else {
		divBody += 'max-width:100%;';
	}
	divBody += 'overflow:auto">';
	divBody += '<style>' + POPUP_CSS + '</style>';	// the look of the popup, in the PARAM block
	divBody += '</div>';
	theDiv.innerHTML=divBody;
	document.body.insertBefore(theDiv, document.body.firstChild);

	container = document.getElementById ("theDiv");

	// adding the function toolbar at the top
	addToolbar(container, 0);
	placeStatus();	// the band of an answer shown while the popup was closed, now in it (SF-7.10)

	// adding the body
	var tmp_link=document.createElement('div');
	tmp_link.setAttribute('id', 'divBody');
	tmp_link.style.clear='both';

	trace('createPopup() popupMode=' + popupMode);
	switch(popupMode) {
		case 0: // popup closed
			break;

		case 1: // normal mode
			tmp_link.innerHTML = htmlLinkList(links, files, sizes);
			// the list framed by two lines from one side of the popup to the other, which do not scroll
			// with it (its borders); none in edit mode, where the frame of the edit box separates (I-2)
			tmp_link.className = 'emlList';
			container.appendChild(tmp_link);
			container.style.resize = popupResize();
			// a column: top toolbar, list, bottom toolbar. Only the list scrolls, the
			// toolbars always stay visible, whatever the number of links (SF-2.9)
			container.style.display='flex';
			container.style.flexDirection='column';
			container.style.overflow='hidden';
			tmp_link.style.flex='1 1 auto';
			tmp_link.style.minHeight='0';
			tmp_link.style.overflow='auto';
			addScrollShadows(container, tmp_link);
			// custom method: a click on a file name sends it with a POST form (SF-3.3)
			tmp_link.addEventListener('click', clickOneLink, false);
			// the "check all" boxes follow the boxes of the links
			tmp_link.addEventListener('change', syncCheckAll, false);
			break;

		case 2: // edit mode
			container.appendChild(tmp_link);
			addEditBox(tmp_link, concatLinks(eLinks));
			container.style.resize='none';
			container.style.overflow='hidden';
			break;

		default:
			trace("ERROR: popupMode=" + popupMode);
			alert("Error !!! popupMode unknown.");
			break;
	}

	// adding the function toolbar at the bottom
	addToolbar(container, 1);

	// the "check all" boxes show the links left unchecked by the filter of the settings (SF-5.7),
	// the counters the links that Download sends
	fitCounters();
	syncCheckAll();
}

/**
* The shadows on the edges of the list where links are hidden, laid over it: they tell that the list
* goes on, whatever the scrollbar (Firefox shows it only under the mouse). A background of the list
* cannot do it: Chrome scrolls it with the list (I-2)
* @param container the popup
* @param list the list of the links, which scrolls
*/
function addScrollShadows(container, list) {
	var shadows = [document.createElement('div'), document.createElement('div')];
	shadows[0].className = 'emlShadow top';
	shadows[1].className = 'emlShadow bottom';
	container.appendChild(shadows[0]);
	container.appendChild(shadows[1]);
	var update = function () { placeScrollShadows(container, list, shadows); };
	list.addEventListener('scroll', update, false);
	// the popup resized by the user, minimized, maximized, or the window resized
	if (typeof ResizeObserver == 'function') {
		new ResizeObserver(update).observe(list);
	}
	else {
		window.addEventListener('resize', update, false);
	}
	update();
}

/**
* The shadows over the edges of the list, without its scrollbar, each one shown when links are hidden
* beyond its edge
*/
function placeScrollShadows(container, list, shadows) {
	if (!container.isConnected) {
		return;
	}
	var shown = (list.offsetParent !== null);	// not minimized
	var p = container.getBoundingClientRect();
	var r = list.getBoundingClientRect();
	var top = r.top - p.top - container.clientTop + list.clientTop;
	for (var i=0; i<shadows.length; i++) {
		shadows[i].style.left = (r.left - p.left - container.clientLeft + list.clientLeft) + 'px';
		shadows[i].style.width = list.clientWidth + 'px';
	}
	shadows[0].style.top = top + 'px';
	shadows[1].style.top = (top + list.clientHeight - 7) + 'px';
	shadows[0].style.display = (shown && list.scrollTop > 0) ? 'block' : 'none';
	shadows[1].style.display = (shown && list.scrollTop + list.clientHeight < list.scrollHeight - 1) ? 'block' : 'none';
}

/**
* The counters as wide as their widest value on the page, all the links checked: checking or unchecking
* links moves nothing in the toolbars (I-2). In edit mode, a text with more links widens them.
*/
function fitCounters() {
	var counters=document.querySelectorAll('#theDiv .emlCount');
	for (var c=0; c<counters.length; c++) {
		counters[c].style.minWidth = '';
		counters[c].innerHTML = eLinks.length + '<span>/' + eLinks.length + '</span>';
		counters[c].style.minWidth = counters[c].getBoundingClientRect().width + 'px';
	}
}

/**
* The place of the popup in the window, as CSS: its corner (popupCorner, SF-2.1), and its scrolling
* (popupScroll, SF-2.2): fixed in the window (floating), or scrolling with the page (static)
*/
function popupPlace() {
	var corner = popupCorner.split('-');	// top or bottom, left or right
	return 'position:' + (popupScroll == 'static' ? 'absolute' : 'fixed') + '; ' + corner[0] + ':0; ' + corner[1] + ':0;';
}

/**
* The drawing of the Minimize / Maximize button (SF-2.12): its arrow points to where the popup goes. At the
* top of the window, Minimize ▲ and Maximize ▼; at the bottom, where the popup folds down to its toolbar,
* the other way round
* @param minimized true for the Maximize button of the minimized popup
*/
function viewIcon(minimized) {
	var up = (popupCorner.indexOf('bottom') == 0) ? minimized : !minimized;
	return ICONS[up ? 'minimize' : 'maximize'];
}

/**
* Whether the popup can be resized (SF-2.4): in normal mode, and at the top left only, as the handle of
* the browsers is at its bottom right: elsewhere, the popup would grow the other way than the mouse
*/
function popupResize() {
	return (popupMode == 1 && popupCorner == 'top-left') ? 'both' : 'none';
}

/**
* Delete popup
*/
function delPopup() {
	trace('delPopup()');
	var theDiv = document.getElementById ("theDiv");
	var line = document.getElementById('emlStatus');
	if (theDiv && line && theDiv.contains(line)) {
		document.body.appendChild(line);	// the band of an answer kept, placed again by placeStatus() (SF-7.10)
	}
	if (theDiv) {
		theDiv.parentNode.removeChild(theDiv);
	}
}

/**
* Update Popup
*/
function updatePopup() {
	trace('updatePopup()');
	delPopup();
	createPopup(eLinks, eFiles, eSizes);
}

/**
* HTML link list
* @param links array
* @param files array
* @return html list
*/
function htmlLinkList(links, files, sizes) {
	var html="";

	trace('htmlLinkList()');

	html = '<table>';

	for (var i=0; i<links.length; i++) {
		// the links whose name does not match the filter of the settings are left unchecked, and greyed (SF-5.7)
		if (checkedByDefault(eNames[i])) {
			html += '<tr><td><input class="smallcheck" name="l' + i + '" type="checkbox" id="l' + i + '" tabindex="' + (i+1) + '" value="1" checked="checked" /></td>';
		}
		else {
			html += '<tr class="filtered" title="' + tr('filteredTitle') + '"><td><input class="smallcheck" name="l' + i + '" type="checkbox" id="l' + i + '" tabindex="' + (i+1) + '" value="1" /></td>';
		}
		html += '<td style="white-space:nowrap;"><a class="ed2k" href="' + linkHref(links[i]) + '" target="emule">' + files[i] + '</a></td><td style="min-width:40px;">'+ humanFileSize(sizes[i], false, 0) + '</td></tr>'; //
	}

	html += '</table>';
	return html;
}

/**
* concat links into one string with carrier returns
*/
function concatLinks(links) {
	var str=""; // string of links

	for (var i=0; i<links.length; i++) {
		if (i==0) {
			str=links[i];
		}
		else {
			str += '\n' + links[i];
		}
	}

	return str;
}

/**
* configuring and adding the toolbar
* @param container, the element to append the toolbar
*/
function addToolbar(container, pos) {
	trace('addToolbar(container, '+ pos +')');

	// one row of controls (SF-2.7): the top one is the only one shown when the popup is minimized,
	// so that it holds the sending; the bottom one also, at its right, nearest to the middle of the
	// page, where the mouse usually is (I-2)
	var bar=document.createElement('div');
	bar.className = 'toolbar';
	bar.id = (pos==0) ? 'emlTop' : 'emlBottom';
	container.appendChild(bar);

	// checkbox all, in both toolbars: checks or unchecks every link, mixed when only some of them
	// are checked (syncCheckAll(), SF-5.1, SF-5.4)
	var box=document.createElement('input');
	box.type = "checkbox";
	box.value = "1";
	box.checked = true;
	box.className = 'smallcheck checkall';
	box.name = (pos==0) ? "lall" : "lall2";
	box.id = (pos==0) ? "checkall" : "checkall2";
	box.title = tr('checkAllTitle');
	// in edit mode the link list is a textarea: there is no checkbox to toggle
	box.disabled = (popupMode == 2);
	box.addEventListener('click', function(e){ checkButton(e.target); }, false );
	bar.appendChild(box);

	// the links that Download sends, out of the links of the page (syncCheckAll())
	var count=document.createElement('span');
	count.className = 'emlCount';
	bar.appendChild(count);

	// bottom toolbar: Edit/Normal mode
	if (pos==1) {
		var edit = toolbarButton(trLabel((popupMode == 2) ? 'normalMode' : 'editMode'),
			tr((popupMode == 2) ? 'normalModeTitle' : 'editModeTitle'), editButton, '');
		edit.id = 'emlEdit';
		bar.appendChild(edit);
	}

	// the sending: the server (when there is a choice) and the category, each one unless hidden by the
	// settings, then Download; at the right of the bottom toolbar
	var sending = [];
	if (showServerList && pageServers.length > 1) {
		sending.push(serverList(pos));
	}
	if (showCategories) {
		sending.push(categoryList(pos));
	}
	var add = toolbarButton(trLabel('download'), tr('downloadTitle'), addButton, 'emlAdd');
	add.disabled = sendingBusy;	// disabled while a sending waits for its answer (setSending())
	sending.push(add);
	if (pos==1) {
		sending[0].classList.add('emlRight');
	}
	for (var s=0; s<sending.length; s++) {
		bar.appendChild(sending[s]);
	}

	// top toolbar, at its right: settings, help, minimize or maximize, close
	if (pos==0) {
		bar.appendChild(iconButton('settings', tr('settingsTitle'), setButton, 'emlIcon emlRight'));
		var help = iconButton('help', tr('helpTitle'), helpButton, 'emlIcon');
		help.id = 'emlHelpBtn';
		bar.appendChild(help);
		// its name as data-icon (minimize or maximize), its arrow as the corner of the popup asks (viewIcon())
		var min = toolbarButton(viewIcon(popupMinimized), tr(popupMinimized ? 'maximizeTitle' : 'minimizeTitle'),
			minimizeButton, 'emlIcon');
		min.setAttribute('data-icon', popupMinimized ? 'maximize' : 'minimize');
		min.id = 'emlMin';
		bar.appendChild(min);
		var close = iconButton('close', tr('closeTitle'), closeButton, 'emlIcon');
		close.id = 'emlClose';
		bar.appendChild(close);
	}
}

/**
* A button of a toolbar showing an icon (ICONS), named by its attribute data-icon
* @param icon the name of the icon
* @param title its tooltip: what it does, and its shortcut
* @param action the function called by a click
* @param classes its classes
*/
function iconButton(icon, title, action, classes) {
	var button = toolbarButton(ICONS[icon], title, action, classes);
	button.setAttribute('data-icon', icon);
	return button;
}

/**
* A button of a toolbar
* @param html its label, with the letter of its shortcut underlined
* @param title its tooltip: what it does, and its shortcut
* @param action the function called by a click
* @param classes its classes
*/
function toolbarButton(html, title, action, classes) {
	var button=document.createElement('button');
	button.innerHTML = html;
	button.title = title;
	button.className = classes;
	button.addEventListener('click', function(){ action(); }, false );
	return button;
}

/**
* The drop-down list of the categories of a toolbar: "cat" at the top, "cat2" at the bottom; both
* show the same category (changeCat())
* @param pos 0 for the top toolbar, 1 for the bottom one
*/
function categoryList(pos) {
	var selection = document.createElement('select');
	selection.setAttribute('name', (pos==0) ? 'Category' : 'Category2');
	selection.id = (pos==0) ? "cat" : "cat2";
	selection.className = 'emlCat';

	for(var i=0; i < emuleCat.length; i++) {
		trace('emuleCat['+i+'] => '+emuleCat[i].name+'='+emuleCat[i].value+' ('+emuleCat[i].select+')');
		var option = document.createElement('option');
		option.setAttribute('value',emuleCat[i].value);
		option.text = emuleCat[i].name;
		if (emuleCat[i].select==1) {
			option.setAttribute('selected',1);
		}
		selection.appendChild(option);
	}

	// grayed out when there is nothing to choose: a method without categories, or a single category
	if(ed2kDlMethod=='local' || ed2kDlMethod=='mldonkey' || emuleCat.length < 2) {
		selection.disabled = true;
	}
	selection.title = categoryTitle(selection);

	selection.addEventListener('change', function(e){ changeCat(e.target); }, false );
	return selection;
}

/**
* The tooltip of a category list: the category chosen, whole (a long name is cut in the list)
*/
function categoryTitle(selection) {
	var option = selection.options[selection.selectedIndex];
	return tr('categoryTip', {name: option ? option.text : ''});
}

/**
* The drop-down list of the servers of a toolbar (I-6): "srv" at the top, "srv2" at the bottom; both
* show the same server (changeServer()). Grayed out while a sending waits for its answer (setSending()).
* @param pos 0 for the top toolbar, 1 for the bottom one
*/
function serverList(pos) {
	var selection = document.createElement('select');
	selection.setAttribute('name', (pos==0) ? 'Server' : 'Server2');
	selection.id = (pos==0) ? 'srv' : 'srv2';
	selection.className = 'emlSrv';

	for (var i=0; i<pageServers.length; i++) {
		var option = document.createElement('option');
		option.value = pageServers[i].id;
		option.text = pageServers[i].name;
		option.selected = (pageServers[i].id == pageServer);
		selection.appendChild(option);
	}
	selection.disabled = sendingBusy;
	selection.title = serverTitle(selection);

	selection.addEventListener('change', function(e){ changeServer(e.target); }, false );
	return selection;
}

/**
* The tooltip of a server list: the server chosen, whole (a long name is cut in the list), and its method
*/
function serverTitle(selection) {
	var server = findPageServer(selection.value);
	var name = !server ? '' : (server.method == 'local') ? methodLabel('local') : server.name + ', ' + methodLabel(server.method);
	return tr('serverTip', {name: name});
}

/**
* Add a text area full of ed2k links
* @param container, the element to append the textarea
*/
function addEditBox(container, txt) {
	var tmp_link=document.createElement('textarea');
	tmp_link.id = "editbox";
	tmp_link.name = "txt";
	// no maximum length: it would only prevent the user from typing, the list itself is
	// never truncated by it (checked with 2,000 links, about 216,000 characters)
	tmp_link.cols = editCol;
	tmp_link.rows = editRow;
	tmp_link.value = txt;
	tmp_link.style.fontSize='11px';
	tmp_link.style.width='100%';
	tmp_link.style.height='100%';
	// the counters follow the links of the text
	tmp_link.addEventListener('input', syncCheckAll, false);
	container.appendChild (tmp_link);
//	container.style.resize='none';
	tmp_link.select();
}

/**
* Delete text area
*/
function delEditBox() {
	var editBox=document.getElementById('editbox');
	editBox.parentNode.removeChild(editBox);
}

/**
* Actions when "Edit/Reset" button is pressed
*/
function editButton() {
	trace("editButton()");
	// no popup on a page without ed2k links: nothing to switch, and the mode stays as it is
	if (eLinks.length == 0) {
		trace("editButton() no ed2k link in this page");
		return;
	}
	// the popup is rebuilt, maximized
	popupMinimized = false;
	switch(popupMode) {
		case 1: // in normal mode
			popupMode = 2;
			updatePopup();
			break;

		case 0: // popup closed
		case 2: // in edit mode
			popupMode = 1;
			updatePopup();
			break;

		default:
			trace("ERROR: popupMode=" + popupMode);
			alert("Error !!! popupMode unknown.");
			return;
	}
}

/**
* Actions when "Settings" button is pressed
*/
function setButton() {
	trace("setButton()");
	trace("scriptConfig() invoking the dialog");
	GM_config.open();
	GM_setValue("emule_config",1);
}

/**
* Actions when the popup is closed by the user: its Close button, Ctrl+Alt+C, the menu "Close Popup".
* A message then tells how to open it again (I-3), unless the setting closeMessage is unchecked; none
* when no popup was open.
*/
function closeButton() {
	trace("closeButton()");
	if (closePopup() && closeMessage) {
		showCloseMessage();
	}
}

/**
* Close the popup, without any message: Ctrl+Alt+X goes through the views with it (cycleView())
* @return true when a popup was open
*/
function closePopup() {
	var candidate=document.getElementById("theDiv");
	delPopup();
	popupMode = 0;
	popupMinimized = false;
	placeStatus();	// the band of an answer stays, alone in the corner of the popup (SF-7.10)
	return candidate != null;
}

/**
* The message shown when the popup is closed (I-3): a box inside the page, not an alert, centered in the
* window on a backdrop, as the settings dialog, so that it cannot be missed, telling how to open it again, and how to keep it closed (the default view, or the script
* restricted to some sites, step 7 of the installation guide of the README). OK, its Close button or
* Escape close it, and so does the popup opened again; its box "Don't display again" then unchecks the
* setting closeMessage, stored at once.
*/
function showCloseMessage() {
	var manager = (typeof GM_info != 'undefined' && GM_info.scriptHandler) ? GM_info.scriptHandler : tr('userscriptManager');
	var box = document.createElement('div');
	var backdrop = document.createElement('div');

	trace('showCloseMessage()');
	delCloseMessage();
	backdrop.id = 'emlMsgBackdrop';		// the page cannot be clicked behind the message, nor does a click close it
	box.id = 'emlMsg';
	box.innerHTML = '<style>' + MESSAGE_CSS + '</style>'	// the look of the message, in the PARAM block
		+ '<div class="emlMsgBar"><span class="emlMsgTitle">' + tr('closedTitle') + '</span></div>'
		+ '<div class="emlMsgText">' + tr('closedText', {manager: '<span class="emlMsgManager"></span>',
			link: '<a target="_blank" rel="noopener">', end: '</a>'}) + '</div>'
		+ '<div class="emlMsgBar bottom"><label><input type="checkbox" id="emlMsgOff">' + tr('dontDisplay') + '</label></div>';
	box.querySelector('.emlMsgManager').textContent = manager;
	box.querySelector('.emlMsgText a').href = REPOSITORY + '#how-to-install';
	var close = iconButton('close', tr('closeMessageTitle'), dismissCloseMessage, '');
	close.id = 'emlMsgClose';
	box.querySelector('.emlMsgBar').appendChild(close);
	var ok = toolbarButton(tr('ok'), tr('closeMessageTitle'), dismissCloseMessage, '');
	ok.id = 'emlMsgOk';
	box.querySelector('.emlMsgBar.bottom').appendChild(ok);
	document.body.appendChild(backdrop);
	document.body.appendChild(box);
	document.addEventListener('keydown', closeMessageOnEscape, false);
}

/**
* Close the message of the closed popup (OK, its Close button, Escape): with "Don't display again"
* checked, the setting closeMessage is unchecked and stored at once (storeSetting())
*/
function dismissCloseMessage() {
	var off = document.getElementById('emlMsgOff');
	if (off && off.checked) {
		closeMessage = false;
		storeSetting('closeMessage', false);
	}
	delCloseMessage();
}

/**
* Remove the message of the closed popup, if any, with its backdrop
*/
function delCloseMessage() {
	var box = document.getElementById('emlMsg');
	var backdrop = document.getElementById('emlMsgBackdrop');
	if (box) {
		box.parentNode.removeChild(box);
	}
	if (backdrop) {
		backdrop.parentNode.removeChild(backdrop);
	}
	document.removeEventListener('keydown', closeMessageOnEscape, false);
}

/**
* Escape closes the message of the closed popup, as OK does
*/
function closeMessageOnEscape(e) {
	if (e.key == 'Escape' || e.keyCode == 27) {
		dismissCloseMessage();
	}
}

/**
* Actions when the help is asked: the ? button, Ctrl+Alt+H, the menu "Help" (I-5). It shows the help, or
* closes it when it is shown; nothing on a page without ed2k links, as the other commands of the popup.
*/
function helpButton() {
	trace('helpButton()');
	if (document.getElementById('emlHelp')) {
		delHelp();
	}
	else if (eLinks.length > 0) {
		showHelp();
	}
}

/**
* The help built into the script (I-5): a box inside the page, without backdrop, so that the popup it
* explains stays in view and usable, beside it (placeHelp()). It draws each control of the toolbars, with
* what it does and its shortcut, and links to the documentation and to the issues on GitHub, in a new tab.
* OK, its Close button, Escape, the ? button or Ctrl+Alt+H close it.
*/
function showHelp() {
	var manager = (typeof GM_info != 'undefined' && GM_info.scriptHandler) ? GM_info.scriptHandler : tr('userscriptManager');
	var box = document.createElement('div');
	var chip = function (html, classes) { return '<span class="emlChip ' + (classes || '') + '">' + html + '</span>'; };
	// each control of the toolbars, drawn: what it does, its shortcut
	var rows = [
		[chip('<input type="checkbox" checked tabindex="-1">', 'icon'), tr('helpCheckAll'), 'Ctrl+Alt+A'],
		[chip('9<span>/9</span>', 'count'), tr('helpCount'), ''],
		[chip(tr('helpServerChip')), tr('helpServer'), ''],
		[chip(tr('helpCategoryChip')), tr('helpCategory'), ''],
		[chip(trPlain('download'), 'add'), tr('helpDownload'), 'Ctrl+Alt+D'],
		[chip(trPlain('editMode')), tr('helpEditMode'), 'Ctrl+Alt+M'],
		[chip(ICONS.settings, 'icon'), tr('helpSettings'), 'Ctrl+Alt+S'],
		[chip(ICONS.help, 'icon'), tr('helpHelp'), 'Ctrl+Alt+H'],
		[chip(viewIcon(false), 'icon min') + ' ' + chip(viewIcon(true), 'icon min'), tr('helpView'), 'Ctrl+Alt+X'],
		[chip(ICONS.close, 'icon close'), tr('helpClose'), 'Ctrl+Alt+C']
	];

	trace('showHelp()');
	box.id = 'emlHelp';
	box.innerHTML = '<style>' + HELP_CSS + '</style>'	// the look of the help, in the PARAM block
		+ '<div class="emlHelpBar emlHelpHead"><span class="emlHelpTitle"></span></div>'
		+ '<div class="emlHelpBody">'
		+ '<p>' + tr('helpIntro') + '</p>'
		+ '<h4>' + tr('helpToolbars') + '</h4><table class="emlHelpRows">'
		+ rows.map(function (r) { return '<tr><td>' + r[0] + '</td><td>' + r[1] + '</td><td>' + r[2] + '</td></tr>'; }).join('')
		+ '</table>'
		+ '<h4>' + tr('helpList') + '</h4><ul>'
		+ '<li>' + tr('helpListClick') + '</li>'
		+ '<li>' + tr('helpListGray') + '</li>'
		+ '<li>' + tr('helpListShadow') + '</li></ul>'
		+ '<h4>' + tr('helpNext') + '</h4><ul>'
		+ '<li>' + tr('helpNextView') + '</li>'
		+ '<li>' + tr('helpNextMenu', {manager: '<span class="emlHelpManager"></span>'}) + '</li></ul>'
		+ '</div>'
		+ '<div class="emlHelpBar bottom"><a id="emlHelpDoc" target="_blank" rel="noopener noreferrer"></a>'
		+ '<span class="emlHelpSep">|</span><a id="emlHelpIssues" target="_blank" rel="noopener noreferrer"></a></div>';
	box.querySelector('.emlHelpTitle').textContent = boxTitle(tr('help'));
	box.querySelector('#emlHelpDoc').textContent = tr('helpDoc');
	box.querySelector('#emlHelpIssues').textContent = tr('helpIssues');
	box.querySelector('.emlHelpManager').textContent = manager;
	box.querySelector('#emlHelpDoc').href = REPOSITORY;
	box.querySelector('#emlHelpIssues').href = REPOSITORY + '/issues';
	var close = iconButton('close', tr('helpCloseTitle'), delHelp, '');
	close.id = 'emlHelpClose';
	box.querySelector('.emlHelpHead').appendChild(close);
	box.querySelector('.emlHelpHead').addEventListener('pointerdown', dragHelp, false);
	var ok = toolbarButton(tr('ok'), tr('helpCloseTitle'), delHelp, '');
	ok.id = 'emlHelpOk';
	box.querySelector('.emlHelpBar.bottom').appendChild(ok);
	document.body.appendChild(box);
	placeHelp();
	window.addEventListener('resize', placeHelp, false);
	document.addEventListener('keydown', helpOnEscape, false);
}

/**
* Place the help: where the user moved it on this page (helpPlace), or else centered in the free space
* beside the popup, at its right, or at its left when the popup is at the right of the window, so that
* both can be read at once; centered in the window when it does not fit there, or without popup. Always within the window. Called again when the window is resized: a help
* moved by the user is then only brought back into the window.
*/
function placeHelp() {
	var box = document.getElementById('emlHelp');
	var popup = document.getElementById('theDiv');
	var width = document.documentElement.clientWidth;	// the window, without its scrollbar
	var height = document.documentElement.clientHeight;
	var x, y;

	if (box == null) {
		return;
	}
	if (helpPlace) {
		x = helpPlace.left;
		y = helpPlace.top;
	}
	else {
		var rect = popup ? popup.getBoundingClientRect() : null;
		var atRight = rect ? width - rect.right : 0;	// the free space at the right of the popup
		var atLeft = rect ? rect.left : 0;
		if (rect && atRight >= atLeft && atRight >= box.offsetWidth + 20) {
			x = rect.right + (atRight - box.offsetWidth) / 2;
		}
		else if (rect && atLeft > atRight && atLeft >= box.offsetWidth + 20) {
			x = (atLeft - box.offsetWidth) / 2;
		}
		else {
			x = (width - box.offsetWidth) / 2;
		}
		y = (height - box.offsetHeight) / 2;
	}
	box.style.left = Math.max(0, Math.min(x, width - box.offsetWidth)) + 'px';
	box.style.top = Math.max(0, Math.min(y, height - box.offsetHeight)) + 'px';
}

/**
* Move the help by dragging its title bar, not from its Close button, within the window (placeHelp()):
* the place is kept for the page (helpPlace). The pointer is captured, so that the help follows it even
* out of the bar; the moves are listened to during the drag only.
*/
function dragHelp(e) {
	var box = document.getElementById('emlHelp');
	var bar = e.currentTarget;

	if (box == null || e.button != 0 || e.target.closest('button')) {
		return;
	}
	e.preventDefault();		// no text selected while dragging
	var start = {x: e.clientX, y: e.clientY, left: parseFloat(box.style.left) || 0, top: parseFloat(box.style.top) || 0};
	var move = function (m) {
		helpPlace = {left: start.left + m.clientX - start.x, top: start.top + m.clientY - start.y};
		placeHelp();
	};
	var end = function () {
		helpPlace = {left: parseFloat(box.style.left) || 0, top: parseFloat(box.style.top) || 0};	// within the window
		bar.removeEventListener('pointermove', move, false);
		bar.removeEventListener('pointerup', end, false);
		bar.removeEventListener('pointercancel', end, false);
	};
	if (bar.setPointerCapture) {
		bar.setPointerCapture(e.pointerId);
	}
	bar.addEventListener('pointermove', move, false);
	bar.addEventListener('pointerup', end, false);
	bar.addEventListener('pointercancel', end, false);
}

/**
* Remove the help, if any
*/
function delHelp() {
	var box = document.getElementById('emlHelp');
	if (box) {
		box.parentNode.removeChild(box);
	}
	window.removeEventListener('resize', placeHelp, false);
	document.removeEventListener('keydown', helpOnEscape, false);
}

/**
* Escape closes the help, as OK does
*/
function helpOnEscape(e) {
	if (e.key == 'Escape' || e.keyCode == 27) {
		delHelp();
	}
}

/**
* Actions when the popup is opened: Ctrl+Alt+O, Ctrl+Alt+X when closed, menu "Open Popup"
* There is always one popup at most: an open popup is left as it is (its selection and
* its edit box are kept), maximized if it was minimized, and nothing is opened on a page
* without ed2k links (SF-1.12).
*/
function openButton() {
	trace("openButton()");
	if (eLinks.length == 0) {
		trace("openButton() no ed2k link in this page");
		return;
	}
	if (document.getElementById("theDiv")) {
		if (popupMinimized) {
			setMinimized(false);
		}
		return;		// already open
	}
	popupMode = 1;
	popupMinimized = false;
	createPopup(eLinks, eFiles, eSizes);
}

/**
* Actions when the minimize / maximize button of the popup is pressed (I-2)
*/
function minimizeButton() {
	trace("minimizeButton()");
	setMinimized(!popupMinimized);
}

/**
* Minimize or maximize the popup: minimized, only its top toolbar is shown, at the width of the
* maximized popup, so that nothing moves in it; its list (or its edit box) and its bottom toolbar
* are only hidden: the checked links and the edited text are kept.
* @param on true to minimize, false to maximize
*/
function setMinimized(on) {
	var container = document.getElementById('theDiv');
	var hidden = [document.getElementById('divBody'), document.getElementById('emlBottom')];
	var button = document.getElementById('emlMin');

	trace('setMinimized(' + on + ')');
	if (container == null || on == popupMinimized) {
		return;
	}
	if (on) {
		// the size given by the user (resize) is kept for the maximized popup
		container.dataset.width = container.style.width;
		container.dataset.height = container.style.height;
		container.style.boxSizing = 'border-box';
		container.style.width = container.getBoundingClientRect().width + 'px';
		container.style.height = '';
		container.style.resize = 'none';
	}
	else {
		container.style.boxSizing = '';
		container.style.width = container.dataset.width || '';
		container.style.height = container.dataset.height || '';
		container.style.resize = popupResize();
	}
	for (var i=0; i<hidden.length; i++) {
		if (hidden[i]) {
			hidden[i].style.display = on ? 'none' : '';
		}
	}
	button.innerHTML = viewIcon(on);
	button.setAttribute('data-icon', on ? 'maximize' : 'minimize');
	button.title = tr(on ? 'maximizeTitle' : 'minimizeTitle');
	popupMinimized = on;
	placeStatus();	// the band of an answer: in the popup, or floating against it
}

/**
* Ctrl+Alt+X, menu "Switch view": maximized, minimized, closed, in turn (I-2)
*/
function cycleView() {
	trace("cycleView()");
	if (popupMode == 0 || !document.getElementById("theDiv")) {
		openButton();
	}
	else if (!popupMinimized) {
		setMinimized(true);
	}
	else {
		closePopup();	// no message: who goes through the views knows how to open the popup again
	}
}

/**
* Ctrl+Alt+A, menu "Check or uncheck all links": as a click on the box of the top toolbar; nothing
* when there is no box to click (popup closed, edit mode)
*/
function checkAllButton() {
	var box = document.getElementById('checkall');
	trace("checkAllButton()");
	if (box == null || box.disabled) {
		trace("checkAllButton() no list of links to check");
		return;
	}
	box.click();
}

/**
* Actions when the "check all" box of a toolbar is clicked: every link takes its state. A mixed
* box becomes checked when clicked: every link is then checked.
* @param checkbox the box clicked, in the top or the bottom toolbar
*/
function checkButton(checkbox) {
	trace("checkButton()");
	var line;
	for (var i=0; i<eLinks.length; i++) {
		line = document.getElementById('l'+i);
		if (line != null) { line.checked=checkbox.checked; }
	}
	syncCheckAll();
}

/**
* Show the state of the links on the "check all" boxes of both toolbars: checked when every link
* is checked, unchecked when none is, mixed otherwise (SF-5.1, SF-5.7)
*/
function syncCheckAll() {
	var count=0;
	var line;
	var editBox=document.getElementById('editbox');
	var counters=document.querySelectorAll('#theDiv .emlCount');
	if (popupMode == 2 && editBox != null) {
		// edit mode: the boxes are disabled, the counters tell the links of the text, which Download sends
		count = editBox.value.split('\n').filter(function (l) { return /^ed2k:\/\//i.test(l.trim()); }).length;
	}
	else {
		for (var i=0; i<eLinks.length; i++) {
			line = document.getElementById('l'+i);
			if (line != null && line.checked) { count++; }
		}
		var boxes=document.querySelectorAll('#theDiv input.checkall');
		for (var b=0; b<boxes.length; b++) {
			boxes[b].checked = (count == eLinks.length);
			boxes[b].indeterminate = (count > 0 && count < eLinks.length);
		}
	}
	for (var c=0; c<counters.length; c++) {
		counters[c].innerHTML = count + '<span>/' + eLinks.length + '</span>';
		counters[c].title = (popupMode == 2) ? tr('countTextTitle', {count: count})
			: tr('countTitle', {count: count, total: eLinks.length});
	}
}

/**
* Actions when category is changed
*/
function changeCat(cat) {
	trace("changeCat()");

	// both lists of the popup show the category chosen
	var lists=document.querySelectorAll('#theDiv select.emlCat');
	for (var l=0; l<lists.length; l++) {
		lists[l].value = cat.value;
		lists[l].title = categoryTitle(lists[l]);
	}

	for (var i=0; i<emuleCat.length; i++) {
		if(emuleCat[i].value==cat.value) {
			emuleCat[i].select=1;
		}
		else {
			emuleCat[i].select=0;
		}
	}
	// Not stored on purpose (product decision, SPECIFICATIONS.md SF-6.9): the category chosen here is valid for the current page only,
	// each new page starts again on the default category of the settings.
	// Storing it was tried: it was causing a bug when the user changed the category in the popup and then opened the settings dialog: the category was reset to the default value.
	//GM_config.set("emuleCat", catToStr(emuleCat));
	// nothing else to do: the popup is not rebuilt, and no link of the popup carries the category,
	// read when sending (SF-6.6, SF-6.8)
}

/**
* Actions when the server is changed (I-6): the server chosen receives the links of this page, with its
* own settings (useServer()); the category lists offer its categories, from its default one. Not stored,
* as the category (SF-6.9): the next page starts on the server checked in the settings.
* @param list the server list changed
*/
function changeServer(list) {
	var server = findPageServer(list.value);

	if (server == null) {
		return;
	}
	trace('changeServer() ' + server.name);
	useServer(server);

	// both lists of the popup show the server chosen
	var lists = document.querySelectorAll('#theDiv select.emlSrv');
	for (var l=0; l<lists.length; l++) {
		lists[l].value = server.id;
		lists[l].title = serverTitle(lists[l]);
	}
	// the category lists, rebuilt with its categories, in their place
	var cats = document.querySelectorAll('#theDiv select.emlCat');
	for (var c=0; c<cats.length; c++) {
		var fresh = categoryList((cats[c].id == 'cat') ? 0 : 1);
		fresh.className = cats[c].className;
		cats[c].parentNode.replaceChild(fresh, cats[c]);
	}
}

/**
* Actions when the menu entry "Toggle debug traces" is chosen
* The setting is stored: the traces stay on (or off) on the next pages, until switched again.
*/
function debugButton() {
	DEBUG_MODE = DEBUG_MODE ? 0 : 1;
	GM_setValue('debug_mode', DEBUG_MODE);
	alert(tr(DEBUG_MODE ? 'debugOn' : 'debugOff'));
}

// -------------------------------------------------------------------------
// Selection: the links checked, the server and the category chosen (SF-5, SF-6, I-6)
// -------------------------------------------------------------------------

/**
* Get selected links
* When the popup is not displayed there is no checkbox to read: the links that the
* popup would check are then selected, every link when the filter of the settings is
* empty (SF-5.5, SF-5.7).
* @param links the ed2k links found in the page
* @return the selected links
*/
function getSelectLink(links) {
	var lnk= new Array();
	var idx=0;
	var checkbox;

	for (var i=0; i<links.length; i++) {
		checkbox = document.getElementById('l'+i);
		if (checkbox == null ? checkedByDefault(eNames[i]) : checkbox.checked == true) {
			lnk[idx]=links[i];
			idx++;
		}
	}
	return lnk;
}

/**
* Read the filter of the links checked by default (SF-5.7): a regular expression, written alone
* (case-sensitive) or as /expression/flags, as in JavaScript (/expression/i ignores the case).
* The flags g and y are refused: they make each test start where the previous one stopped.
* @param str the filter, as written in the settings
* @return {re: the regular expression, or null for an empty filter} or {error: the reason}
*/
function parseCheckFilter(str) {
	var text = String(str == null ? '' : str).trim();
	var source = text;
	var flags = '';
	var m = /^\/(.*)\/([a-z]*)$/.exec(text);

	if (text == '') {
		return {re: null};
	}
	if (m) {
		source = m[1];
		flags = m[2];
	}
	if (/[gy]/.test(flags)) {
		return {error: tr('filterFlags')};
	}
	try {
		return {re: new RegExp(source, flags)};
	}
	catch (e) {
		// the reason given by the browser, without the expression that it repeats (Chrome)
		var reason = String(e.message).split(': ').pop();
		return {error: tr('filterInvalid', {reason: reason.charAt(0).toUpperCase() + reason.slice(1)})};
	}
}

/**
* Tell whether a link is checked by default in the popup (SF-5.7)
* @param name the decoded file name, without the suffix of a duplicate name
* @return true when the name matches the filter of the settings, or when it is empty
*/
function checkedByDefault(name) {
	return checkRegExp == null || checkRegExp.test(name);
}

/**
* Get the category selected by the user
* The value comes from the emuleCat array and not from the popup, so that links
* can be sent even when the popup is not displayed.
* @return the value of the selected category, '0' when none is selected
*/
function getSelectedCat() {
	for (var i=0; i<emuleCat.length; i++) {
		if (emuleCat[i].select==1) {
			return emuleCat[i].value;
		}
	}
	return '0';
}

/**
* The servers that the popup offers (I-6), in pageServers: Local (unless disabled, I-14), then the servers
* stored by the settings dialog, in their order, the one checked in the settings chosen. Only its settings
* are kept: the others have their name and method only, their settings (their password included) being read
* when one is chosen (useServer()), so that they leave the storage only on an action of the user. This one takes its method and its
* settings from GM_config, as the rest of the script (saveConfig()): the settings of the older versions,
* kept there only, make a server named after its method, as in the settings dialog (setupServers()).
*/
function readServers() {
	var stored = GM_getValue('servers', '');
	var saved = {active: null, list: []};
	var checked = {method: ed2kDlMethod, emuleUrl: emuleUrl, emuleUser: emuleUser, emulePwd: emulePwd, emuleCat: catToStr(emuleCat)};
	var server;

	try {
		if (stored) {
			saved = JSON.parse(stored);
		}
	}
	catch (e) {
		trace('readServers() servers ignored: ' + e);
	}
	// Local, unless disabled in the settings (I-14), when another server receives the links
	pageServers = (saved.localDisabled && ed2kDlMethod != 'local') ? [] : [pageServerOf({id: 'local', name: tr('local'), method: 'local'})];
	pageServer = 'local';
	for (var i=0; i<(saved.list || []).length; i++) {
		server = saved.list[i];
		if (ed2kDlMethod != 'local' && server.id == saved.active) {
			pageServer = server.id;
			pageServers.push(pageServerOf(Object.assign({}, server, checked)));
		}
		else {
			pageServers.push({id: server.id, name: server.name, method: server.method});	// its settings: when chosen
		}
	}
	if (ed2kDlMethod != 'local' && pageServer == 'local') {
		pageServer = 'checked';
		pageServers.push(pageServerOf(Object.assign({id: pageServer, name: methodLabel(ed2kDlMethod)}, checked)));
	}
	trace('readServers() ' + pageServers.length + ' server(s), ' + pageServer + ' chosen');
}

/**
* A server of the popup: its id, its name, its method, and its settings (their default value when it
* has none), the Server URL ending with a / as in saveConfig()
*/
function pageServerOf(server) {
	var page = {id: server.id, name: server.name, method: server.method, ready: true};
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		page[METHOD_SETTINGS[i]] = serverSetting(server, METHOD_SETTINGS[i]);
	}
	if (page.method != 'custom' && page.emuleUrl.charAt(page.emuleUrl.length-1) != '/') {
		page.emuleUrl += '/';
	}
	return page;
}

/**
* Read the settings of a server of the popup, now that it is chosen (useServer()): from the servers stored
* by the settings dialog; its default settings if it is no longer there
* @return the server of the popup, with its settings, in place of the one given
*/
function readPageServer(server) {
	var found = null;
	try {
		found = (JSON.parse(GM_getValue('servers', '') || '{}').list || [])
			.filter(function (stored) { return stored.id == server.id; })[0];
	}
	catch (e) {
		trace('readPageServer() servers ignored: ' + e);
	}
	var page = pageServerOf(found || server);
	pageServers[pageServers.indexOf(server)] = page;
	return page;
}

/**
* The server of the popup that has this id, or null
*/
function findPageServer(id) {
	return pageServers.filter(function (server) { return server.id == id; })[0] || null;
}

/**
* Send the links of this page to this server: its method and its settings replace the ones of the
* settings, in memory only, its default category chosen
*/
function useServer(server) {
	if (!server.ready) {
		server = readPageServer(server);	// its settings, read now that it is chosen
	}
	pageServer = server.id;
	ed2kDlMethod = server.method;
	emuleUrl = server.emuleUrl;
	emuleUser = server.emuleUser;
	emulePwd = server.emulePwd;
	emuleCat = strToCat(server.emuleCat);
	if (emuleCat == -1) {
		emuleCat = strToCat('*default=0');
	}
}

// -------------------------------------------------------------------------
// Sending: the links to the method of the settings, and the answer of the client (SF-7)
// -------------------------------------------------------------------------

/**
* The methods whose sending a link of the popup cannot make: a POST form (custom), a JSON
* request (amuleapi), requests of the script, without a window (emule, amule, mldonkey): every
* method but local
*/
function sentByScript() {
	return ed2kDlMethod != 'local';
}

/**
* The href of a file name link of the popup
* For the methods whose sending a link cannot make (sentByScript()), the href is the ed2k link
* itself (shown on hover, copied by "Copy link"), and a click on it is turned into the sending
* by clickOneLink() (SF-3.3).
* @param link the ed2k link
* @return the href of its link in the popup
*/
function linkHref(link) {
	return sentByScript() ? encodeEd2kLink(link) : getAddLink([link]);
}

/**
* A click on a file name of the popup, with every method but local: the link
* cannot send the request itself, this sends it for this file only. The other methods:
* nothing to do, the link does the job.
* @param e the click event, caught on the list of links
*/
function clickOneLink(e) {
	var a = e.target.closest('a.ed2k');
	if (!a || !sentByScript()) {
		return;
	}
	e.preventDefault();
	var anchors = document.querySelectorAll('#divBody a.ed2k');
	var href = getAddLink([eLinks[[].indexOf.call(anchors, a)]]);
	if (ed2kDlMethod == 'amuleapi') {
		sendToAmuleApi(href);
	}
	else if (ed2kDlMethod == 'emule') {
		sendToEmule(href);
	}
	else if (ed2kDlMethod == 'amule') {
		sendToAmuleWeb(href);
	}
	else if (ed2kDlMethod == 'mldonkey') {
		sendToMldonkey(href);
	}
	else {
		post(emuleUrl, href);
	}
}

/**
* Actions when the Download button is pressed (Ctrl+Alt+D, menu "Download")
*/
function addButton() {
	trace("addButton()");
	var href="";
	var links=new Array();

	switch(popupMode) {
		case 0: // popup closed
		case 1: // in normal mode
			links=getSelectLink(eLinks);
			break;
		case 2: // in edit mode
			var txt = document.getElementById("editbox");
			if (txt == null) {
				// edit mode without its edit box: nothing to read
				links=getSelectLink(eLinks);
			}
			else {
				links=txt.value.split('\n');
			}
			break;
		default:
			trace("ERROR: popupMode=" + popupMode);
			alert("Error !!! popupMode unknown.");
			return;
	}

	if (links.length == 0) {
		trace("addButton() nothing to send");
		return;
	}

	href = getAddLink(links);
	trace("addButton() " + links.length + " link(s)");	// not the request: it may carry the password

	if(ed2kDlMethod=='local') {
		for (var i=0; i<links.length; i++) {
			openLocalLink(links[i]);
		}
	} else if(ed2kDlMethod=='custom') {
		post(emuleUrl, href);
	} else if(ed2kDlMethod=='amuleapi') {
		sendToAmuleApi(href);
	} else if(ed2kDlMethod=='emule') {
		sendToEmule(href);
	} else if(ed2kDlMethod=='amule') {
		sendToAmuleWeb(href);
	} else if(ed2kDlMethod=='mldonkey') {
		sendToMldonkey(href);
	}
}

/**
* Choose the right method to send the ed2k files
*/
function getAddLink(links) {
	var url="";
	var lnk=""; // string of links
	var tmp="";
	var cat="";

	trace('getAddLink('+links+')');

	cat = getSelectedCat();

	for (var i=0; i<links.length; i++) {
		tmp=links[i].split('|');

		// we encode the filename
		try {
			tmp[2]=encodeURIComponent(decodeURIComponent(tmp[2]));
		}
		catch (e) {
			trace("Error in decoding and re-encoding filename");
		}

		tmp=tmp.join('|');

		if (i==0) {
			lnk=tmp;
		}
		else {
			lnk += '\n' + tmp;
		}
	}

	switch(ed2kDlMethod) {
		case 'local':
			// a raw ed2k link is not a valid url: recent Chrome turns it into about:blank
			url = links.map(encodeEd2kLink).join('\n');
			break;

		case 'emule':
			// GET request of the script (sendToEmule()), no window: the links are in the url, so they are
			// encoded (the filename is then encoded twice), the password and the category too. Lines that
			// are not ed2k links (empty lines of the edit box) are left out: eMule does not check them, it
			// would answer that they are added
			lnk = lnk.split('\n').map(function (l) { return l.trim(); })
				.filter(function (l) { return /^ed2k:\/\//i.test(l); });
			url = {
				count: lnk.length,
				url: emuleUrl + "?w=password&p=" + encodeURIComponent(emulePwd) + "&cat=" + encodeURIComponent(cat) + "&c=" + encodeURIComponent(lnk.join('\n'))
			};
			break;

		case 'amule':
			if(cat == "0") {
				cat = "all";
			}

			// GET requests of the script (sendToAmuleWeb()), no window: the login, then the links, the
			// session being kept by its cookie. The links are in the url, so they are encoded (the filename
			// is then encoded twice), the category too (a name: amuleWebCategory()). Lines that are not
			// ed2k links are left out; the hashes of the links are kept, to find them in the downloads.
			lnk = lnk.split('\n').map(function (l) { return l.trim(); })
				.filter(function (l) { return /^ed2k:\/\//i.test(l); });
			url = {
				count: lnk.length,
				hashes: lnk.map(function (l) { return (l.split('|')[4] || '').toUpperCase(); }),
				url: emuleUrl + "footer.php?selectcat=" + amuleWebCategory(cat) + "&Submit=Download+link&ed2klink=" + encodeURIComponent(lnk.join('\n'))
			};
			break;

		case 'amuleapi':
			// JSON POST (sendToAmuleApi()): the links are not in a url, so they are not encoded a
			// second time. Lines that are not ed2k links (empty lines of the edit box) are left out:
			// the API would refuse the whole request
			url = {
				links: lnk.split('\n').map(function (l) { return l.trim(); })
					.filter(function (l) { return /^ed2k:\/\//i.test(l); }),
				category_index: parseInt(cat, 10) || 0
			};
			break;

		case 'mldonkey':
			// GET request of the script (sendToMldonkey()), no window, with HTTP Basic: the links are in
			// the url, so they are encoded (the filename is then encoded twice). Lines that are not ed2k
			// links are left out.
			lnk = lnk.split('\n').map(function (l) { return l.trim(); })
				.filter(function (l) { return /^ed2k:\/\//i.test(l); });
			url = {
				count: lnk.length,
				url: emuleUrl + "submit?jvcmd=multidllink&links=" + encodeURIComponent(lnk.join('\n'))
			};
			break;

		case 'custom':
			// POST method: no need to encode the link
			url = new Array();
			url["cat"] = cat;	// the category
			url["ref"] = window.location;	// the post where the links come from
			url["ed2k"] = lnk;	// the ed2k links
			break;

		default:
			break;
	}
	return url;
}

/**
* Percent encode an ed2k link so that it is a valid url
* Everything between ed2k:// and the final / is parsed as the host of the url,
* where |, spaces, #, ?, [, ] ... are forbidden: recent Chrome versions turn such
* a link into about:blank. This whole part is therefore encoded, the ed2k
* handlers decode the link they receive. Like getAddLink() does for the filename,
* it is decoded first, so that an already encoded link (pasted in edit mode for
* instance) is not encoded twice.
* @param lnk the ed2k link
* @return the encoded link
*/
function encodeEd2kLink(lnk) {
	var parts = lnk.match(/^(ed2k:\/\/)(.*?)(\/?)$/i);
	var body;

	if (parts == null) {
		return lnk;
	}

	body = parts[2];
	try {
		body = decodeURIComponent(body);
	}
	catch (e) {
		trace("encodeEd2kLink() can not decode, encoding as is: " + lnk);
	}

	return parts[1] + encodeURIComponent(body) + parts[3];
}

/**
* Hand one ed2k link to the application registered for the ed2k: scheme
* The link has to be percent encoded by ourselves (see encodeEd2kLink()): recent
* Chrome versions silently turn a raw link into about:blank instead of encoding
* it (older ones did it on their own, see 0.2 in CHANGELOG.md).
* We go through a synthetic anchor click and not location.replace(): the latter
* rejects the link outright, and it would replace the document, so only the last
* link of a batch would ever be sent.
* @param lnk the ed2k link to open
*/
function openLocalLink(lnk) {
	var a = document.createElement('a');
	a.href = encodeEd2kLink(lnk);
	a.style.display = 'none';
	document.body.appendChild(a);
	a.click();
	a.parentNode.removeChild(a);
}

/**
* Send ed2k links to aMule 3.1 and later, through its REST API (amuleapi)
* The API needs a JSON POST and a bearer token, which neither a window nor a form can
* send, and a fetch() from the page is blocked by the browser (CORS): the requests go
* through GM_xmlhttpRequest. A session is opened for this sending only and closed after
* it: the token is never stored. The password travels in a request body, never in a url.
* @param body the request body made by getAddLink(): {links: [...], category_index: n}
*/
async function sendToAmuleApi(body) {
	var api = emuleUrl + 'api/v1/';
	var token = null;
	var r;

	if (sendingBusy) {
		// a sending is waiting for its answer: the same links would be sent twice
		trace('sendToAmuleApi() a sending is already in progress, ignored');
		return;
	}
	if (body.links.length == 0) {
		showStatus(tr('noLink'), false);
		return;
	}
	trace('sendToAmuleApi() ' + body.links.length + ' link(s), category ' + body.category_index);
	setSending(true);
	showStatus(tr('pleaseWait'), null);	// until the answer of aMule replaces it
	try {
		r = await gmRequest('POST', api + 'auth/login?include_token=true', {password: emulePwd});
		if (r.status != 200 || r.json == null || !r.json.token) {
			showStatus(amuleApiError(r), false);
			return;
		}
		token = r.json.token;
		r = await gmRequest('POST', api + 'downloads', body, token, sendingTimeout(body.links.length));
		// 207: aMule received the links, and left some out (invalid, or already in its list): a warning
		showStatus(amuleApiResult(body.links, r), (r.status == 202) ? true : (r.status == 207) ? 'doubt' : false);
	}
	catch (e) {
		trace('sendToAmuleApi() ' + e);
		if (e.timeout) {
			// aMule received the request but answers late: the links may well be added
			showStatus(tr('notAnswered', {client: 'aMule', seconds: Math.round(e.timeout / 1000)}), false);
		}
		else {
			showStatus(tr('notReached', {client: 'aMule', url: emuleUrl}), false);
		}
	}
	finally {
		setSending(false);
		if (token != null) {
			gmRequest('POST', api + 'auth/logout', null, token).catch(function () {});
		}
	}
}

/**
* Send ed2k links to eMule through its web interface, without a window (SF-7.12)
* The request is the GET that a window of the older versions opened, made by GM_xmlhttpRequest:
* no window, nothing in the history of the browser, not subject to CORS nor to mixed content.
* eMule answers it with a short XML status (checked on eMule 0.70b), shown to the user.
* @param req the request made by getAddLink(): {url, count}
*/
async function sendToEmule(req) {
	var r, result;

	if (sendingBusy) {
		// a sending is waiting for its answer: the same links would be sent twice
		trace('sendToEmule() a sending is already in progress, ignored');
		return;
	}
	if (req.count == 0) {
		showStatus(tr('noLink'), false);
		return;
	}
	trace('sendToEmule() ' + req.count + ' link(s)');
	setSending(true);
	showStatus(tr('pleaseWait'), null);	// until the answer of eMule replaces it
	try {
		r = await gmRequest('GET', req.url, null, null, sendingTimeout(req.count));
		result = emuleResult(req.count, r);
		showStatus(result[0], result[1]);
	}
	catch (e) {
		trace('sendToEmule() ' + e);
		if (e.timeout) {
			// eMule received the request but answers late: the links may well be added
			showStatus(tr('notAnswered', {client: 'eMule', seconds: Math.round(e.timeout / 1000)}), false);
		}
		else {
			showStatus(tr('notReached', {client: 'eMule', url: emuleUrl}), false);
		}
	}
	finally {
		setSending(false);
	}
}

/**
* The message for the answer of eMule to a sending, and its kind
* eMule 0.70b answers <status result="OK">...</status>, or result="FAILED" with a reason
* (WRONG_PASSWORD). Another answer (another server, another version of eMule) is not
* understood: the links may still be added.
* @param count the number of links sent
* @param r the answer, from gmRequest()
* @return [message, kind]: kind true (added), false (refused), 'doubt' (not understood)
*/
function emuleResult(count, r) {
	var status = /<status\s+result="(\w+)"(?:\s+reason="(\w+)")?/i.exec(r.text);

	if (r.status == 200 && status && status[1].toUpperCase() == 'OK') {
		return [tr('linksAdded', {count: count, client: 'eMule'}), true];
	}
	if (status && status[2] && status[2].toUpperCase() == 'WRONG_PASSWORD') {
		return [tr('refusedPassword', {client: 'eMule'}), false];
	}
	if (status) {
		return [tr('emuleRefusedLinks', {why: status[2] ? ' (' + status[2] + ')' : ''}), false];
	}
	return [tr('emuleNotUnderstood'), 'doubt'];
}

/**
* Send ed2k links to aMule 2.x through its web interface (amuleweb), without a window (SF-7.13)
* amuleweb needs a session: a login request first (the password), awaited, then the links, the
* session being kept by its cookie (amuleweb_session_id), as a browser does. It answers the links
* with its form again, without any result: the links are then looked for in its downloads, by
* their hash (checked on aMule 2.3.3).
* @param req the request made by getAddLink(): {url, count, hashes}
*/
async function sendToAmuleWeb(req) {
	var r, login, found;

	if (sendingBusy) {
		trace('sendToAmuleWeb() a sending is already in progress, ignored');
		return;
	}
	if (req.count == 0) {
		showStatus(tr('noLink'), false);
		return;
	}
	trace('sendToAmuleWeb() ' + req.count + ' link(s)');
	setSending(true);
	showStatus(tr('pleaseWait'), null);
	try {
		r = await gmRequest('GET', emuleUrl + '?pass=' + encodeURIComponent(emulePwd), null, null);
		login = amuleWebLogin(r);
		if (login != null) {
			showStatus(login, false);
			return;
		}
		await gmRequest('GET', req.url, null, null, sendingTimeout(req.count));
		try {
			found = await amuleWebFound(emuleUrl, req.hashes);
		}
		catch (e) {
			// the links are sent: only their check failed, they may well be added
			trace('sendToAmuleWeb() ' + e);
			showStatus(tr('amuleListUnread'), 'doubt');
			return;
		}
		if (found == req.count) {
			showStatus(tr('linksAdded', {count: req.count, client: 'aMule'}), true);
		}
		else {
			showStatus(tr('amuleFound', {found: found, count: req.count}), 'doubt');
		}
	}
	catch (e) {
		trace('sendToAmuleWeb() ' + e);
		if (e.timeout) {
			showStatus(tr('notAnswered', {client: 'aMule', seconds: Math.round(e.timeout / 1000)}), false);
		}
		else {
			showStatus(tr('notReached', {client: 'aMule', url: emuleUrl}), false);
		}
	}
	finally {
		setSending(false);
	}
}

/**
* The category of a sending to amuleweb (aMule 2.x), encoded in its url
* amuleweb 2.3.3 compares the name it receives with the names of its categories as if it had read
* it in Latin-1: a name with accents sent in UTF-8 matches no category, and the links are then
* dropped without any message (its own form does so too). It is therefore sent as amuleweb reads
* it: each byte of its UTF-8 form taken as a character, then encoded. A name without accents is
* unchanged. Checked on aMule 2.3.3: the links land in the accented category.
* @param cat the name of the category
* @return the name encoded for the url
*/
function amuleWebCategory(cat) {
	var bytes = new TextEncoder().encode(String(cat));
	return encodeURIComponent(Array.prototype.map.call(bytes, function (b) { return String.fromCharCode(b); }).join(''));
}

/**
* The answer of amuleweb (aMule 2.x) to a login (?pass=): null when the session is open (a page that
* goes on to amuleweb-main-dload.php), or the message of the error
* @param r the answer, from gmRequest()
* @param url the address of aMule (the setting when not given)
*/
function amuleWebLogin(r, url) {
	if (r.status == 200 && /<form[^>]*name=["']?login/i.test(r.text)) {
		return tr('refusedPassword', {client: 'aMule'});
	}
	if (r.status == 200 && /amuleweb-main/i.test(r.text)) {
		return null;
	}
	return tr('noAmuleWeb', {url: url || emuleUrl});
}

/**
* How many of the links sent are in the downloads of amuleweb (aMule 2.x), found by their hash:
* each download has a checkbox named after its hash. aMule lists them at once (0.03 s on aMule
* 2.3.3); the list is read again for a few seconds while some are missing.
* @param url the address of aMule
* @param hashes the hashes of the links sent, in capitals
* @return a promise of the number of them found (a link already there counts as found)
*/
async function amuleWebFound(url, hashes) {
	var end = Date.now() + 5000;
	var listed, found;

	while (true) {
		listed = (await gmRequest('GET', url + 'amuleweb-main-dload.php', null, null)).text.toUpperCase();
		found = hashes.filter(function (h) { return h && listed.indexOf('NAME="' + h + '"') != -1; }).length;
		if (found == hashes.length || Date.now() > end) {
			return found;
		}
		await new Promise(function (resolve) { setTimeout(resolve, 500); });
	}
}

/**
* Send ed2k links to MLDonkey through its web interface, without a window (SF-7.14)
* MLDonkey asks for HTTP Basic (a user and a password): without them, the browser asked for them
* in its own dialog. The request is the one that a window used to open, with this authorization.
* MLDonkey answers a line per link (checked on MLDonkey 3.2.1): "Added link", or "Unable to match
* URL", with "already in download queue" for a link already there.
* @param req the request made by getAddLink(): {url, count}
*/
async function sendToMldonkey(req) {
	var r, result;

	if (sendingBusy) {
		trace('sendToMldonkey() a sending is already in progress, ignored');
		return;
	}
	if (req.count == 0) {
		showStatus(tr('noLink'), false);
		return;
	}
	trace('sendToMldonkey() ' + req.count + ' link(s)');
	setSending(true);
	showStatus(tr('pleaseWait'), null);
	try {
		r = await gmRequest('GET', req.url, null, basicAuth(emuleUser, emulePwd), sendingTimeout(req.count));
		result = mldonkeyResult(req.count, r, emuleUrl);
		showStatus(result[0], result[1]);
	}
	catch (e) {
		trace('sendToMldonkey() ' + e);
		if (e.timeout) {
			showStatus(tr('notAnswered', {client: 'MLDonkey', seconds: Math.round(e.timeout / 1000)}), false);
		}
		else {
			showStatus(tr('notReached', {client: 'MLDonkey', url: emuleUrl}), false);
		}
	}
	finally {
		setSending(false);
	}
}

/**
* The message for the answer of MLDonkey to a sending, and its kind
* @param count the number of links sent
* @param r the answer, from gmRequest()
* @param url the address of MLDonkey
* @return [message, kind]: kind true (every link added or already there), false (an error),
* 'doubt' (links refused by MLDonkey, which received them: a warning; or an answer of MLDonkey that
* tells nothing about the links)
*/
function mldonkeyResult(count, r, url) {
	var added = (r.text.match(/Added link/g) || []).length;
	var already = (r.text.match(/already in download queue/g) || []).length;
	var unmatched = (r.text.match(/Unable to match URL/g) || []).length;
	var refused = Math.max(0, unmatched - already);

	if (r.status == 401) {
		return [tr('mldonkeyRefused'), false];
	}
	if (r.status != 200 || !/MLdonkey/i.test(r.text)) {
		return [tr('noMldonkey', {url: url}), false];
	}
	if (added + unmatched == 0) {
		return [tr('mldonkeyNotUnderstood'), 'doubt'];
	}
	if (refused == 0) {
		return [tr('linksAdded', {count: count, client: 'MLDonkey'}), true];
	}
	return [tr('linksAddedRefused', {added: count - refused, client: 'MLDonkey', refused: refused, why: ''}), 'doubt'];
}

/**
* Mark a sending to aMule, eMule or MLDonkey as in progress or finished
* While it waits for its answer, the Download buttons and the server lists are disabled, and the sendings
* (sendToAmuleApi(), sendToEmule(), sendToAmuleWeb(), sendToMldonkey()) ignore any other one
* (shortcut, click on a file name).
* @param busy true when the sending starts, false when its answer has arrived
*/
function setSending(busy) {
	var buttons = document.querySelectorAll('#theDiv button.emlAdd, #theDiv select.emlSrv');

	sendingBusy = busy;
	for (var i=0; i<buttons.length; i++) {
		buttons[i].disabled = busy;
	}
}

/**
* How long to wait for the answer of aMule 3.x or eMule to a sending
* They answer only once every link is added, and this time grows with the number of links:
* measured on aMule 3.1.0, 8 s for 500 links, 77 s for 2,000 links; on eMule 0.70b, 7 s for 500.
* @param count the number of links sent
* @return the time limit in milliseconds: 60 s, plus 100 ms per link
*/
function sendingTimeout(count) {
	return 60000 + 100 * count;
}

/**
* The message for an error answer of the aMule API
* @param r the answer, from gmRequest()
* @param url the address of aMule (the setting when not given; the one typed in the settings
* dialog for Test and Import)
* @return the message shown to the user
*/
function amuleApiError(r, url) {
	var detail = (r.json && r.json.error && r.json.error.message) ? ' (' + r.json.error.message + ')' : '';
	switch (r.status) {
		case 401:
			return tr('refusedPassword', {client: 'aMule'});
		case 403:
			return tr('amuleAdmin');
		case 200:	// a page, not the answer of the API: an older aMule, or another server
		case 404:
			return tr('noAmuleApi', {url: url || emuleUrl});
		case 429:
			return tr('amuleTooMany', {retry: r.retryAfter ? tr('retryIn', {seconds: r.retryAfter}) : ''});
		case 503:
			return tr('amuleNoCore');
		default:
			return tr('amuleHttp', {status: r.status, detail: detail});
	}
}

/**
* The message for the answer of aMule to a sending
* @param links the links sent
* @param r the answer, from gmRequest(): 202 all added, 207 some refused
* @return the message shown to the user
*/
function amuleApiResult(links, r) {
	var results = (r.json && r.json.results) ? r.json.results : [];
	var refused = results.filter(function (x) { return !x.ok; });
	var why = '';

	if (r.status == 202) {
		return tr('linksAdded', {count: links.length, client: 'aMule'});
	}
	if (r.status == 207) {
		if (refused.length > 0 && refused[0].error && refused[0].error.message) {
			why = ': ' + refused[0].error.message;
		}
		return tr('linksAddedRefused', {added: links.length - refused.length, client: 'aMule', refused: refused.length, why: why});
	}
	return amuleApiError(r);
}

/**
* Show the result of a sending to the user, in a band (SF-7.10): under the top toolbar, over the top of
* the list or of the edit box, so that the popup keeps its size; minimized, floating against the popup, as
* wide as its message; the popup closed, alone in the corner of the popup, instead of an alert. A
* success goes away after STATUS_DELAY; an error or a doubt stays until its Close button or the next
* sending. While waiting (ok = null), the message is followed by animated dots, until the next message
* replaces it.
* @param msg the message
* @param ok true for a success (green), false for an error (red: the sending failed), 'doubt' for a
* warning (orange): links left out by the client, which received them, or an answer that is not
* understood (the links may still be added); null while waiting
*/
function showStatus(msg, ok) {
	var container = document.getElementById('theDiv');
	var line = document.getElementById('emlStatus');
	var kind = (ok == null) ? 'wait' : (ok === 'doubt') ? 'doubt' : ok ? 'ok' : 'ko';
	var text;
	var dots = 0;

	trace('showStatus() ' + msg);
	// the look of the band, in the PARAM block: once in the page, as the band may be out of the popup
	if (document.getElementById('emlStatusCss') == null) {
		var css = document.createElement('style');
		css.id = 'emlStatusCss';
		css.textContent = STATUS_CSS;
		(document.head || document.body).appendChild(css);
	}
	if (statusTimer != null) {
		clearInterval(statusTimer);
		statusTimer = null;
	}
	if (statusHide != null) {
		clearTimeout(statusHide);
		statusHide = null;
	}
	if (line == null) {
		line = document.createElement('div');
		line.id = 'emlStatus';
		// while waiting, its three dots are shown one after the other, hidden but in place: the band keeps
		// its width, and its Close button does not move
		line.innerHTML = '<span class="emlStatusIcon"></span><span class="emlStatusText"></span><span class="emlStatusDots"></span>';
		var close = iconButton('close', tr('statusCloseTitle'), delStatus, '');
		line.appendChild(close);
		(container || document.body).appendChild(line);	// moved by placeStatus() when needed
		window.addEventListener('resize', placeStatus, false);
	}
	line.className = kind;
	line.style.color = (kind == 'wait') ? '#555' : (kind == 'doubt') ? '#a65f00' : (kind == 'ok') ? '#060' : '#c00';
	line.querySelector('.emlStatusIcon').innerHTML = (kind == 'wait') ? '' : ICONS[kind == 'ok' ? 'ok' : 'warn'];
	text = line.querySelector('.emlStatusText');
	text.textContent = msg;
	// the three dots of the waiting only, none in an answer
	line.querySelector('.emlStatusDots').innerHTML = (kind == 'wait') ? '<span>.</span><span>.</span><span>.</span>' : '';
	var marks = line.querySelectorAll('.emlStatusDots span');
	var showDots = function (count) {
		for (var d=0; d<marks.length; d++) {
			marks[d].style.visibility = (d < count) ? 'visible' : 'hidden';
		}
	};
	placeStatus();
	if (kind == 'wait') {
		statusTimer = setInterval(function () {
			dots = (dots + 1) % 4;
			showDots(dots);
		}, 400);
	}
	else if (kind == 'ok') {
		statusHide = setTimeout(delStatus, STATUS_DELAY);
	}
}

/**
* Place the band of the answer (showStatus()): in the popup, under the top toolbar, over the list; minimized,
* floating against the popup, glued to it (under it, above it at the bottom of the window, on its left edge, its right one
* in a corner at the right), as wide as its message, the popup keeping its size; the popup closed, alone in
* its corner. Floating, the band has its own border (.toast). Called again when the view or the window changes.
*/
function placeStatus() {
	var line = document.getElementById('emlStatus');
	var container = document.getElementById('theDiv');
	var bar = document.getElementById('emlTop');
	var corner = popupCorner.split('-');	// the corner of the popup: top or bottom, left or right

	if (line == null) {
		return;
	}
	line.style.top = line.style.bottom = line.style.left = line.style.right = line.style.position = '';
	if (container && !popupMinimized) {
		if (line.parentNode != container) {
			container.appendChild(line);
		}
		line.classList.remove('toast');
		line.style.top = (bar ? bar.offsetTop + bar.offsetHeight : 0) + 'px';
		return;
	}
	if (line.parentNode != document.body) {
		document.body.appendChild(line);
	}
	line.classList.add('toast');
	if (container == null) {
		line.style[corner[0]] = '0';
		line.style[corner[1]] = '0';
		return;
	}
	// against the minimized popup, positioned as it: fixed in the window, or scrolling with the page; anchored
	// by the side of its corner, so that a long message grows away from it, as the popup itself
	var r = container.getBoundingClientRect();
	var fixed = getComputedStyle(container).position == 'fixed';
	var sx = fixed ? 0 : window.scrollX;
	var sy = fixed ? 0 : window.scrollY;
	line.style.position = fixed ? 'fixed' : 'absolute';
	if (corner[1] == 'right') {
		line.style.right = Math.max(0, document.documentElement.clientWidth - r.right - sx) + 'px';
	}
	else {
		line.style.left = Math.max(0, r.left + sx) + 'px';
	}
	if (corner[0] == 'bottom') {
		line.style.bottom = Math.max(0, document.documentElement.clientHeight - r.top - sy) + 'px';
	}
	else {
		line.style.top = (r.bottom + sy) + 'px';
	}
}

/**
* Remove the band of the answer, if any (its Close button, after STATUS_DELAY for a success)
*/
function delStatus() {
	var line = document.getElementById('emlStatus');

	if (statusTimer != null) {
		clearInterval(statusTimer);
		statusTimer = null;
	}
	if (statusHide != null) {
		clearTimeout(statusHide);
		statusHide = null;
	}
	if (line) {
		line.parentNode.removeChild(line);
	}
	window.removeEventListener('resize', placeStatus, false);
}

// -------------------------------------------------------------------------
// Settings: the settings read and saved, the settings dialog and its servers (SF-8)
// -------------------------------------------------------------------------

/**
* calling the settings dialog
*/
function resetConfig() {
	GM_setValue("emule_config",0);
	scriptConfig();
}

/**
* Configure and invoke the settings dialog
*/
function scriptConfig() {
	trace("scriptConfig() configuring the dialog");

	// Create a div to use as the config window — avoids iframe cross-origin issues in Chrome/Tampermonkey
	var configDiv = document.createElement('div');
	document.body.appendChild(configDiv);

	// Configure Settings dialog: the fields, then the look and the behavior of the dialog, given to
	// GM_config through its custom CSS and its open/close callbacks (settingsDialogOpened())
	GM_config.init(configDiv, settingsTitle(), SETTINGS_CSS, {
		'section0' : { section: [tr('section0'), tr('section0Help')], label: '', type: 'hidden'},
		'language': { label: tr('languageLabel'), title : tr('languageHelp'), type: 'select', options:{'browser':tr('language.browser'),'en':tr('language.en'),'fr':tr('language.fr')}, default: language },
		'popupView': { label: tr('popupViewLabel'), title : tr('popupViewHelp'), type: 'select', options:{'maximized':tr('popupView.maximized'),'minimized':tr('popupView.minimized'),'closed':tr('popupView.closed')}, default: popupView },
		'closeMessage': { label: tr('closeMessageLabel'), title : tr('closeMessageHelp'), type: 'checkbox', default: closeMessage },
		'section1' : { section: [tr('section1'), tr('section1Help')], label: '', type: 'hidden'},
		'ed2kDlMethod': { label: tr('ed2kDlMethodLabel'), title : tr('ed2kDlMethodHelp'), type:'select', options:{'local':tr('ed2kDlMethod.local'),'emule':tr('ed2kDlMethod.emule'),'amuleapi':tr('ed2kDlMethod.amuleapi'),'amule':tr('ed2kDlMethod.amule'),'mldonkey':tr('ed2kDlMethod.mldonkey'),'custom':tr('ed2kDlMethod.custom')}, default: ed2kDlMethod}, // default value doesn't work with a dropdown menu => see bugfix in the lib
		'emuleUrl': { label: tr('emuleUrlLabel'), title : tr('emuleUrlHelp'), type: 'text', size: 32, default: emuleUrl },
		'emuleUser': { label: tr('emuleUserLabel'), title : tr('emuleUserHelp'), type: 'text', size: 20, default: emuleUser },
		'emulePwd': { label: tr('emulePwdLabel'), title : tr('emulePwdHelp'), type: 'text', size: 20, default: emulePwd },
		'emuleCat': { label: tr('emuleCatLabel'), title : tr('emuleCatHelp'), type: 'text', size: 40, default: catToStr(emuleCat) },
		'section2' : { section: [tr('section2'), tr('section2Help')], label: '', type: 'hidden'},
		'showCategories': { label: tr('showCategoriesLabel'), title : tr('showCategoriesHelp'), type: 'checkbox', default: showCategories },
		'showServerList': { label: tr('showServerListLabel'), title : tr('showServerListHelp'), type: 'checkbox', default: showServerList },
		'popupCorner': { label: tr('popupCornerLabel'), title : tr('popupCornerHelp'), type: 'select', options:{'top-left':tr('popupCorner.top-left'),'top-right':tr('popupCorner.top-right'),'bottom-left':tr('popupCorner.bottom-left'),'bottom-right':tr('popupCorner.bottom-right')}, default: popupCorner },
		'popupScroll': { label: tr('popupScrollLabel'), title : tr('popupScrollHelp'), type: 'select', options:{'floating':tr('popupScroll.floating'),'static':tr('popupScroll.static')}, default: popupScroll },
		'popupHeight': { label: tr('popupHeightLabel'), title : tr('popupHeightHelp'), type: 'int', size: 6, default: popupHeight },
		'popupWidth': { label: tr('popupWidthLabel'), title : tr('popupWidthHelp'), type: 'int', size: 6, default: popupWidth },
		'checkFilter': { label: tr('checkFilterLabel'), title : tr('checkFilterHelp'), type: 'text', size: 40, default: checkFilter },
		'section3' : { section: [tr('section3'), tr('section3Help')], label: '', type: 'hidden'},
		'editCol': { label: tr('editColLabel'), title : tr('editColHelp'), type: 'int', size: 4, default: editCol },
		'editRow': { label: tr('editRowLabel'), title : tr('editRowHelp'), type: 'int', size: 4, default: editRow },
	},
	{
		//open: function() { GM_config.sections2tabs(); }, // not working (not included into the library)
		open: function() { settingsDialogOpened(); },
		close: function() { settingsDialogClosed(); },
		save: function() { storeServers(); location.reload(); } // reload the page when configuration was changed
	}
	);

	// invoke the dialog
	if (GM_getValue("emule_config", 0)<1)
	{
		trace("scriptConfig() invoking the dialog");
		GM_config.open();
		GM_setValue("emule_config",1);
	}

	// store the settings
	saveConfig();

}

// The settings dialog: look and behavior added to the dialog built by GM_config

/**
* The title of the settings dialog, with the version of the script given by the userscript manager
*/
function settingsTitle() {
	return boxTitle(tr('settings'));
}

/**
* Write the help of a field: the text between backquotes is code (an address, a value, a regular
* expression), shown in a monospace font. The tooltip of a row, its textContent, has no backquote.
* @param help the element of the help
* @param text the help, its code between backquotes
*/
function setHelpText(help, text) {
	var parts = String(text).split('`');
	help.textContent = '';
	for (var i=0; i<parts.length; i++) {
		if (i % 2 == 1) {
			var code = document.createElement('code');
			code.textContent = parts[i];
			help.appendChild(code);
		}
		else {
			help.appendChild(document.createTextNode(parts[i]));
		}
	}
}

/**
* Called by GM_config once the settings dialog is built: helps under the fields, masked password,
* the servers as a list each with its own method and settings, values checked before saving,
* Escape and a backdrop to close it
*/
function settingsDialogOpened() {
	var root = document.getElementById('GM_config');
	var rows = root.querySelectorAll('.config_var');
	var pwd = document.getElementById('GM_config_field_emulePwd');
	var reveal;

	trace('settingsDialogOpened()');
	for (var i=0; i<rows.length; i++) {
		var row = rows[i];
		var text = row.getAttribute('title');
		row.removeAttribute('title');	// no slow tooltip of the browser
		if (row.querySelector('input[type=hidden]')) {
			row.style.display = 'none';		// the fields that only hold a section title
			continue;
		}
		if (text) {
			// the help is shown under the field instead
			var help = document.createElement('div');
			help.className = 'help';
			setHelpText(help, text);
			row.appendChild(help);
		}
	}

	// the password is masked, a button shows it
	pwd.type = 'password';
	pwd.autocomplete = 'off';
	reveal = document.createElement('button');
	reveal.type = 'button';
	reveal.className = 'reveal';
	reveal.textContent = tr('show');
	reveal.addEventListener('click', function () {
		pwd.type = (pwd.type == 'password') ? 'text' : 'password';
		reveal.textContent = tr((pwd.type == 'password') ? 'show' : 'hide');
	}, false);
	// the password and its button share the whole width of the column, as the other long fields
	var pwdbox = document.createElement('div');
	pwdbox.className = 'pwdbox';
	pwd.parentNode.insertBefore(pwdbox, pwd);
	pwdbox.appendChild(pwd);
	pwdbox.appendChild(reveal);

	// the servers as a list, each one with its name, method and settings
	setupServers();

	// Test and Import, for aMule 3.x (amuleapi)
	addApiButtons();

	// the values are checked before GM_config saves them: this listener on the holder of the
	// buttons runs before the one of the Save button, and stops the click when a value is wrong.
	// The fields of GM_config then receive the settings of the checked server, which it saves.
	document.getElementById('GM_config_buttons_holder').addEventListener('click', function (e) {
		if (e.target.id != 'GM_config_saveBtn') {
			return;
		}
		if (!checkSettings() || !keepEditedServer()) {
			e.stopPropagation();
			e.preventDefault();
			return;
		}
		prepareServersForSaving();
	}, true);

	// the buttons of GM_config, in the language of the script (I-7)
	document.getElementById('GM_config_saveBtn').textContent = tr('save');
	document.getElementById('GM_config_saveBtn').title = tr('saveTitle');
	document.getElementById('GM_config_closeBtn').textContent = tr('close');
	document.getElementById('GM_config_closeBtn').title = tr('closeWindowTitle');

	// in the header: [?], which shows or hides the helps of every field, the choice being kept, and a Close icon
	addHelpButton();

	// at the bottom of the window, the popup always stays in view: Popup scrolling follows Popup position
	settingsField('popupCorner').addEventListener('change', syncPopupScroll, false);
	syncPopupScroll();

	// a Reset button that tells what it changed, and can be undone
	addResetButton();

	// a backdrop behind the dialog, and Escape to close it
	if (!document.getElementById('GM_config_backdrop')) {
		var backdrop = document.createElement('div');
		backdrop.id = 'GM_config_backdrop';
		backdrop.setAttribute('style', 'position:fixed; top:0; left:0; right:0; bottom:0; z-index:998;'
			+ ' background:rgba(0,0,0,.35);');
		document.body.appendChild(backdrop);
	}
	document.addEventListener('keydown', closeSettingsOnEscape, true);

	// the links to the repository, at the bottom
	addFooter();
}

/**
* Add the links to the repository at the bottom of the settings dialog: to report a problem, and
* to the project. They open in a new tab.
*/
function addFooter() {
	var footer = document.createElement('div');
	var links = [['GM_config_issuesLink', REPOSITORY + '/issues', tr('reportProblem')],
		['GM_config_repoLink', REPOSITORY, tr('repository')]];

	footer.className = 'footer';
	for (var i=0; i<links.length; i++) {
		var a = document.createElement('a');
		a.id = links[i][0];
		a.href = links[i][1];
		a.target = '_blank';
		a.rel = 'noopener noreferrer';
		a.textContent = links[i][2];
		footer.appendChild(a);
	}
	document.getElementById('GM_config_wrapper').appendChild(footer);
}

/**
* Called by GM_config when the settings dialog is closed
*/
function settingsDialogClosed() {
	var backdrop = document.getElementById('GM_config_backdrop');
	if (backdrop) {
		backdrop.parentNode.removeChild(backdrop);
	}
	document.removeEventListener('keydown', closeSettingsOnEscape, true);
	dialogServers = null;
	dialogEdited = null;
}

/**
* A field of the settings dialog
*/
function settingsField(id) {
	return document.getElementById('GM_config_field_' + id);
}

/**
* The name displayed for a download method, as in the settings dialog
*/
function methodLabel(method) {
	var options = GM_config.fields.ed2kDlMethod.settings.options;
	return options[method] || method;
}

/**
* A new server, with the default settings
*/
function newServer(name, method) {
	var server = {id: '', name: name, method: method};
	var ids = dialogServers.list.map(function (srv) { return parseInt(srv.id.replace(/\D/g, ''), 10) || 0; });
	server.id = 'srv' + (Math.max.apply(null, [0].concat(ids)) + 1);
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		server[METHOD_SETTINGS[i]] = GM_config.fields[METHOD_SETTINGS[i]].settings['default'];
	}
	return server;
}

/**
* A setting of a server, or its default value when the server has none (a server stored by an
* older version, before the setting existed: User, in 0.12)
*/
function serverSetting(server, id) {
	return server[id] != null ? server[id] : GM_config.fields[id].settings['default'];
}

/**
* The server of the settings dialog that has this id
*/
function findServer(id) {
	return dialogServers.list.filter(function (srv) { return srv.id == id; })[0] || null;
}

/**
* Show the servers of the settings dialog as a list: each one has a name, a download method and
* its settings, and a radio button chooses the one that receives the links (or Local)
* The servers are kept in "servers"; the checked one also has its method and settings in
* GM_config, which the rest of the script reads: they are taken from there, which also turns the
* single set of settings of the older versions into a server.
*/
function setupServers() {
	var select = settingsField('ed2kDlMethod');
	var row = document.getElementById('GM_config_ed2kDlMethod_var');
	var list = document.createElement('div');
	var fields = document.createElement('div');
	var add = document.createElement('div');
	var addBtn = document.createElement('button');
	var stored = GM_getValue('servers', '');
	var active;

	dialogServers = {active: null, list: []};
	try {
		if (stored) {
			dialogServers = JSON.parse(stored);
		}
	}
	catch (e) {
		trace('setupServers() servers ignored: ' + e);
	}
	if (select.value != 'local') {
		active = findServer(dialogServers.active);
		if (active == null) {
			active = newServer(methodLabel(select.value), select.value);
			dialogServers.list.push(active);
			dialogServers.active = active.id;
		}
		active.method = select.value;
		for (var i=0; i<METHOD_SETTINGS.length; i++) {
			active[METHOD_SETTINGS[i]] = settingsField(METHOD_SETTINGS[i]).value;
		}
	}
	else {
		dialogServers.active = null;
	}
	// Local can be disabled only when another server receives the links (I-14)
	dialogServers.localDisabled = !!dialogServers.localDisabled && dialogServers.active != null && dialogServers.list.length > 0;
	dialogEdited = dialogServers.active;

	list.className = 'slist';
	list.id = 'GM_config_servers';
	row.insertBefore(list, row.querySelector('.help'));
	row.querySelector('.help').textContent = tr('serversHelp');

	// the settings of a server: its name, its method, then the fields of GM_config that the method uses
	fields.className = 'sfields';
	fields.id = 'GM_config_server_fields';
	fields.appendChild(settingRow('serverName', tr('serverNameLabel'), 'input', tr('serverNameHelp')));
	fields.appendChild(settingRow('serverMethod', tr('ed2kDlMethodLabel'), 'select',
		GM_config.fields.ed2kDlMethod.settings.title));
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		fields.appendChild(document.getElementById('GM_config_' + METHOD_SETTINGS[i] + '_var'));
	}
	list.appendChild(fields);

	add.className = 'sadd';
	addBtn.type = 'button';
	addBtn.id = 'GM_config_addServer';
	addBtn.textContent = tr('addServer');
	addBtn.addEventListener('click', addServer, false);
	add.appendChild(addBtn);
	list.appendChild(add);

	// the row of the server being edited follows what is typed
	settingsField('serverName').addEventListener('input', function () {
		var label = document.querySelector('#GM_config_server_' + dialogEdited + ' label');
		if (label) {
			label.textContent = this.value;
		}
	}, false);
	settingsField('emuleUrl').addEventListener('input', function () {
		var sum = document.querySelector('#GM_config_server_' + dialogEdited + ' .sum');
		if (sum) {
			sum.textContent = this.value;
		}
	}, false);
	settingsField('serverMethod').addEventListener('change', function () {
		var badge = document.querySelector('#GM_config_server_' + dialogEdited + ' .method');
		if (badge) {
			badge.textContent = methodLabel(this.value);
		}
		removeApiStatus('test');
		removeApiStatus('import');
		showServerFields();
	}, false);

	showServers();
}

/**
* A row of the settings of a server, built as the rows of GM_config: label, field, help
*/
function settingRow(id, text, tag, helpText) {
	var row = document.createElement('div');
	var label = document.createElement('label');
	var field = document.createElement(tag);
	var help = document.createElement('div');
	var options = GM_config.fields.ed2kDlMethod.settings.options;

	row.className = 'config_var';
	row.id = 'GM_config_' + id + '_var';
	label.className = 'field_label';
	label.textContent = text;
	label.htmlFor = 'GM_config_field_' + id;
	field.id = 'GM_config_field_' + id;
	if (tag == 'input') {
		field.type = 'text';
	}
	else {
		for (var method in options) {
			if (method != 'local') {	// the local method needs no server
				var option = document.createElement('option');
				option.value = method;
				option.textContent = options[method];
				field.appendChild(option);
			}
		}
	}
	help.className = 'help';
	setHelpText(help, helpText);
	row.appendChild(label);
	row.appendChild(field);
	row.appendChild(help);
	return row;
}

/**
* A row of the list of the servers: a radio button to choose the server that receives the links,
* its name, its method, its address, and the buttons to edit or delete it
*/
function serverRow(server) {
	var row = document.createElement('div');
	var radio = document.createElement('input');
	var label = document.createElement('label');
	var badge = document.createElement('span');
	var sum = document.createElement('span');
	var acts = document.createElement('span');
	var id = server ? server.id : 'local';

	row.className = 'srow';
	row.id = 'GM_config_server_' + id;
	row.setAttribute('data-server', id);
	radio.type = 'radio';
	radio.name = 'GM_config_server';
	radio.id = 'GM_config_server_radio_' + id;
	radio.value = id;
	radio.checked = server ? (dialogServers.active == id) : (dialogServers.active == null);
	radio.addEventListener('change', function () { chooseServer(server ? id : null); }, false);
	label.htmlFor = radio.id;
	label.textContent = server ? server.name : tr('local');
	badge.className = 'method';
	badge.textContent = server ? methodLabel(server.method) : tr('localBadge');
	badge.title = badge.textContent;	// the whole name, when the badge is too narrow for it
	sum.className = 'sum' + (server ? '' : ' none');
	sum.textContent = server ? server.emuleUrl : tr('nothingToConfigure');
	acts.className = 'acts';
	if (server) {
		var edit = document.createElement('button');
		var del = document.createElement('button');
		edit.type = 'button';
		edit.className = 'edit';
		edit.textContent = tr('edit');
		edit.style.visibility = (dialogEdited == id) ? 'hidden' : '';
		edit.addEventListener('click', function () { editServer(id); }, false);
		del.type = 'button';
		del.className = 'del';
		del.textContent = tr('delete');
		del.addEventListener('click', function () { deleteServer(id); }, false);
		acts.appendChild(edit);
		acts.appendChild(del);
	}
	else if (dialogServers.list.length > 0) {
		// Local: Disable, in the color of Delete, or Enable, in the color of Edit (I-14); not while it is checked
		var toggle = document.createElement('button');
		toggle.type = 'button';
		toggle.className = dialogServers.localDisabled ? 'enable' : 'del';
		toggle.textContent = tr(dialogServers.localDisabled ? 'enable' : 'disable');
		toggle.disabled = !dialogServers.localDisabled && dialogServers.active == null;
		toggle.title = tr(dialogServers.localDisabled ? 'enableTitle' : toggle.disabled ? 'disableBlocked' : 'disableTitle');
		toggle.addEventListener('click', toggleLocal, false);
		acts.appendChild(toggle);
	}
	if (!server && dialogServers.localDisabled) {
		row.classList.add('off');
		radio.disabled = true;
	}
	row.classList.toggle('sel', radio.checked);
	row.appendChild(radio);
	row.appendChild(label);
	row.appendChild(badge);
	row.appendChild(sum);
	row.appendChild(acts);
	return row;
}

/**
* Display the list of the servers as it is, and under the server being edited its settings
*/
function showServers() {
	var list = document.getElementById('GM_config_servers');
	var fields = document.getElementById('GM_config_server_fields');
	var add = list.querySelector('.sadd');
	var rows = list.querySelectorAll('.srow');
	var server = findServer(dialogEdited);

	for (var i=0; i<rows.length; i++) {
		rows[i].parentNode.removeChild(rows[i]);
	}
	list.insertBefore(serverRow(null), list.firstChild);
	for (var i=0; i<dialogServers.list.length; i++) {
		list.insertBefore(serverRow(dialogServers.list[i]), add);
	}
	if (server == null) {
		dialogEdited = null;
		fields.style.display = 'none';
		list.insertBefore(fields, add);
		return;
	}
	var edited = document.getElementById('GM_config_server_' + server.id);
	edited.parentNode.insertBefore(fields, edited.nextSibling);
	fields.style.display = '';
	settingsField('serverName').value = server.name;
	settingsField('serverMethod').value = server.method;
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		settingsField(METHOD_SETTINGS[i]).value = serverSetting(server, METHOD_SETTINGS[i]);
	}
	showServerFields();
}

/**
* Show, in the settings of the server being edited, the fields that its method uses only, and
* the Test button for eMule, aMule and MLDonkey, the Import button for eMule and aMule (MLDonkey has no categories)
*/
function showServerFields() {
	var method = settingsField('serverMethod').value;
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		document.getElementById('GM_config_' + METHOD_SETTINGS[i] + '_var').style.display =
			(METHOD_FIELDS[method].indexOf(METHOD_SETTINGS[i]) != -1) ? '' : 'none';
	}
	document.getElementById('GM_config_server_fields').classList.toggle('notest', !TEST_ACTIONS.hasOwnProperty(method));
	document.getElementById('GM_config_server_fields').classList.toggle('noimport', !IMPORT_ACTIONS.hasOwnProperty(method));
}

/**
* The wrong values of the server being edited: a missing or duplicate name, a Server URL that
* does not start with http:// or https://, a category list without any valid entry
* @return [[field id, message], ...]
*/
function serverErrors() {
	var errors = [];
	var name, method;

	if (dialogEdited == null) {
		return errors;
	}
	name = settingsField('serverName').value.trim();
	method = settingsField('serverMethod').value;
	if (name == '') {
		errors.push(['serverName', tr('nameRequired')]);
	}
	else if (dialogServers.list.some(function (srv) {
			return srv.id != dialogEdited && srv.name.trim().toLowerCase() == name.toLowerCase(); })) {
		errors.push(['serverName', tr('nameTaken')]);
	}
	if (METHOD_FIELDS[method].indexOf('emuleUrl') != -1 && !SERVER_URL.test(settingsField('emuleUrl').value.trim())) {
		errors.push(['emuleUrl', tr('serverUrlError')]);
	}
	if (METHOD_FIELDS[method].indexOf('emuleCat') != -1 && strToCat(settingsField('emuleCat').value.trim()) == -1) {
		errors.push(['emuleCat', tr('categoryError')]);
	}
	return errors;
}

/**
* Keep in memory the settings displayed for the server being edited, once they are right
* @return false when a value is wrong: it is then shown under its field
*/
function keepEditedServer() {
	var server = findServer(dialogEdited);
	var errors;

	if (server == null) {
		return true;
	}
	clearSettingsErrors();
	errors = serverErrors();
	if (errors.length > 0) {
		for (var i=0; i<errors.length; i++) {
			showSettingsError(errors[i][0], errors[i][1]);
		}
		settingsField(errors[0][0]).focus();
		return false;
	}
	server.name = settingsField('serverName').value.trim();
	server.method = settingsField('serverMethod').value;
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		server[METHOD_SETTINGS[i]] = settingsField(METHOD_SETTINGS[i]).value;
	}
	return true;
}

/**
* Choose the server that receives the links (radio button), null for Local: its settings are displayed
*/
function chooseServer(id) {
	if (!keepEditedServer()) {
		showServers();		// the radio button goes back to the server checked before
		return;
	}
	trace('chooseServer() ' + id);
	clearSettingsMarks();	// the notice of a deletion: its Undo would also undo this change
	dialogServers.active = id;
	dialogEdited = id;
	showServers();
}

/**
* Disable Local, or enable it again (I-14): disabled, it can no longer be checked, and the popup neither
* offers nor counts it. Not while it is checked: the server that receives the links never changes without
* the user. Saved with the servers.
*/
function toggleLocal() {
	if (!dialogServers.localDisabled && dialogServers.active == null) {
		return;
	}
	if (!keepEditedServer()) {
		return;
	}
	trace('toggleLocal() ' + (dialogServers.localDisabled ? 'enabled' : 'disabled'));
	clearSettingsMarks();
	dialogServers.localDisabled = !dialogServers.localDisabled;
	showServers();
}

/**
* Display the settings of a server without choosing it (Edit button)
*/
function editServer(id) {
	if (!keepEditedServer()) {
		return;
	}
	clearSettingsMarks();
	dialogEdited = id;
	showServers();
	settingsField('serverName').focus();
}

/**
* Add a server, with the default settings: its settings are displayed, to name and configure it
*/
function addServer() {
	var name = tr('newServer');
	var n = 1;
	var server;

	if (!keepEditedServer()) {
		return;
	}
	clearSettingsMarks();
	while (dialogServers.list.some(function (srv) { return srv.name.toLowerCase() == name.toLowerCase(); })) {
		name = tr('newServerN', {n: ++n});
	}
	server = newServer(name, 'emule');
	dialogServers.list.push(server);
	dialogEdited = server.id;
	showServers();
	settingsField('serverName').focus();
	settingsField('serverName').select();
}

/**
* Delete a server at once; a notice with an Undo button takes its place in the list, where the
* user clicked, so that it is in view. Deleting the checked server checks Local.
*/
function deleteServer(id) {
	var before;
	var server = findServer(id);
	var index = dialogServers.list.indexOf(server);
	var next;

	if (id != dialogEdited && !keepEditedServer()) {
		return;
	}
	before = {servers: JSON.stringify(dialogServers), edited: dialogEdited};
	clearSettingsMarks();
	dialogServers.list = dialogServers.list.filter(function (srv) { return srv.id != id; });
	if (dialogServers.list.length == 0) {
		dialogServers.localDisabled = false;	// Local, the only choice left, enabled again (I-14)
	}
	if (dialogServers.active == id) {
		// the checked server deleted: Local checked, or the first server left when Local is disabled
		dialogServers.active = dialogServers.localDisabled ? dialogServers.list[0].id : null;
	}
	if (dialogEdited == id) {
		dialogEdited = null;
	}
	showServers();
	// the notice goes before the server that followed the deleted one, or before "+ Add a server"
	next = dialogServers.list[index] ? document.getElementById('GM_config_server_' + dialogServers.list[index].id)
		: document.querySelector('#GM_config_servers .sadd');
	showNotice(tr('serverDeleted', {name: server.name}), function () {
		dialogServers = JSON.parse(before.servers);
		dialogEdited = before.edited;
		showServers();
	}, next);
}

/**
* Before GM_config saves: its fields receive the method and the settings of the checked server, the
* ones the rest of the script reads (Local and the default settings when no server is checked)
*/
function prepareServersForSaving() {
	var server = findServer(dialogServers.active);
	var defaults = newServer('', 'emule');
	settingsField('ed2kDlMethod').value = server ? server.method : 'local';
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		settingsField(METHOD_SETTINGS[i]).value = serverSetting(server || defaults, METHOD_SETTINGS[i]);
	}
}

/**
* Store the servers, once GM_config has saved the other settings
*/
function storeServers() {
	if (dialogServers != null) {
		GM_setValue('servers', JSON.stringify(dialogServers));
	}
}

/**
* Show a notice, with an Undo button when undo is given: under the buttons of the settings dialog,
* or before the element "before" (in the list of the servers, for a deleted server)
*/
function showNotice(text, undo, before) {
	var bar = document.getElementById('GM_config_buttons_holder');
	var notice = document.createElement('div');
	var button;

	notice.className = 'notice';
	notice.id = 'GM_config_notice';
	notice.textContent = text;
	if (undo) {
		button = document.createElement('button');
		button.type = 'button';
		button.id = 'GM_config_undoBtn';
		button.textContent = tr('undo');
		button.addEventListener('click', function () {
			undo();
			clearSettingsMarks();
		}, false);
		notice.appendChild(button);
	}
	if (before) {
		before.parentNode.insertBefore(notice, before);
	}
	else {
		bar.appendChild(notice);
	}
}

/**
* Add the Test and Import buttons to the settings of a server: Test after Show, on the row of the
* password, and Import after the Category field, for eMule and aMule (showServerFields()). They use what is typed in the dialog, saved or not.
*/
function addApiButtons() {
	var cat = settingsField('emuleCat');
	var catbox = document.createElement('div');
	var make = function (id, text, title, action) {
		var button = document.createElement('button');
		button.type = 'button';
		button.id = id;
		button.className = 'apibtn';
		button.textContent = text;
		button.title = title;
		button.addEventListener('click', action, false);
		return button;
	};

	settingsField('emulePwd').parentNode.appendChild(		// the box of the password and of Show
		make('GM_config_testBtn', tr('test'), tr('testTitle'), testServer));
	catbox.className = 'catbox';
	cat.parentNode.insertBefore(catbox, cat);
	catbox.appendChild(cat);
	catbox.appendChild(make('GM_config_importBtn', tr('import'), tr('importTitle'), importCategories));

	// a result no longer matches the fields once they are changed
	settingsField('emuleUrl').addEventListener('input', function () { removeApiStatus('test'); }, false);
	settingsField('emulePwd').addEventListener('input', function () { removeApiStatus('test'); }, false);
	settingsField('emuleUser').addEventListener('input', function () { removeApiStatus('test'); }, false);
	cat.addEventListener('input', function () { removeApiStatus('import'); }, false);
}

/**
* Show the result of Test or Import under its field, framed in green (ok), orange (warn) or red (ko)
* @param which 'test' or 'import'
* @param text the message
* @param kind 'ok', 'warn' or 'ko'
* @param undo for an import, the function that puts the field back as it was: an Undo button on
* the right of the message, under Import
*/
function showApiStatus(which, text, kind, undo) {
	var status = document.createElement('div');
	var box, button;

	removeApiStatus(which);
	status.id = 'GM_config_' + which + 'Status';
	status.className = 'apistatus ' + kind;
	status.textContent = {ok: '✔ ', warn: '⚠ ', ko: '✖ '}[kind] + text;
	if (which == 'test') {
		box = settingsField('emulePwd').parentNode;
		box.parentNode.insertBefore(status, box.nextSibling);
		return;
	}
	box = settingsField('emuleCat').parentNode;
	box.appendChild(status);
	if (undo == null) {
		status.classList.add('wide');		// nothing under Import
		return;
	}
	button = document.createElement('button');
	button.type = 'button';
	button.id = 'GM_config_importUndoBtn';
	button.className = 'apibtn';
	button.textContent = tr('undo');
	button.addEventListener('click', function () {
		undo();
		removeApiStatus('import');
	}, false);
	box.appendChild(button);
}

/**
* Remove the result of Test or Import; for an import, also its Undo button and its highlight
* @param which 'test' or 'import'
*/
function removeApiStatus(which) {
	var olds = [document.getElementById('GM_config_' + which + 'Status')];
	var row = document.getElementById('GM_config_emuleCat_var');

	if (which == 'import') {
		olds.push(document.getElementById('GM_config_importUndoBtn'));
		if (row) {
			row.classList.remove('changed');
		}
	}
	for (var i=0; i<olds.length; i++) {
		if (olds[i]) {
			olds[i].parentNode.removeChild(olds[i]);
		}
	}
}

/**
* Start a Test or an Import: the address typed is checked, then Test and Import are disabled
* until the answer, the button clicked showing that it waits
* @param button the button clicked
* @param waiting its text while it waits
* @return what the request needs and what is checked when its answer arrives, or null when the
* address is wrong (shown under the field)
*/
function startApiAction(button, waiting) {
	var url = settingsField('emuleUrl').value.trim();
	var buttons = document.querySelectorAll('#GM_config_testBtn, #GM_config_importBtn');
	var ctx;

	clearSettingsMarks();		// the next action: the previous results and notices go away
	if (!SERVER_URL.test(url)) {
		showSettingsError('emuleUrl', tr('serverUrlError'));
		settingsField('emuleUrl').focus();
		return null;
	}
	if (url.charAt(url.length - 1) != '/') {
		url += '/';
	}
	for (var i=0; i<buttons.length; i++) {
		buttons[i].disabled = true;
	}
	ctx = {button: button, label: button.textContent, url: url, api: url + 'api/v1/', edited: dialogEdited,
		typed: [settingsField('emuleUrl').value, settingsField('emulePwd').value, settingsField('emuleCat').value,
			settingsField('emuleUser').value]};
	button.textContent = waiting;
	return ctx;
}

/**
* End a Test or an Import: the buttons are enabled again, the session closed, and the result shown,
* unless the dialog no longer shows what was tested (closed, another server, fields changed)
* @param ctx what startApiAction() returned
* @param token the token of the session, or null
* @param result {which, text, kind, apply, undo}: apply changes the dialog, undo puts it back
*/
function finishApiAction(ctx, token, result) {
	var buttons = document.querySelectorAll('#GM_config_testBtn, #GM_config_importBtn');
	var now;

	for (var i=0; i<buttons.length; i++) {
		buttons[i].disabled = false;
	}
	ctx.button.textContent = ctx.label;
	if (token != null) {
		gmRequest('POST', ctx.api + 'auth/logout', null, token).catch(function () {});
	}
	now = GM_config.isOpen && document.contains(ctx.button) ?
		[settingsField('emuleUrl').value, settingsField('emulePwd').value, settingsField('emuleCat').value,
			settingsField('emuleUser').value] : null;
	if (result == null || now == null || dialogEdited != ctx.edited || now.join('\n') != ctx.typed.join('\n')) {
		trace('finishApiAction() result ignored: the dialog has changed');
		return;
	}
	showApiStatus(result.which, result.text, result.kind, result.undo);
	if (result.apply) {
		result.apply();		// after the message: showing it removes the highlight of a previous import
	}
}

/**
* The message for a request of Test or Import that got no answer
* @param client the name of the client: aMule when not given, or eMule
*/
function apiFailure(e, url, client) {
	client = client || 'aMule';
	return e.timeout ? tr('notAnsweredShort', {client: client, seconds: Math.round(e.timeout / 1000)})
		: tr('notReached', {client: client, url: url});
}

/**
* Test button, for the method of the server displayed: eMule, aMule 3.x, aMule 2.x or MLDonkey
* (TEST_ACTIONS, SF-8.16, SF-8.17)
*/
function testServer() {
	var method = settingsField('serverMethod').value;
	if (TEST_ACTIONS.hasOwnProperty(method)) {
		TEST_ACTIONS[method](this);
	}
}

/**
* Test button, MLDonkey: its version (submit?q=version), asked with the user and the password typed
* (HTTP Basic) (SF-8.17). Nothing is saved, nothing is sent.
* @param button the Test button
*/
async function testMldonkey(button) {
	var ctx = startApiAction(button, tr('testing'));
	var result = null;
	var r, version;

	if (ctx == null) {
		return;
	}
	trace('testMldonkey() ' + ctx.url);
	try {
		r = await gmRequest('GET', ctx.url + 'submit?q=version', null, basicAuth(ctx.typed[3], ctx.typed[1]));
		version = /MLNet\s+(\d[\w.]*)/.exec(r.text);
		if (r.status == 401) {
			result = {which: 'test', kind: 'ko', text: tr('mldonkeyRefused')};
		}
		else if (r.status == 200 && /MLdonkey/i.test(r.text)) {
			result = {which: 'test', kind: 'ok', text: tr('connectedTo', {name: 'MLDonkey' + (version ? ' ' + version[1].replace(/\.git$/, '') : '')})};
		}
		else {
			result = {which: 'test', kind: 'ko', text: tr('noMldonkey', {url: ctx.url})};
		}
	}
	catch (e) {
		trace('testMldonkey() ' + e);
		result = {which: 'test', text: apiFailure(e, ctx.url, 'MLDonkey'), kind: 'ko'};
	}
	finally {
		finishApiAction(ctx, null, result);
	}
}

/**
* Test button, aMule 2.x: log in to amuleweb with the address and the password typed, then read the
* version of aMule in the first lines of its log (log.php: "Initialising aMuleD 2.3.3 ...") (SF-8.17).
* amuleweb has no logout: its session ends by itself. Nothing is saved, nothing is sent.
* @param button the Test button
*/
async function testAmuleWeb(button) {
	var ctx = startApiAction(button, tr('testing'));
	var result = null;
	var r, error, version;

	if (ctx == null) {
		return;
	}
	trace('testAmuleWeb() ' + ctx.url);
	try {
		r = await gmRequest('GET', ctx.url + '?pass=' + encodeURIComponent(ctx.typed[1]), null, null);
		error = amuleWebLogin(r, ctx.url);
		if (error != null) {
			result = {which: 'test', kind: 'ko', text: error};
			return;
		}
		r = await gmRequest('GET', ctx.url + 'log.php', null, null);
		version = /Initialising aMule\w*\s+([\d][\w.]*)/.exec(r.text);
		result = {which: 'test', kind: 'ok', text: tr('connectedTo', {name: 'aMule ' + (version ? version[1] : '2.x')})};
	}
	catch (e) {
		trace('testAmuleWeb() ' + e);
		result = {which: 'test', text: apiFailure(e, ctx.url), kind: 'ko'};
	}
	finally {
		finishApiAction(ctx, null, result);
	}
}

/**
* Test button, eMule: log in to its web interface with the address and the password typed, as
* the login page of eMule does, then log out (SF-8.17). eMule 0.70b answers with its interface,
* which holds a session and its version in its title, or with its login page again when the
* password is wrong. Nothing is saved, nothing is sent.
* @param button the Test button
*/
async function testEmule(button) {
	var ctx = startApiAction(button, tr('testing'));
	var result = null;
	var r, session, title;

	if (ctx == null) {
		return;
	}
	trace('testEmule() ' + ctx.url);
	try {
		r = await gmRequest('GET', ctx.url + '?w=password&p=' + encodeURIComponent(ctx.typed[1]), null, null);
		session = /[?&]ses=(-?\d+)/.exec(r.text);
		title = /<title>\s*([^<]*?)\s*-\s*Web Interface\s*<\/title>/i.exec(r.text);
		if (r.status == 200 && session) {
			result = {which: 'test', kind: 'ok',
				text: tr('connectedTo', {name: title && /emule/i.test(title[1]) ? title[1] : 'eMule'})};
			// the session opened by this test is closed at once
			gmRequest('GET', ctx.url + '?ses=' + session[1] + '&w=logout', null, null).catch(function () {});
		}
		else if (r.status == 200 && /<input[^>]*type=["']?password/i.test(r.text)) {
			result = {which: 'test', kind: 'ko', text: tr('refusedPassword', {client: 'eMule'})};
		}
		else {
			result = {which: 'test', kind: 'ko', text: tr('noEmule', {url: ctx.url})};
		}
	}
	catch (e) {
		trace('testEmule() ' + e);
		result = {which: 'test', text: apiFailure(e, ctx.url, 'eMule'), kind: 'ko'};
	}
	finally {
		finishApiAction(ctx, null, result);
	}
}

/**
* Test button, aMule 3.x: log in to aMule with the address and the password typed, then read its
* version and its connection state (SF-8.17). Nothing is saved.
* @param button the Test button
*/
async function testAmuleApi(button) {
	var ctx = startApiAction(button, tr('testing'));
	var token = null;
	var result = null;
	var r, version, state, networks, name;

	if (ctx == null) {
		return;
	}
	trace('testAmuleApi() ' + ctx.url);
	try {
		r = await gmRequest('POST', ctx.api + 'auth/login?include_token=true', {password: ctx.typed[1]});
		if (r.status != 200 || r.json == null || !r.json.token) {
			result = {which: 'test', text: amuleApiError(r, ctx.url), kind: 'ko'};
			return;
		}
		token = r.json.token;
		version = await gmRequest('GET', ctx.api + 'version', null, null);
		state = await gmRequest('GET', ctx.api + 'status', null, token);
		name = 'aMule' + ((version.status == 200 && version.json && version.json.daemon_version) ?
			' ' + version.json.daemon_version : '');
		if (r.json.role && r.json.role != 'admin') {
			result = {which: 'test', kind: 'warn', text: tr('connectedNotAdmin', {name: name})};
		}
		else if (state.status == 503 || (state.json && state.json.ec_connected === false)) {
			result = {which: 'test', kind: 'warn', text: tr('connectedNoCore', {name: name})};
		}
		else {
			networks = [];
			if (state.json && state.json.ed2k && state.json.ed2k.state) {
				networks.push('ed2k: ' + state.json.ed2k.state);
			}
			if (state.json && state.json.kad && state.json.kad.state) {
				networks.push('Kad: ' + state.json.kad.state);
			}
			result = {which: 'test', kind: 'ok',
				text: tr('connectedTo', {name: name + (networks.length ? ' (' + networks.join(', ') + ')' : '')})};
		}
	}
	catch (e) {
		trace('testAmuleApi() ' + e);
		result = {which: 'test', text: apiFailure(e, ctx.url), kind: 'ko'};
	}
	finally {
		finishApiAction(ctx, token, result);
	}
}

/**
* Import button, for the method of the server displayed: eMule, aMule 3.x or aMule 2.x
* (IMPORT_ACTIONS, SF-8.18)
*/
function importCategories() {
	var method = settingsField('serverMethod').value;
	if (IMPORT_ACTIONS.hasOwnProperty(method)) {
		IMPORT_ACTIONS[method](this);
	}
}

/**
* Import button, aMule 2.x: log in to amuleweb, then read its categories in the list of its form to
* add a link (footer.php, <select name="selectcat">), in its order (SF-8.18). aMule 2.x knows its
* categories by their name: each one is imported as name=name (all=all for its first one).
* @param button the Import button
*/
async function importAmuleWebCategories(button) {
	var ctx = startApiAction(button, tr('importing'));
	var result = null;
	var r, error, options, cats;

	if (ctx == null) {
		return;
	}
	trace('importAmuleWebCategories() ' + ctx.url);
	try {
		r = await gmRequest('GET', ctx.url + '?pass=' + encodeURIComponent(ctx.typed[1]), null, null);
		error = amuleWebLogin(r, ctx.url);
		if (error != null) {
			result = {which: 'import', kind: 'ko', text: error};
			return;
		}
		r = await gmRequest('GET', ctx.url + 'footer.php', null, null);
		options = new DOMParser().parseFromString(r.text, 'text/html').querySelectorAll('select[name="selectcat"] option');
		if (options.length == 0) {
			result = {which: 'import', kind: 'ko', text: tr('noAmuleWeb', {url: ctx.url})};
			return;
		}
		cats = [].map.call(options, function (o) { return {index: o.textContent, name: o.textContent}; });
		result = importResult(cats, ctx, 'aMule', true);
	}
	catch (e) {
		trace('importAmuleWebCategories() ' + e);
		result = {which: 'import', text: apiFailure(e, ctx.url), kind: 'ko'};
	}
	finally {
		finishApiAction(ctx, null, result);
	}
}

/**
* The result of an import: the categories read merged into the field typed (mergeCategories()),
* applied to the field once shown, with Undo; or a message when the field already holds them
* @param cats the categories read: [{index, name}, ...]
* @param ctx what startApiAction() returned
* @param client eMule or aMule
* @param byName true for aMule 2.x, which knows its categories by their name (mergeCategories())
*/
function importResult(cats, ctx, client, byName) {
	var merged = mergeCategories(cats, ctx.typed[2], client, byName);
	if (merged.value == ctx.typed[2].trim()) {
		return {which: 'import', kind: 'ok', text: tr('importAlready', {client: client})};
	}
	return {which: 'import', kind: 'ok', text: merged.message,
		apply: function () {
			settingsField('emuleCat').value = merged.value;
			document.getElementById('GM_config_emuleCat_var').classList.add('changed');
		},
		undo: function () {
			settingsField('emuleCat').value = ctx.typed[2];
		}};
}

/**
* Import button, eMule: log in to its web interface, as Test does, read its categories in the
* list of its form to add a link (<select name="cat">: index and name, in its order, without the
* display filters of its menu), then log out (SF-8.18). The names are read by the HTML parser of
* the browser (entities, accents). Nothing is saved, nothing is sent.
* @param button the Import button
*/
async function importEmuleCategories(button) {
	var ctx = startApiAction(button, tr('importing'));
	var result = null;
	var r, session, options, cats;

	if (ctx == null) {
		return;
	}
	trace('importEmuleCategories() ' + ctx.url);
	try {
		r = await gmRequest('GET', ctx.url + '?w=password&p=' + encodeURIComponent(ctx.typed[1]), null, null);
		session = /[?&]ses=(-?\d+)/.exec(r.text);
		options = r.status == 200 ?
			new DOMParser().parseFromString(r.text, 'text/html').querySelectorAll('select[name="cat"] option') : [];
		if (session) {
			gmRequest('GET', ctx.url + '?ses=' + session[1] + '&w=logout', null, null).catch(function () {});
		}
		if (session && options.length > 0) {
			cats = [].map.call(options, function (o) { return {index: o.value, name: o.textContent}; });
			result = importResult(cats, ctx, 'eMule');
		}
		else if (r.status == 200 && /<input[^>]*type=["']?password/i.test(r.text)) {
			result = {which: 'import', kind: 'ko', text: tr('refusedPassword', {client: 'eMule'})};
		}
		else {
			result = {which: 'import', kind: 'ko', text: tr('noEmule', {url: ctx.url})};
		}
	}
	catch (e) {
		trace('importEmuleCategories() ' + e);
		result = {which: 'import', text: apiFailure(e, ctx.url, 'eMule'), kind: 'ko'};
	}
	finally {
		finishApiAction(ctx, null, result);
	}
}

/**
* Import button, aMule 3.x: read the categories of aMule, every page of them, and fill the Category
* field with them (SF-8.18). The field is highlighted, and an Undo button puts it back. Nothing is saved.
* @param button the Import button
*/
async function importAmuleCategories(button) {
	var ctx = startApiAction(button, tr('importing'));
	var token = null;
	var result = null;
	var cats = [];
	var r;

	if (ctx == null) {
		return;
	}
	trace('importAmuleCategories() ' + ctx.url);
	try {
		r = await gmRequest('POST', ctx.api + 'auth/login?include_token=true', {password: ctx.typed[1]});
		if (r.status != 200 || r.json == null || !r.json.token) {
			result = {which: 'import', text: amuleApiError(r, ctx.url), kind: 'ko'};
			return;
		}
		token = r.json.token;
		// the API answers page by page (100 categories by default; aMule has 256 at most)
		do {
			r = await gmRequest('GET', ctx.api + 'categories?limit=100&offset=' + cats.length, null, token);
			if (r.status != 200 || r.json == null || !Array.isArray(r.json.categories)) {
				result = {which: 'import', text: amuleApiError(r, ctx.url), kind: 'ko'};
				return;
			}
			cats = cats.concat(r.json.categories);
		} while (r.json.categories.length > 0 && cats.length < (r.json.total || 0) && cats.length < 1000);
		result = importResult(cats, ctx, 'aMule');
	}
	catch (e) {
		trace('importAmuleCategories() ' + e);
		result = {which: 'import', text: apiFailure(e, ctx.url), kind: 'ko'};
	}
	finally {
		finishApiAction(ctx, token, result);
	}
}

/**
* The Category setting made of the categories of the client (Import, SF-8.18)
* In the order of the client, each one with its name and its index, the category 0 included (aMule
* names it Default, eMule All); Default=0 when the client has none. The default one (*) stays on the
* category of the same name, whatever the case, or else goes to the first one. The characters of
* the syntax of the field (; and =, a leading *) are taken out of the names, and a category
* without a name is named after its index.
* @param cats the categories of the client: [{index, name}, ...]
* @param current the value of the field before the import
* @param client the name of the client in the message: aMule when not given, or eMule
* @param byName true when the client knows its categories by their name (aMule 2.x): the value of
* each one is then its name as the client knows it, an = included, a ; written \;
* @return {value: the new value of the field, message: what changed}
*/
function mergeCategories(cats, current, client, byName) {
	var old = strToCat(String(current).trim());
	client = client || 'aMule';
	var lower = function (s) { return s.toLowerCase(); };
	var names = function (list) { return list.slice(0, 3).join(', ') + (list.length > 3 ? ', …' : ''); };
	var entries = [];
	var oldDefault = '';
	var def, added, removed, parts, message;

	if (old == -1) {
		old = [];
	}
	for (var i=0; i<old.length; i++) {
		if (old[i].select == 1) {
			oldDefault = old[i].name;
		}
	}
	for (var i=0; i<cats.length; i++) {
		var index = byName ? null : parseInt(cats[i].index, 10);
		var raw = String(cats[i].name == null ? '' : cats[i].name);
		var name = raw.replace(/[;=]/g, ' ').replace(/^[\s*]+/, '').replace(/\s+/g, ' ').trim();
		if (byName ? name == '' : isNaN(index)) {
			continue;
		}
		// aMule 2.x: the value is the name as aMule knows it, an = included (strToCat() reads the value
		// after the first =), a ; written \; (the separator of the field)
		entries.push({name: name || tr('categoryN', {index: index}), index: byName ? raw.trim().replace(/;/g, '\\;') : index});
	}
	if (entries.length == 0) {
		return {value: '*Default=0', message: tr('importNone', {client: client})};
	}
	def = entries.filter(function (e) { return oldDefault != '' && lower(e.name) == lower(oldDefault); })[0] || entries[0];
	added = entries.filter(function (e) {
		return !old.some(function (c) { return lower(c.name) == lower(e.name); });
	}).map(function (e) { return e.name; });
	removed = old.filter(function (c) {
		return !entries.some(function (e) { return lower(e.name) == lower(c.name); });
	}).map(function (c) { return c.name; });

	parts = [];
	if (added.length > 0) {
		parts.push(tr('importNew', {count: added.length, names: names(added)}));
	}
	if (removed.length > 0) {
		parts.push(tr('importRemoved', {count: removed.length, names: names(removed)}));
	}
	message = tr(entries.length > 1 ? 'importMany' : 'importOne', {count: entries.length, client: client,
		parts: parts.length ? ': ' + parts.join(', ') : ''}) + ' '
		+ tr(oldDefault != '' && lower(def.name) == lower(oldDefault) ? 'importStays' : 'importIsNow', {name: def.name});
	return {value: entries.map(function (e) { return (e === def ? '*' : '') + e.name + '=' + e.index; }).join(';'),
		message: message};
}

/**
* The value of a field of the settings dialog, as displayed
*/
function settingsFieldValue(id) {
	var node = document.getElementById('GM_config_field_' + id);
	var checked;
	if (node.tagName == 'DIV') {	// radio buttons
		checked = node.querySelector('input:checked');
		return checked ? checked.value : '';
	}
	if (node.type == 'checkbox') {
		return node.checked;
	}
	return node.value;
}

/**
* Display a value in a field of the settings dialog
*/
function setSettingsFieldValue(id, value) {
	var node = document.getElementById('GM_config_field_' + id);
	var radios;
	if (node.tagName == 'DIV') {
		radios = node.querySelectorAll('input');
		for (var i=0; i<radios.length; i++) {
			radios[i].checked = (radios[i].value == value);
		}
		return;
	}
	if (node.type == 'checkbox') {
		node.checked = value;
		return;
	}
	node.value = value;
}

/**
* Add the Help button at the right of the title of the settings dialog
* It shows or hides the helps under every field at once. The choice is stored (settings_help),
* so that the dialog opens the next time as it was left.
*/
function addHelpButton() {
	var root = document.getElementById('GM_config');
	var button = document.createElement('button');
	var show = function (on) {
		// helps hidden: each row keeps its help as the tooltip of the browser, shown after a
		// short delay over it; helps shown: no tooltip, the same text is already under the field
		var helps = root.querySelectorAll('.config_var .help');
		for (var i=0; i<helps.length; i++) {
			if (on) {
				helps[i].parentNode.removeAttribute('title');
			}
			else {
				helps[i].parentNode.setAttribute('title', helps[i].textContent);
			}
		}
		root.classList.toggle('helps', on);
		button.title = tr(on ? 'helpHide' : 'helpShow');
		button.setAttribute('aria-pressed', on ? 'true' : 'false');
	};
	var close = document.createElement('button');

	button.type = 'button';
	button.id = 'GM_config_helpBtn';
	button.className = 'helpbtn';
	button.innerHTML = ICONS.help;
	button.setAttribute('data-icon', 'help');
	button.addEventListener('click', function () {
		var on = !root.classList.contains('helps');
		GM_setValue('settings_help', on ? 1 : 0);
		show(on);
	}, false);
	show(GM_getValue('settings_help', 0) == 1);
	document.getElementById('GM_config_header').appendChild(button);

	// the Close icon, at the right of the header: the same as the Close button, at the bottom
	close.type = 'button';
	close.id = 'GM_config_closeIcon';
	close.innerHTML = ICONS.close;
	close.setAttribute('data-icon', 'close');
	close.title = tr('closeDialogTitle');
	close.addEventListener('click', function () { document.getElementById('GM_config_closeBtn').click(); }, false);
	document.getElementById('GM_config_header').appendChild(close);
}

/**
* At the bottom of the window, the popup always stays in view (SF-2.2): scrolling with the page, it would
* be seen only at the load of the page. Popup scrolling is then Stays in view, grayed out; at the top, it
* can be chosen again.
*/
function syncPopupScroll() {
	var scroll = settingsField('popupScroll');
	var bottom = settingsField('popupCorner').value.indexOf('bottom') == 0;

	if (bottom) {
		scroll.value = 'floating';
	}
	scroll.disabled = bottom;
}

/**
* Replace the "Reset to defaults" link of GM_config by a button at the left of the buttons
* The button sets every setting back to its default value, in the dialog only: Local is checked
* and every server removed. The settings it changed are highlighted, and a notice says that
* nothing is saved yet, with an Undo button.
*/
function addResetButton() {
	var bar = document.getElementById('GM_config_buttons_holder');
	var button = document.createElement('button');
	var others = ['language', 'popupView', 'closeMessage', 'showCategories', 'showServerList', 'popupCorner', 'popupScroll', 'popupHeight', 'popupWidth', 'checkFilter', 'editCol', 'editRow'];
	var editor = ['serverName', 'serverMethod'].concat(METHOD_SETTINGS);

	button.type = 'button';
	button.id = 'GM_config_resetBtn';
	button.className = 'resetbtn';
	button.textContent = tr('reset');
	button.title = tr('resetTitle');
	button.addEventListener('click', function () {
		var before = {servers: JSON.stringify(dialogServers), edited: dialogEdited, values: {}};
		var changed = 0;

		for (var i=0; i<others.length; i++) {
			before.values[others[i]] = settingsFieldValue(others[i]);
		}
		for (var i=0; i<editor.length; i++) {
			before.values[editor[i]] = settingsField(editor[i]).value;
		}
		clearSettingsMarks();
		GM_config.reset();
		dialogServers = {active: null, list: []};
		dialogEdited = null;
		for (var i=0; i<others.length; i++) {
			if (settingsFieldValue(others[i]) != before.values[others[i]]) {
				document.getElementById('GM_config_' + others[i] + '_var').classList.add('changed');
				changed++;
			}
		}
		if (before.servers != JSON.stringify(dialogServers)) {
			document.getElementById('GM_config_ed2kDlMethod_var').classList.add('changed');
			changed++;
		}
		showServers();
		syncPopupScroll();
		if (changed == 0) {
			showNotice(tr('resetNone'), null);
			return;
		}
		showNotice(tr(changed > 1 ? 'resetMany' : 'resetOne', {count: changed}), function () {
			dialogServers = JSON.parse(before.servers);
			dialogEdited = before.edited;
			for (var i=0; i<others.length; i++) {
				setSettingsFieldValue(others[i], before.values[others[i]]);
			}
			showServers();
			syncPopupScroll();
			// the text displayed for the server being edited, even if not kept yet
			for (var i=0; i<editor.length; i++) {
				settingsField(editor[i]).value = before.values[editor[i]];
			}
			if (dialogEdited != null) {
				showServerFields();
			}
		});
	}, false);
	bar.insertBefore(button, bar.firstChild);
}

/**
* Remove the marks of a reset (changed fields, notice), the results of Test and Import and the
* error messages of the dialog
*/
function clearSettingsMarks() {
	var marks;

	removeApiStatus('test');
	removeApiStatus('import');
	marks = document.querySelectorAll('#GM_config .changed, #GM_config_notice');
	for (var i=0; i<marks.length; i++) {
		if (marks[i].id == 'GM_config_notice') {
			marks[i].parentNode.removeChild(marks[i]);
		}
		else {
			marks[i].classList.remove('changed');
		}
	}
	clearSettingsErrors();
}

/**
* Remove the error messages of the settings dialog
*/
function clearSettingsErrors() {
	var olds = document.querySelectorAll('#GM_config .error, #GM_config .invalid');
	for (var i=0; i<olds.length; i++) {
		if (olds[i].classList.contains('error')) {
			olds[i].parentNode.removeChild(olds[i]);
		}
		else {
			olds[i].classList.remove('invalid');
		}
	}
}

/**
* Show an error under a field of the settings dialog, in red, and give it the focus
*/
function showSettingsError(id, text) {
	var field = settingsField(id);
	var message = document.createElement('div');
	message.className = 'error';
	message.textContent = text;
	field.classList.add('invalid');
	document.getElementById('GM_config_' + id + '_var').appendChild(message);
}

/**
* Escape closes the settings dialog, without saving
*/
function closeSettingsOnEscape(e) {
	if (e.key == 'Escape' && GM_config.isOpen) {
		e.preventDefault();
		GM_config.close();
	}
}

/**
* Check the values of the settings dialog before they are saved
* A wrong value is shown under its field, in red, instead of an alert, and nothing is saved.
* The name and the category of the server being edited are checked too (serverErrors()).
* @return true when every value can be saved
*/
function checkSettings() {
	var errors = [];
	var value = function (id) { return settingsField(id).value.trim(); };
	var whole = /^\d+$/;

	clearSettingsErrors();
	errors = serverErrors();
	if (!whole.test(value('popupHeight'))) {
		errors.push(['popupHeight', tr('wholeNumber')]);
	}
	else if (parseInt(value('popupHeight'), 10) > 0 && parseInt(value('popupHeight'), 10) < 40) {
		errors.push(['popupHeight', tr('heightMin')]);
	}
	if (!whole.test(value('popupWidth'))) {
		errors.push(['popupWidth', tr('wholeNumber')]);
	}
	else if (parseInt(value('popupWidth'), 10) > 0 && parseInt(value('popupWidth'), 10) < 100) {
		errors.push(['popupWidth', tr('widthMin')]);
	}
	if (parseCheckFilter(value('checkFilter')).error) {
		errors.push(['checkFilter', parseCheckFilter(value('checkFilter')).error]);
	}
	if (!whole.test(value('editCol')) || parseInt(value('editCol'), 10) < 1) {
		errors.push(['editCol', tr('wholeAtLeast1')]);
	}
	if (!whole.test(value('editRow')) || parseInt(value('editRow'), 10) < 1) {
		errors.push(['editRow', tr('wholeAtLeast1')]);
	}

	for (var i=0; i<errors.length; i++) {
		showSettingsError(errors[i][0], errors[i][1]);
	}
	if (errors.length > 0) {
		trace('checkSettings() ' + errors.length + ' wrong value(s)');
		settingsField(errors[0][0]).focus();
	}
	return errors.length == 0;
}

/**
* Store one setting at once, outside the settings dialog ("Don't display again" of the message of the
* closed popup, I-3): on top of the stored settings, the other ones left exactly as the user saved them
*/
function storeSetting(id, value) {
	var stored = GM_config.read();
	stored[id] = value;
	GM_config.write(null, stored);
	GM_config.set(id, value);
}

/**
* Save the config parameters
*/
function saveConfig() {
	var corrected = {};	// settings replaced by a usable value, to be stored

	trace("saveConfig() storing the settings");

	ed2kDlMethod = GM_config.get('ed2kDlMethod');

	emuleUrl = GM_config.get('emuleUrl');
	if( (ed2kDlMethod!='custom') && emuleUrl.charAt(emuleUrl.length-1) != '/') {
		GM_config.set("emuleUrl", emuleUrl + '/');
		emuleUrl += '/';
		corrected.emuleUrl = emuleUrl;
	}

	// the password is optional: eMule accepts a web interface without one
	emuleUser = GM_config.get('emuleUser');
	emulePwd = GM_config.get('emulePwd');

	emuleCat = strToCat(GM_config.get('emuleCat'));
	if(emuleCat==-1) {
		alert(tr('alertCategory'));
		GM_config.set('emuleCat', '*default=0');
		emuleCat = strToCat('*default=0');
		corrected.emuleCat = '*default=0';
	}

	popupView = GM_config.get('popupView');
	if (['maximized', 'minimized', 'closed'].indexOf(popupView) < 0) {
		popupView = 'maximized';
	}

	// Popup position and Popup scrolling (0.14), in place of Popup Position (popupPos): absolute is static,
	// fixed is floating, stored once; the popup was then at the top left (SF-8.7)
	var saved = GM_config.read();
	if (saved.popupScroll === undefined && (saved.popupPos == 'absolute' || saved.popupPos == 'fixed')) {
		GM_config.set('popupScroll', (saved.popupPos == 'absolute') ? 'static' : 'floating');
		corrected.popupScroll = GM_config.get('popupScroll');
	}
	popupCorner = GM_config.get('popupCorner');
	if (['top-left', 'top-right', 'bottom-left', 'bottom-right'].indexOf(popupCorner) < 0) {
		popupCorner = 'top-left';
	}
	popupScroll = GM_config.get('popupScroll');
	if (['floating', 'static'].indexOf(popupScroll) < 0 || popupCorner.indexOf('bottom') == 0) {
		popupScroll = 'floating';	// at the bottom of the window, the popup always stays in view (SF-2.2)
	}
	closeMessage = (GM_config.get('closeMessage') !== false);
	showCategories = (GM_config.get('showCategories') !== false);
	showServerList = (GM_config.get('showServerList') !== false);

	popupHeight = GM_config.get('popupHeight');
	if (popupHeight > 0 && popupHeight < 40 ) {
		alert(tr('alertHeight'));
		GM_config.set("popupHeight",0);
		popupHeight = 0;
		corrected.popupHeight = 0;
	}

	popupWidth = GM_config.get('popupWidth');
	if (popupWidth > 0 && popupWidth < 100 ) {
		alert(tr('alertWidth'));
		GM_config.set("popupWidth",0);
		popupWidth = 0;
		corrected.popupWidth = 0;
	}

	// a filter that can not be read is refused by Save (checkSettings()): one stored anyway is
	// ignored, and every link is checked (SF-5.7)
	checkFilter = GM_config.get('checkFilter');
	var filter = parseCheckFilter(checkFilter);
	if (filter.error) {
		trace("saveConfig() filter of the links checked by default ignored: " + filter.error);
	}
	checkRegExp = filter.error ? null : filter.re;

	editCol = GM_config.get('editCol');
	editRow = GM_config.get('editRow');

	// GM_config.set() only changes the value in memory: without storing it, the invalid
	// value is read again on the next page load and the same alert pops up on every page.
	// Only the corrected settings are stored, on top of the stored ones: the other settings
	// are left exactly as the user saved them.
	if (Object.keys(corrected).length > 0) {
		var stored = GM_config.read();
		for (var id in corrected) {
			stored[id] = corrected[id];
		}
		GM_config.write(null, stored);
	}
}

// -------------------------------------------------------------------------
// Utilities: the traces, the requests of the script, the categories as text, the sizes
// -------------------------------------------------------------------------

/**
* To trace some text in the console
* @param txt the text to trace into the console
*/
function trace(txt) {
	if (DEBUG_MODE) {
		console.log(txt);
	}
}

/**
* A JSON request through GM_xmlhttpRequest, which is not subject to CORS
* @param method the http method
* @param url the full url
* @param body the object to send as JSON, or null
* @param token the bearer token, or the value of an HTTP Basic authorization (basicAuth()), or null
* @param timeout the time limit in milliseconds (15 s when not given)
* @return a promise of {status, json, text, retryAfter} (json: the answer read as JSON, or null;
* text: the answer as it came), rejected when the server can not be reached, or with an error
* whose timeout property is set when it did not answer in time
*/
function gmRequest(method, url, body, token, timeout) {
	timeout = timeout || 15000;
	return new Promise(function (resolve, reject) {
		var headers = {'Accept': 'application/json'};
		if (body != null) {
			headers['Content-Type'] = 'application/json';
		}
		if (token != null) {
			headers['Authorization'] = /^Basic /.test(token) ? token : 'Bearer ' + token;
		}
		GM_xmlhttpRequest({
			method: method,
			url: url,
			headers: headers,
			data: body == null ? undefined : JSON.stringify(body),
			timeout: timeout,
			onload: function (res) {
				var json = null;
				var retry = /^retry-after:\s*(\S+)/im.exec(res.responseHeaders || '');
				try {
					json = JSON.parse(res.responseText);
				}
				catch (e) {
					// not a JSON answer: only the status is used
				}
				resolve({status: res.status, json: json, text: res.responseText || '', retryAfter: retry ? retry[1] : null});
			},
			onerror: function () { reject(new Error('network error')); },
			ontimeout: function () {
				var e = new Error('no answer within ' + timeout + ' ms');
				e.timeout = timeout;
				reject(e);
			}
		});
	});
}

/**
* The value of an HTTP Basic authorization: the user and the password, in UTF-8, in base 64
*/
function basicAuth(user, password) {
	var bytes = new TextEncoder().encode(user + ':' + password);
	return 'Basic ' + btoa(Array.prototype.map.call(bytes, function (b) { return String.fromCharCode(b); }).join(''));
}

/**
* Category array to string
*/
function catToStr(cat) {
	var str="";

	//trace('catToStr()');

	for (var i=0; i < cat.length; i++) {
		if (cat[i].select==1) {
			str +='*';
		}
		// a ; in a name or a value is written \; (strToCat())
		str +=String(cat[i].name).replace(/;/g, '\\;')+'=';
		str +=String(cat[i].value).replace(/;/g, '\\;') +';';
	}

	trace('catToStr() -> ' + str);
	return str;
}

/**
* The title of a box of the script, with its version, as given by the userscript manager:
* "Emule Linker 0.14 — Settings", "Emule Linker 0.14 — Help"
*/
function boxTitle(name) {
	var version = (typeof GM_info != 'undefined' && GM_info.script) ? GM_info.script.version : '';
	return 'Emule Linker ' + (version ? version + ' ' : '') + '\u2014 ' + name;
}

/**
* The language of the texts (I-7): the setting Language, read from the storage of GM_config before it is
* set up, as its fields need the texts; Browser language: the language of the browser when the script has
* its texts, English otherwise
*/
function scriptLanguage() {
	var chosen = 'browser';
	try {
		chosen = JSON.parse(GM_getValue('GM_config', '{}') || '{}').language || language;
	}
	catch (e) {
		trace('scriptLanguage() settings not read: ' + e);
	}
	if (!TEXTS.hasOwnProperty(chosen)) {	// Browser language, or an unknown value read as it (SF-12.2)
		chosen = String(navigator.language || '').slice(0, 2).toLowerCase();
	}
	return TEXTS.hasOwnProperty(chosen) ? chosen : 'en';
}

/**
* A text in the language of the script (TEXTS, I-7), English when it has none
* @param key the name of the text
* @param values the values of its {names}, if any
*/
function tr(key, values) {
	var table = TEXTS[textLanguage] || TEXTS.en;
	var text = (table[key] != null) ? table[key] : TEXTS.en[key];

	if (text == null) {
		trace('tr() no text ' + key);
		return key;
	}
	return text.replace(/\{(\w+)\}/g, function (all, name) {
		return (values && values[name] != null) ? String(values[name]) : all;
	});
}

/**
* A label with the letter of its keyboard shortcut underlined, marked by & in the text (I-7); not
* underlined when the label of a language does not hold it
*/
function trLabel(key) {
	return tr(key).replace(/&(.)/, '<u>$1</u>');
}

/**
* A label without the mark of its shortcut
*/
function trPlain(key) {
	return tr(key).replace('&', '');
}

/**
* String to category array
* Expected format: [*]name=value;[*]name=value;...  (the * marks the default category). The value
* is everything after the first =, and a ; in a name or a value is written \; (aMule 2.x knows its
* categories by their name, which may hold them: A=B, test;23).
* Invalid entries are skipped. Exactly one category ends up selected, so that the
* drop-down list and the category sent (getSelectedCat()) always agree.
* @param str the categories as entered in the settings
* @return the category array, or -1 when the string holds no valid category
*/
function strToCat(str) {
	var cat = new Array();
	var tab = String(str).split(/(?<!\\);/);	// the ; written \; are not separators
	var equal, name, value, select;
	var hasDefault = false;

	//trace ('strToCat('+str+')');

	for (var i=0; i<tab.length; i++) {
		if (tab[i].trim() == '') {
			continue;	// empty entry, typically after the last ;
		}

		// the value is everything after the first =: an aMule 2.x category may hold one
		equal = tab[i].indexOf('=');
		name = (equal == -1 ? tab[i] : tab[i].slice(0, equal)).replace(/\\;/g, ';').trim();
		value = (equal == -1) ? '' : tab[i].slice(equal + 1).replace(/\\;/g, ';').trim();
		select = 0;

		if (name.charAt(0) == '*') {
			name = name.slice(1).trim();
			// only one default category: the first one marked wins
			if (!hasDefault) {
				select = 1;
				hasDefault = true;
			}
		}

		// every category needs a name and a value, not only the first one
		if (name == '' || value == '') {
			trace('strToCat() ignoring invalid category: ' + tab[i]);
			continue;
		}

		cat.push({name: name, value: value, select: select});
		//trace('cat['+(cat.length-1)+'] => '+name+'='+value+' ('+select+')');
	}

	if (cat.length == 0) {
		trace('strToCat() no valid category found');
		return -1;
	}

	// no category marked with *: the first one becomes the default, as the list shows it first
	if (!hasDefault) {
		cat[0].select = 1;
	}

	trace('strToCat() -> ' + cat.length + ' categories');
	return cat;
}

/**
* Submit a post
* source : http://stackoverflow.com/questions/133925/javascript-post-request-like-a-form-submit
*
* ex: post('/contact/', {name: 'Johnny Bravo'});
*/
function post(path, params, method) {
	method = method || "post"; // Set method to post by default if not specified.

	// The rest of this code assumes you are not using a library.
	// It can be made less wordy if you use one.
	var form = document.createElement("form");
	form.setAttribute("method", method);
	form.setAttribute("action", path);
	form.setAttribute("target", "emule");

	for(var key in params) {
		if(params.hasOwnProperty(key)) {
			var hiddenField = document.createElement("input");
			hiddenField.setAttribute("type", "hidden");
			hiddenField.setAttribute("name", key);
			hiddenField.setAttribute("value", params[key]);

			form.appendChild(hiddenField);
		}
	}

	document.body.appendChild(form);
	form.submit();
	// the submission has started: the form is no longer needed, it would pile up at each sending
	form.parentNode.removeChild(form);
}

/**
* Format bytes as human-readable text.
*
* @param bytes Number of bytes.
* @param si True to use metric (SI) units, aka powers of 1000. False to use
*           binary (IEC), aka powers of 1024.
* @param dp Number of decimal places to display.
*
* @return Formatted string.
*/
function humanFileSize(bytes, si=false, dp=1) {
	const thresh = si ? 1000 : 1024;

	if (Math.abs(bytes) < thresh) {
		return bytes + ' B';
	}

	const units = si
		? ['kB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
		: ['KiB', 'MiB', 'GiB', 'TiB', 'PiB', 'EiB', 'ZiB', 'YiB'];
	let u = -1;
	const r = 10**dp;

	do {
		bytes /= thresh;
		++u;
	} while (Math.round(Math.abs(bytes) * r) / r >= thresh && u < units.length - 1);

	return bytes.toFixed(dp) + ' ' + units[u];
}
