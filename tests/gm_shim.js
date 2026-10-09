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

// In Tampermonkey, GM_xmlhttpRequest is not subject to CORS: it reaches any address. A
// fetch() from the page would be, so the test server relays the request (/__gmxhr) and
// sends back the answer, as the extension does. Same callbacks as the real one.
function GM_xmlhttpRequest(d) {
	fetch('/__gmxhr', {
		method: 'POST',
		headers: {'Content-Type': 'application/json'},
		body: JSON.stringify({method: d.method || 'GET', url: d.url, headers: d.headers || {},
		                      data: d.data == null ? null : d.data, timeout: d.timeout || 0})
	})
	.then(function (r) { return r.json(); })
	.then(function (r) {
		if (r.error == 'timeout') {
			if (d.ontimeout) d.ontimeout({});
		}
		else if (r.error) {
			if (d.onerror) d.onerror({error: r.error});
		}
		else if (d.onload) {
			d.onload({status: r.status, responseText: r.responseText,
			          responseHeaders: r.responseHeaders, finalUrl: d.url});
		}
	})
	.catch(function (e) { if (d.onerror) d.onerror({error: String(e)}); });
}
