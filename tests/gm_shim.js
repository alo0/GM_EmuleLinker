// Minimal stand-in for the Greasemonkey / Tampermonkey API used by GM_EmuleLinker.user.js,
// so that the script runs unchanged in a plain page, without the extension.
// Values are kept in localStorage, JSON-encoded so that their type is preserved
// (popup_mode is a number, the GM_config settings a string), as GM_setValue does.
var GM_PREFIX = 'gm:';

function GM_getValue(name, def) {
	var v = localStorage.getItem(GM_PREFIX + name);
	return v === null ? def : JSON.parse(v);
}

function GM_setValue(name, value) {
	localStorage.setItem(GM_PREFIX + name, JSON.stringify(value));
}

// The menu commands are kept by access key, so that a test can call one the way
// Tampermonkey does, without any "this": window.__GM_menu['o']()
function GM_registerMenuCommand(name, callback, accessKey) {
	(window.__GM_menu = window.__GM_menu || {})[accessKey] = callback;
}

function GM_log(txt) {
	console.log(txt);
}
