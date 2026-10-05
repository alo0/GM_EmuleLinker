// ==UserScript==
// @name        Emule Linker
// @namespace   https://github.com/alo0/GM_EmuleLinker
// @description Add all ED2K links (with one click) into remote emule/amule/mldonkey or any application installed on your system that handles ed2k links
// @include     *
// @grant		GM_getValue
// @grant		GM_setValue
// @grant		GM_registerMenuCommand
// @grant 		GM_log
// @version     0.10
// @updateURL       https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/GM_EmuleLinker.user.js
// @downloadURL     https://raw.githubusercontent.com/alo0/GM_EmuleLinker/master/GM_EmuleLinker.user.js
// ==/UserScript==
// -------------------------------------------------------------------------
// WHAT IT DOES:
// The script scans pages for ed2k links. It collects these links
// and displays them in a (closable) popup box in the upper left
// hand corner of the page. Then, you can add all of them into emule
// or separately.
//
// This script has been inspired from these scripts below
// http://userscripts.org/scripts/show/4011
// http://userscripts.org/scripts/show/11310
// -------------------------------------------------------------------------
// INSTALLATION
// 1. install this script in the Tampermonkey extension
// 2. (optional) to send the links to emule/amule/mldonkey, activate the web interface of this application
// 3. Navigate to a page with ed2k links
// => The popup should appear at the upper left
// 4. Edit the script params using the settings dialog (ctl+alt+s)
// 5. (optional) restrict the pages where this script is active with the "User includes" of its
//    Tampermonkey settings: unlike a change of the @include variable, they survive the updates
// -------------------------------------------------------------------------
// CHANGELOG
// 0.10 (2026-10-09)
//  + Bugfix: a malformed ed2k link no longer stops the detection of the other links of the page
//  + Bugfix: ed2k links whose scheme is url-encoded (ed2k%3A%2F%2F...) are now detected
//  + Bugfix: links can be sent with the popup closed (keyboard shortcut or menu)
//  + Bugfix: local mode works again on recent Chrome (links are url-encoded) and sends every selected link
//  + Links that are not files (server, serverlist) are now ignored
//  + Bugfix: an empty or invalid Category setting no longer stops the script on every page
//  + Categories: invalid entries are skipped and exactly one default is kept, so the category displayed is the one sent
//  + Settings corrected automatically are now stored, so their alert is no longer shown on every page
//  + Bugfix: the emule password is optional, as in eMule: no more alert and settings dialog on every page without it
//  + Bugfix: the popup can no longer be opened twice, and a popup closed on a page stays closed on the next ones
//  + Bugfix: the "Open Popup" menu entry works, and the shortcuts no longer fail on pages without ed2k links
//  + Bugfix: changing the category no longer resets the popup (checkboxes, edit box text, size)
//  + Bugfix: custom method, clicking a file name sends it, instead of opening a copy of the page
//  + The MaxLength setting of the edit box is removed: the list was never truncated, it only blocked typing
//  + With many links, only the list scrolls in the popup: both toolbars always stay visible
//  + Debug traces are off by default, and switched on or off by the new menu entry "Toggle debug traces"
//  + Known limit: on Chrome, local mode sends one link per user action. To send many links at once, use the emule web server
//  + The script file is renamed GM_EmuleLinker.user.js, for a one-click install. Existing installations move to it on their own
// 0.9 (2025-10-29)
//  + adding password support for amule mode
//  + adding file size in normal mode
//  + Checking double encoding of filename
//  + Enhance the css style of main popup
//  + Default settings changed as screen resolution are getting bigger
//  + Bugfix: Encoding of newline was necessary for some ed2k links
//  + Code refactoring and cleaning
// 0.8 (2018-11-11)
//	+ Bugfix: Now detect which method to use to decode URL : first decodeURIComponent() then unescape()
//  + Custom link is now using a post method and ending by a / is not mandatory in this case
// 0.7 (2013-01-27)
//  + Local appli ed2k handler support
//  + Checkbox filter
//  + Category selector
//  + Remove duplicate links check
//  + Add suffix to identical filename (but with different links)
//  + Key accelerator support (ctrl+alt+...  m, a, c, o, s, x)
//  + Bugfix: URL style was applying to the whole page
//	+ GM_config.js is now integrated into this script (for quick bugfix inside the lib)
// 0.6 (2013-01-17):
//	+ added amule support
//  + added mldonkey support
//	+ added focus back to main window
//	+ enhanced switch beetween edit & normal mode
//  + bugfix: char encoding
// 0.5 (2013-01-04):
//  + added edit mode function
//	+ changed height and width settings
//	+ bugfix on character encoding display
// 0.4 (2012-12-21): add settings dialog
// 0.3 (2012-12-20): script renamed and uploaded to userscripts.org
// 0.2 (2012-11-20): fixbug - on '|' char escaped to '%7C'
// 0.1 (2012-11-18): first version
// -------------------------------------------------------------------------



// -------------------------------------------------------------------------
// 								PARAM
// -------------------------------------------------------------------------
// These are the default values. Use the setting dialog to modify the parameters

// Debug traces in the browser console 0|1: a stored setting, off by default, switched by the
// menu entry "Toggle debug traces". Nothing to change in the code before publishing it.
var DEBUG_MODE = GM_getValue('debug_mode', 0);

// emule/amule/mldonkey server parameters
var ed2kDlMethod = 'local';
	// local: ed2k default application of your system (default)
	// emule: emule via web url
	// amule: amule via web url
	// mldonkey: mldonkey via web url
	// custom: custom via web url (experimental)

var emuleUrl = 'http://127.0.0.1:4711/'; 	// the adress and port of your emule web server
var emulePwd = ''; // the password to access the emule web server (optional)
var emuleCat = [ {name: 'default', value: '0', select: '1'} ]; // Which emule category to assign 0=all (default)

// Popup parameters
var popupPos = 'fixed'; // absolute or fixed
var popupHeight = 800; // max height in pixel of the popup box
var popupWidth = 800; // max width in pixel of the popup box

// edit box parameters
var editCol = 80; // number of column
var editRow = 16; // number of line



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
      window.addEventListener('resize', config.center, false); // Center frame on resize

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
/**
* Main : The entry point of the script
*/
var eLinks=new Array();
var eFiles=new Array();
var eSizes=new Array();

var childWindow = null;
const waitReady = () => new Promise((resolve) => {
    childWindow.addEventListener('load', resolve, true);
});

// add Emule Linker settings dialog to Greasemonkey Menu
GM_registerMenuCommand('Emule Linker: Settings', setButton, 's');
GM_registerMenuCommand('Emule Linker: Add links', addButton, 'a');
GM_registerMenuCommand('Emule Linker: Change mode (edit/normal)', editButton, 'm');
GM_registerMenuCommand('Emule Linker: Close Popup', closeButton, 'c');
GM_registerMenuCommand('Emule Linker: Open Popup', openButton, 'o');
GM_registerMenuCommand('Emule Linker: Toggle debug traces', debugButton, 'd');

// configuring the settings dialog & display it if it is the first time
scriptConfig();

// if ed2k links, display the popup
var n = 0;
try {
	n = getEd2kLinks(eLinks, eFiles, eSizes);
}
catch (e) {
	// whatever happens during the scan, the keyboard shortcuts installed below
	// must stay available and the page must not be left half processed
	trace("getEd2kLinks() failed: " + e);
}
// a popup closed on a page stays closed on the next ones, until it is opened again
if (n>0 && GM_getValue("popup_mode", 1) != 0) {
	createPopup(eLinks, eFiles, eSizes);
}

// Add key accelerator shortcuts
(function(d){
d.addEventListener('keydown', function(e) {
	// pressed ctl+alt
	if (e.keyCode == 65 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { addButton(); }	// ctl+alt+a
	if (e.keyCode == 67 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { closeButton(); } // ctl+alt+c
	if (e.keyCode == 77 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { editButton(); } // ctl+alt+m
	if (e.keyCode == 79 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { openButton(); } // ctl+alt+o
	if (e.keyCode == 83 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { setButton(); } // ctl+alt+s
	if (e.keyCode == 88 && !e.shiftKey && e.ctrlKey && e.altKey && !e.metaKey) { // ctl+alt+x
		switch(GM_getValue("popup_mode", 1)) {
		case 0: // popup closed
			openButton();
			break;

		case 1: // normal mode
		case 2: // edit mode
			closeButton();
			break;

		default:
			trace("ERROR: popup_mode=" + GM_getValue("popup_mode", 1));
			alert("Error !!! popup_mode unknown.");
			break;
		}
	}
	}, false);
})(document);

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
* Actions when the menu entry "Toggle debug traces" is chosen
* The setting is stored: the traces stay on (or off) on the next pages, until switched again.
*/
function debugButton() {
	DEBUG_MODE = DEBUG_MODE ? 0 : 1;
	GM_setValue('debug_mode', DEBUG_MODE);
	alert("Emule Linker: debug traces " + (DEBUG_MODE ? "on (see the browser console)" : "off"));
}

// -------------------------------------------------------------------------
/**
* Get ed2k links in the page
* @param links array to stock the ed2k links
* @param files array to stock the ed2k file names
* @return number of ed2k links
*/
function getEd2kLinks(links, files, sizes) {
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
	// First the Div
    theDiv=document.createElement('div');
	divBody = '<div id="theDiv" style="\
                    position:'+ popupPos + '; \
					top:0; \
					left:0; \
					background-color:white; \
					opacity:0.97; \
					color:black;\
                    margin:0;\
					border:2px solid #00f;\
					z-index:255;\
					text-align:left;\
					font-size:10px;\
					line-height:90%;\
					padding-left:5px;\
					padding-right:5px;';
	if (popupHeight != 0 && GM_getValue("popup_mode", 1)==1) {
		divBody += 'max-height:'+ popupHeight +'px;';
	}
	else {
		divBody += 'max-height:100%;';
	}
	if (popupWidth != 0 && GM_getValue("popup_mode", 1)==1) {
		divBody += 'max-width:'+ popupWidth +'px;';
	}
	else {
		divBody += 'max-width:100%;';
	}
	divBody += 'overflow:auto"> \
	<style> \
        div#theDiv button { \
			font-size:11px;\
		} \
        div#theDiv select { \
			font-size:11px;\
		} \
		div#theDiv input.smallcheck { \
			height: 9px; \
			width: 9px; \
			vertical-align:text-bottom;\
			font-size:10px;\
			line-height:90%;\
		} \
        div#divBody a {font-size: 10px;} \
		div#divBody a.ed2k:link       { color: #000000; text-decoration: none } \
		div#divBody a.ed2k:visited    { color: #000000; text-decoration: none } \
		div#divBody a.ed2k:hover      { color: #0000FF; text-decoration: underline; font-weight: normal } \
		div#divBody a.ed2k:active     { color: #0000FF; text-decoration: underline; font-weight: normal } \
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
            background: #FFFFFF; padding: 0px 4px;} \
        div#divBody th { \
            background: #FFFFFF; padding: 0px 4px;} \
        div#divBody tr { \
            background: #FFFFFF; \
        } \
        div#divBody tr:hover td { \
            background: #e3f0fa; \
        } \
	</style> \
	</div>';
	theDiv.innerHTML=divBody;
	document.body.insertBefore(theDiv, document.body.firstChild);

	container = document.getElementById ("theDiv");

	// adding the function toolbar at the top
	addToolbar(container, 0);

	// adding the body
	var tmp_link=document.createElement('div');
	tmp_link.setAttribute('id', 'divBody');
	tmp_link.style.clear='both';

	trace('createPopup() popup_mode=' + GM_getValue("popup_mode", 1));
	switch(GM_getValue("popup_mode", 1)) {
		case 0: // popup closed
			break;

		case 1: // normal mode
			tmp_link.innerHTML = htmlLinkList(links, files, sizes);
			container.appendChild(tmp_link);
			container.style.resize='both';
			// a column: top toolbar, list, bottom toolbar. Only the list scrolls, the
			// toolbars always stay visible, whatever the number of links (A-15)
			container.style.display='flex';
			container.style.flexDirection='column';
			container.style.overflow='hidden';
			tmp_link.style.flex='1 1 auto';
			tmp_link.style.minHeight='0';
			tmp_link.style.overflow='auto';
			// custom method: a click on a file name sends it with a POST form (A-14)
			tmp_link.addEventListener('click', clickOneLink, false);
			break;

		case 2: // edit mode
			container.appendChild(tmp_link);
			addEditBox(tmp_link, concatLinks(eLinks));
			container.style.resize='none';
			container.style.overflow='hidden';
			break;

		default:
			trace("ERROR: popup_mode=" + GM_getValue("popup_mode", 1));
			alert("Error !!! popup_mode unknown.");
			break;
	}

	// adding the function toolbar at the bottom
	addToolbar(container, 1);
}

/**
* Delete popup
*/
function delPopup() {
	trace('delPopup()');
	var theDiv = document.getElementById ("theDiv");
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

	html = '<hr /><table>';

	for (var i=0; i<links.length; i++) {
		html += '<tr><td><input class="smallcheck" name="l' + i + '" type="checkbox" id="l' + i + '" tabindex="' + i+1 + '" value="1" checked="checked" /></td><td style="white-space:nowrap;"><a class="ed2k" href="' + linkHref(links[i]) + '" target="emule">' + files[i] + '</a></td><td style="min-width:40px;">'+ humanFileSize(sizes[i], false, 0) + '</td></tr>'; //
	}

	html += '</table><hr />';
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

	var divL=document.createElement('div');
	var divR=document.createElement('div');

	divL.style.cssFloat='left';
	divR.style.cssFloat='right';

	divL.style.paddingLeft='0px';
	divL.style.paddingRight='5px';
	divR.style.paddingLeft='5px';
	divR.style.paddingRight='5px';

	divL.style.paddingBottom='2px';
	divL.style.paddingTop='2px';
	divR.style.paddingBottom='2px';
	divR.style.paddingTop='2px';

	// the two halves are grouped in one block, so that the toolbar can stay in place
	// while the list of links scrolls (A-15)
	var bar=document.createElement('div');
	bar.className = 'toolbar';
	bar.style.display = 'flow-root';	// holds its two floating halves
	bar.style.flex = 'none';			// never shrunk in the popup column
	bar.appendChild(divL);
	bar.appendChild(divR);
	container.appendChild(bar);

	// checkbox all
	var tmp_link=document.createElement('input');
	tmp_link.type = "checkbox";
	tmp_link.value = "1";
	tmp_link.checked = true;
	tmp_link.className = 'smallcheck';
	tmp_link.style.verticalAlign='bottom';
	if (pos==0) {
		tmp_link.name = "lall";
		tmp_link.id = "checkall";
		// in edit mode the link list is a textarea: there is no checkbox to toggle
		tmp_link.disabled = (GM_getValue("popup_mode", 1) == 2);
		tmp_link.addEventListener('click', function(){ checkButton(); }, false );
	}
	else {
		tmp_link.disabled = true;
	}

	divL.appendChild (tmp_link);

	divL.appendChild (document.createTextNode(' '));

	// dynamic add links
	tmp_link=document.createElement('button');
	tmp_link.addEventListener('click', function(){ addButton(); }, false );
	tmp_link.innerHTML = '<u>A</u>dd all links';
	divL.appendChild (tmp_link);

	divL.appendChild (document.createTextNode(' '));

	// Edit/Normal mode Link
	tmp_link=document.createElement('button');
	tmp_link.addEventListener('click', function(){ editButton(); }, false );
	switch(GM_getValue("popup_mode", 1)) {
	case 0:	// popup closed
	case 1: // in normal mode
		tmp_link.innerHTML = 'Edit <u>m</u>ode';
		break;
	case 2: // in edit mode
		tmp_link.innerHTML = 'Normal <u>m</u>ode';
		break;
	default: // error
		trace("ERROR: popup_mode=" + GM_getValue("popup_mode", 1));
		alert("Error !!! popup_mode unknown.");
		tmp_link.innerHTML = 'Edit <u>m</u>ode';
		break;
	}

	divL.appendChild (tmp_link);

	divL.appendChild (document.createTextNode(' '));

	// Category list
	if (pos==0) { // top toolbar
		var selection = document.createElement('select');
		selection.setAttribute('name','Category');
		selection.id = "cat";
		selection.style.verticalAlign='bottom';

		for(var i=0; i < emuleCat.length; i++) {
			trace('emuleCat['+i+'] => '+emuleCat[i].name+'='+emuleCat[i].value+' ('+emuleCat[i].select+')');
			var element = new Array()
			element[i] = document.createElement('option');
			element[i].setAttribute('value',emuleCat[i].value);
			element[i].text = emuleCat[i].name;
			if (emuleCat[i].select==1) {
				element[i].setAttribute('selected',1);
			}
			selection.appendChild(element[i]);
		}

		if(ed2kDlMethod=='local' || ed2kDlMethod=='mldonkey') {
			selection.disabled = true;
		}

		selection.addEventListener('change', function(){ changeCat(); }, false );
		divL.appendChild(selection);
		divL.appendChild (document.createTextNode(' '));
	}

	// Configuration Link
	tmp_link=document.createElement('button');
	tmp_link.addEventListener('click', function(){ setButton();}, false );
	tmp_link.innerHTML = '<u>S</u>ettings';
	divR.appendChild (tmp_link);

	divR.appendChild (document.createTextNode(' '));

	// Close link
	tmp_link=document.createElement('button');
	tmp_link.addEventListener('click', function(){ closeButton(); }, false );
	tmp_link.innerHTML = '<u>C</u>lose';
	divR.appendChild (tmp_link);

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
	// no popup on a page without ed2k links: nothing to switch, and the stored mode stays as it is
	if (eLinks.length == 0) {
		trace("editButton() no ed2k link in this page");
		return;
	}
	switch(GM_getValue("popup_mode", 1)) {
	case 1: // in normal mode
		GM_setValue("popup_mode",2);
		updatePopup();
		break;

	case 0: // popup closed
	case 2: // in edit mode
		GM_setValue("popup_mode",1);
		updatePopup();
		break;

	default:
		trace("ERROR: popup_mode=" + GM_getValue("popup_mode", 1));
		alert("Error !!! popup_mode unknown.");
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
* Actions when "Close" button is pressed
*/
function closeButton() {
	trace("closeButton()");
	var candidate=document.getElementById("theDiv");
	if (candidate) {
		candidate.parentNode.removeChild(candidate);
	}
	GM_setValue("popup_mode",0);
}

/**
* Actions when the popup is opened: Ctrl+Alt+O, Ctrl+Alt+X when closed, menu "Open Popup"
* There is always one popup at most: an open popup is left as it is (its selection and
* its edit box are kept), and nothing is opened on a page without ed2k links (SF-1.12).
*/
function openButton() {
	trace("openButton()");
	if (eLinks.length == 0) {
		trace("openButton() no ed2k link in this page");
		return;
	}
	if (document.getElementById("theDiv")) {
		return;		// already open
	}
	GM_setValue("popup_mode", 1);
	createPopup(eLinks, eFiles, eSizes);
}

/**
* Actions when "Check" button is pressed
*/
function checkButton() {
	trace("checkButton()");
    var i=0;
	var checkbox=document.getElementById("checkall");
	var line;
	if (checkbox.checked==true) {
		for (i=0; i<eLinks.length; i++) {
			line = document.getElementById('l'+i);
			if (line != null) { line.checked=true; }
		}
	}
	else {
		for (i=0; i<eLinks.length; i++) {
			line = document.getElementById('l'+i);
			if (line != null) { line.checked=false; }
		}
	}
}

/**
* Actions when category is changed
*/
function changeCat() {
	trace("changeCat()");

	var cat=document.getElementById("cat");

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
	refreshLinkUrls();
}

/**
* Update the URL of the file name links of the popup after a category change
* Only these links depend on the category (getAddLink()): the popup is not rebuilt, so
* that the checkboxes, the edit box, the size and the scroll of the popup are kept (A-7).
*/
function refreshLinkUrls() {
	var anchors = document.querySelectorAll('#divBody a.ed2k');
	for (var i=0; i<anchors.length; i++) {
		anchors[i].setAttribute('href', linkHref(eLinks[i]));
	}
}

/**
* The href of a file name link of the popup
* For the custom method the links are sent with a POST form, which a link cannot do: the
* href is then the ed2k link itself (shown on hover, copied by "Copy link"), and a click on
* it is turned into the POST by clickOneLink() (A-14).
* @param link the ed2k link
* @return the href of its link in the popup
*/
function linkHref(link) {
	return ed2kDlMethod == 'custom' ? encodeEd2kLink(link) : getAddLink([link]);
}

/**
* A click on a file name of the popup, with the custom method: the link cannot send the
* POST form itself, this sends it for this file only. The other methods: nothing to do,
* the link does the job.
* @param e the click event, caught on the list of links
*/
function clickOneLink(e) {
	var a = e.target.closest('a.ed2k');
	if (!a || ed2kDlMethod != 'custom') {
		return;
	}
	e.preventDefault();
	var anchors = document.querySelectorAll('#divBody a.ed2k');
	post(emuleUrl, getAddLink([eLinks[[].indexOf.call(anchors, a)]]));
}

/**
* Actions when "Add all links" button is pressed
*/
async function addButton() {
	trace("addButton()");
	var href="";
	var links=new Array();

	switch(GM_getValue("popup_mode", 1)) {
		case 0: // popup closed
		case 1: // in normal mode
			links=getSelectLink(eLinks);
			break;
		case 2: // in edit mode
			var txt = document.getElementById("editbox");
			if (txt == null) {
				// edit mode is the stored preference but the popup was never built
				// on this page (no link found, or popup closed): nothing to read
				links=getSelectLink(eLinks);
			}
			else {
				links=txt.value.split('\n');
			}
			break;
		default:
			trace("ERROR: popup_mode=" + GM_getValue("popup_mode", 1));
			alert("Error !!! popup_mode unknown.");
			return;
	}

	if (links.length == 0) {
		trace("addButton() nothing to send");
		return;
	}

	href = getAddLink(links);
	trace("href="+href);

	if(ed2kDlMethod=='local') {
		for (var i=0; i<links.length; i++) {
			openLocalLink(links[i]);
		}
	} else if(ed2kDlMethod=='custom') {
		post(emuleUrl, href);
/*	} else if(ed2kDlMethod=='amule') {
        post(emuleUrl + "footer.php", href);

        // Below won't work for security reasons. Browser will block it
        /* var url = emuleUrl + "footer.php";
        var params = href;
        silentPost(url, params);*/
	} else if(ed2kDlMethod=='amule') {
        var a_win = null;

        // This is a tweak to bypass amule login page
        if(emulePwd != "") {
            trace("Send password to make sure we are logged in and wait 1 sec... then...");
            a_win = window.open(emuleUrl + "footer.php?pass=" + emulePwd, 'amule');
            await sleep(1000); // Should be enough to bypass the login page. We don't want to wait too much to avoid slowing down the sending of links.
            //loadChildWindow(emuleUrl + "login.php?pass="+ emulePwd +"&submit=Submit", 'amule');
        }
        trace("Sending ed2k links to amule");
        //loadChildWindow(href, 'amule');
        a_win = window.open(href, 'amule');
        a_win.blur(); // Deprecated in most recent browsers
	}
	else {
        var e_win = window.open(href, 'emule');
		e_win.blur(); // Deprecated in most recent browsers
	}
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
* it (older ones did it on their own, see the 0.2 changelog entry).
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

// Not working
async function loadChildWindow(href, name) {
    childWindow = window.open(href, name);
    await waitReady();
    console.log("Child Window is Ready..");
}

/**
* Wait for x milliseconds
*/
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// -------------------------------------------------------------------------
/**
* Get selected links
* When the popup is not displayed there is no checkbox to read: every link of
* the page is then considered as selected.
* @param links the ed2k links found in the page
* @return the selected links
*/
function getSelectLink(links) {
	var lnk= new Array();
	var idx=0;
	var checkbox;

	for (var i=0; i<links.length; i++) {
		checkbox = document.getElementById('l'+i);
		if (checkbox == null || checkbox.checked == true) {
			lnk[idx]=links[i];
			idx++;
		}
	}
	return lnk;
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
      // GET method: then we encode the link (so the filename is encoded twice)
      lnk=encodeURIComponent(lnk);
      url = emuleUrl + "?w=password&p=" + emulePwd + "&cat=" + cat + "&c=" + lnk;
		  break;

    case 'amule':
      if(cat == "0") {
        cat = "all";
      }

      // Using Get method: we encode the link (so the filename is encoded twice)
      lnk=encodeURIComponent(lnk);
      if(emulePwd != '') {
          url = emuleUrl + "footer.php?pass=" + emulePwd + "&selectcat=" + cat + "&Submit=Download+link&ed2klink=" + lnk;
      } else {
          url = emuleUrl + "footer.php?selectcat=" + cat + "&Submit=Download+link&ed2klink=" + lnk;
      }

      // Using Post method
      /*url = new Array();
      url["selectcat"] = cat;	// the category
      url["Submit"] = "Download+link";	// Submit
      url["ed2klink"] = lnk;	// the ed2k links*/
			break;

    case 'mldonkey':
			// GET method: then we encode the link (so the filename is encoded twice)
      lnk=encodeURIComponent(lnk);
      url = emuleUrl + "submit?jvcmd=multidllink&links=" + lnk;
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

	// Configure Settings dialog
	GM_config.init(configDiv, 'Emule Linker Settings dialog', {
		'section1' : { section: ['ed2k download mode', 'Please refer to your emule/amule/mldonkey configuration'], label: '', type: 'hidden'},
		/*'ed2kDlMethod': { label: 'Ed2k Download Method', title: 'local: local application that handle ed2k links (default)\nemule: remote emule (via web frontend)\namule: remote amule (via web frontend)\nmldonkey: remote mldonkey (via web frontend)\ncustom: custom server implementation (experimental)', type:'radio', options:['local','emule','amule','mldonkey','custom'], default: ed2kDlMethod },*/
		'ed2kDlMethod': { label: 'Ed2k Download Method', title: 'local: local application that handle ed2k links (default)\nemule: remote emule (via web frontend)\namule: remote amule (via web frontend)\nmldonkey: remote mldonkey (via web frontend)\ncustom: custom server implementation (experimental)', type:'select', options:{'local':'your system default','emule':'(remote) emule','amule':'(remote) amule','mldonkey':'(remote) mldonkey','custom':'custom (experimental)'}, default: ed2kDlMethod}, // default value doesn't work with a dropdown menu => see bugfix in the lib
		'emuleUrl': { label: 'Emule Url', title : 'The complete url of your emule web server ending by a / (example: http://127.0.0.1:4711/)', type: 'text', default: emuleUrl },
		'emulePwd': { label: 'Emule Password', title : 'the password you choose to access your emule web server (optional: leave it empty if your web server has none)', type: 'text', default: emulePwd },
		'emuleCat': { label: 'Category', title : 'categories available in your emule/amule application. You can add categories using the following template:\ncategory_name1=corresponding_index_in_emule;category_name2=...\nAdding a * before the name specify the default choice.\nIf you don\'t know what you are doing just specify this: *default=0', type: 'text', default: catToStr(emuleCat) },
		'section2' : { section: ['Popup Configuration', 'modify how the popup is displayed'], label: '', type: 'hidden'},
		'popupPos': { label: 'Popup Position', title : 'choosing \'absolute\', the popup will stay at the top. Choosing fixed, the popup will follow as you scroll within the page', type: 'radio', options:['absolute','fixed'], default: popupPos },
		'popupHeight': { label: 'Max Popup Height in px (0=unlimited)', title : 'Max height of the popup in pixels (0=unlimited)', type: 'int', default: popupHeight },
		'popupWidth': { label: 'Max Popup Width in px (0=unlimited)', title : 'Max width of the popup in pixels (0=unlimited)', type: 'int', default: popupWidth },
		'section3' : { section: ['Edit box Configuration', 'modify how the edit box is displayed'], label: '', type: 'hidden'},
		'editCol': { label: 'Number of columns', title : 'number of columns', type: 'radio', type: 'int', default: editCol },
		'editRow': { label: 'Number of rows', title : 'Number of rows', type: 'int', default: editRow },
		},
		{
		//open: function() { GM_config.sections2tabs(); }, // not working (not included into the library)
		save: function() { location.reload(); } // reload the page when configuration was changed
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
	emulePwd = GM_config.get('emulePwd');

	emuleCat = strToCat(GM_config.get('emuleCat'));
	if(emuleCat==-1) {
		alert("Category value invalid. Reverting back to the default value (*default=0)");
		GM_config.set('emuleCat', '*default=0');
		emuleCat = strToCat('*default=0');
		corrected.emuleCat = '*default=0';
	}

	popupPos = GM_config.get('popupPos');

	popupHeight = GM_config.get('popupHeight');
	if (popupHeight > 0 && popupHeight < 40 ) {
		alert("With a 'Max Popup Height' beetween 0 < x < 40px, you won't be able to press the Settings button. So we consider this value as 0 (unlimited)");
		GM_config.set("popupHeight",0);
		popupHeight = 0;
		corrected.popupHeight = 0;
	}

	popupWidth = GM_config.get('popupWidth');
	if (popupWidth > 0 && popupWidth < 100 ) {
		alert("With a 'Max Popup Width' beetween 0 < x < 100 px, you won't be able to press the Settings button. So we consider this value as 0 (unlimited)");
		GM_config.set("popupWidth",0);
		popupWidth = 0;
		corrected.popupWidth = 0;
	}

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
		str +=cat[i].name+'=';
		str +=cat[i].value +';';
	}

	trace('catToStr() -> ' + str);
	return str;
}

/**
* String to category array
* Expected format: [*]name=value;[*]name=value;...  (the * marks the default category)
* Invalid entries are skipped. Exactly one category ends up selected, so that the
* drop-down list and the category sent (getSelectedCat()) always agree.
* @param str the categories as entered in the settings
* @return the category array, or -1 when the string holds no valid category
*/
function strToCat(str) {
	var cat = new Array();
	var tab = String(str).split(';');
	var tmp, name, value, select;
	var hasDefault = false;

	//trace ('strToCat('+str+')');

	for (var i=0; i<tab.length; i++) {
		if (tab[i].trim() == '') {
			continue;	// empty entry, typically after the last ;
		}

		tmp = tab[i].split('=');
		name = tmp[0].trim();
		value = (tmp.length > 1) ? tmp[1].trim() : '';
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

/*
function silentGet(url) {
	var req = new XMLHttpRequest();

	req.onreadystatechange = function() {
        //silentClose(url, "emule");
    }
	req.open("GET", url, true);
	req.send("");
}
*/

/**
* Submit a post using ajax call
*
* This should be a better way to send post forms but new browser doesn't accept silent calls to remote systems
* If your emule is not using HTTPS, you will have mixed content blocking
* Even if the remote system is HTTPS, browsers restrict cross-origin HTTP requests initiated from scripts
*/
function silentPost(url, params) {
	var req = new XMLHttpRequest();

    req.onreadystatechange = function() { //Call a function when the state changes.

        //document.getElementById(target).innerHTML = req.responseText;
        if (req.readyState == 4) {
            trace("Post sent with response code ["+req.status+"]"); // Données textuelles récupérées
            if (req.status == 200 || req.status == 0) {
                alert("OK: "+req.responseText); // Données textuelles récupérées
            } else {
                alert("KO: "+req.responseText); // Données textuelles récupérées
            }
        }
	}

	req.open("POST", url, true);
	req.setRequestHeader("Content-Type", "application/x-www-form-urlencoded");

	var data="";
	for(var key in params) {
        if(params.hasOwnProperty(key)) {
			if(data=="") {
				data=key+"="+encodeURIComponent(params[key]);
			} else {
				data=data+"&"+key+"="+encodeURIComponent(params[key]);
			}
		}
	}
	req.send(data);
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

