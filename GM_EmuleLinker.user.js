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
// @version     0.12
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
// keyboard shortcuts (Ctrl+Alt+A to send the links).
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
	// amuleapi: aMule 3.1 and later via its REST API
	// amule: amule via web url
	// mldonkey: mldonkey via web url
	// custom: custom via web url

var emuleUrl = 'http://127.0.0.1:4711/'; 	// the adress and port of your emule web server
var emuleUser = 'admin'; // the user of the web interface of MLDonkey (its default one)
var emulePwd = ''; // the password to access the emule web server (optional)
var emuleCat = [ {name: 'default', value: '0', select: '1'} ]; // Which emule category to assign 0=all (default)

// Popup parameters
var popupPos = 'fixed'; // absolute or fixed
var popupHeight = 800; // max height in pixel of the popup box
var popupWidth = 800; // max width in pixel of the popup box

// edit box parameters
var editCol = 80; // number of column
var editRow = 16; // number of line

// The GitHub repository of the script, linked from the bottom of the settings dialog: its issues, to
// report a problem, and the repository itself. If it moves, change also @updateURL and @downloadURL
// in the header, but never @namespace: it identifies the installed script (a new one would be added).
var REPOSITORY = 'https://github.com/alo0/GM_EmuleLinker';



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
/**
* Main : The entry point of the script
*/
var eLinks=new Array();
var eFiles=new Array();
var eSizes=new Array();

var sendingBusy = false;	// a sending (aMule, eMule, MLDonkey) waits for its answer, see setSending()
var statusTimer = null;		// animation of the "Please wait" message, see showStatus()

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
	+ "\n#GM_config .config_header { font-size: 15px; font-weight: bold; padding: 10px 14px; text-align: left;"
	+ " border-bottom: 1px solid #ccd; display: flex; justify-content: space-between; align-items: center; }"
	+ "\n#GM_config .helpbtn { font-size: 12px; font-weight: normal; padding: 3px 10px; }"
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
	// the long values (address, categories) take the whole width of the column, as their help
	+ "\n#GM_config #GM_config_field_emuleUrl, #GM_config #GM_config_field_emuleCat { grid-column: 2 / -1;"
	+ " width: 100%; box-sizing: border-box; }"
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
var dialogServers = null;	// in the settings dialog: {active: id or null for Local, list: [{id, name, method, emuleUrl, emuleUser, emulePwd, emuleCat}]}
var dialogEdited = null;	// in the settings dialog: the id of the server whose settings are displayed, or null
var CATEGORY_ERROR = 'No valid category: write them as name=value, separated by ; (e.g. *default=0;Video=2)';
var SERVER_URL = /^https?:\/\/[^\/\s]+/i;	// the Server URL of every method: http or https only
var SERVER_URL_ERROR = 'An address starting with http:// or https:// is expected, e.g. http://127.0.0.1:4711/';

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
					border:2px solid #2b5c8a;\
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
		div#theDiv div, div#divBody td, div#divBody th { text-align: left; } \
		div#theDiv, div#theDiv * { letter-spacing: normal; word-spacing: normal; text-transform: none; \
			text-indent: 0; font-style: normal; } \
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
			// toolbars always stay visible, whatever the number of links (SF-2.9)
			container.style.display='flex';
			container.style.flexDirection='column';
			container.style.overflow='hidden';
			tmp_link.style.flex='1 1 auto';
			tmp_link.style.minHeight='0';
			tmp_link.style.overflow='auto';
			// custom method: a click on a file name sends it with a POST form (SF-3.3)
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
	// while the list of links scrolls (SF-2.9)
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
	tmp_link.className = 'emlAdd';	// disabled while a sending waits for its answer (setSending())
	tmp_link.disabled = sendingBusy;
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
	// nothing else to do: the popup is not rebuilt, and no link of the popup carries the category,
	// read when sending (SF-6.6, SF-6.8)
}

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
* Actions when "Add all links" button is pressed
*/
function addButton() {
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
		showStatus('No ed2k link to send', false);
		return;
	}
	trace('sendToAmuleApi() ' + body.links.length + ' link(s), category ' + body.category_index);
	setSending(true);
	showStatus('Please wait', null);	// until the answer of aMule replaces it
	try {
		r = await gmRequest('POST', api + 'auth/login?include_token=true', {password: emulePwd});
		if (r.status != 200 || r.json == null || !r.json.token) {
			showStatus(amuleApiError(r), false);
			return;
		}
		token = r.json.token;
		r = await gmRequest('POST', api + 'downloads', body, token, sendingTimeout(body.links.length));
		showStatus(amuleApiResult(body.links, r), r.status == 202);
	}
	catch (e) {
		trace('sendToAmuleApi() ' + e);
		if (e.timeout) {
			// aMule received the request but answers late: the links may well be added
			showStatus('aMule has not answered within ' + Math.round(e.timeout / 1000) + ' s: the links may still be added, check aMule', false);
		}
		else {
			showStatus('aMule can not be reached at ' + emuleUrl, false);
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
		showStatus('No ed2k link to send', false);
		return;
	}
	trace('sendToEmule() ' + req.count + ' link(s)');
	setSending(true);
	showStatus('Please wait', null);	// until the answer of eMule replaces it
	try {
		r = await gmRequest('GET', req.url, null, null, sendingTimeout(req.count));
		result = emuleResult(req.count, r);
		showStatus(result[0], result[1]);
	}
	catch (e) {
		trace('sendToEmule() ' + e);
		if (e.timeout) {
			// eMule received the request but answers late: the links may well be added
			showStatus('eMule has not answered within ' + Math.round(e.timeout / 1000) + ' s: the links may still be added, check eMule', false);
		}
		else {
			showStatus('eMule can not be reached at ' + emuleUrl, false);
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
		return [count + ' link(s) added to eMule', true];
	}
	if (status && status[2] && status[2].toUpperCase() == 'WRONG_PASSWORD') {
		return ['eMule refused the password', false];
	}
	if (status) {
		return ['eMule refused the links' + (status[2] ? ' (' + status[2] + ')' : ''), false];
	}
	return ['Links sent, but the answer of eMule is not understood: check its transfer list', 'doubt'];
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
		showStatus('No ed2k link to send', false);
		return;
	}
	trace('sendToAmuleWeb() ' + req.count + ' link(s)');
	setSending(true);
	showStatus('Please wait', null);
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
			showStatus('Links sent, but the transfer list of aMule could not be read: check it', 'doubt');
			return;
		}
		if (found == req.count) {
			showStatus(req.count + ' link(s) added to aMule', true);
		}
		else {
			showStatus(found + ' of ' + req.count + ' link(s) found in the transfer list of aMule: check it', 'doubt');
		}
	}
	catch (e) {
		trace('sendToAmuleWeb() ' + e);
		if (e.timeout) {
			showStatus('aMule has not answered within ' + Math.round(e.timeout / 1000) + ' s: the links may still be added, check aMule', false);
		}
		else {
			showStatus('aMule can not be reached at ' + emuleUrl, false);
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
		return 'aMule refused the password';
	}
	if (r.status == 200 && /amuleweb-main/i.test(r.text)) {
		return null;
	}
	return 'No aMule 2.x web interface at ' + (url || emuleUrl);
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
* The value of an HTTP Basic authorization: the user and the password, in UTF-8, in base 64
*/
function basicAuth(user, password) {
	var bytes = new TextEncoder().encode(user + ':' + password);
	return 'Basic ' + btoa(Array.prototype.map.call(bytes, function (b) { return String.fromCharCode(b); }).join(''));
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
		showStatus('No ed2k link to send', false);
		return;
	}
	trace('sendToMldonkey() ' + req.count + ' link(s)');
	setSending(true);
	showStatus('Please wait', null);
	try {
		r = await gmRequest('GET', req.url, null, basicAuth(emuleUser, emulePwd), sendingTimeout(req.count));
		result = mldonkeyResult(req.count, r, emuleUrl);
		showStatus(result[0], result[1]);
	}
	catch (e) {
		trace('sendToMldonkey() ' + e);
		if (e.timeout) {
			showStatus('MLDonkey has not answered within ' + Math.round(e.timeout / 1000) + ' s: the links may still be added, check MLDonkey', false);
		}
		else {
			showStatus('MLDonkey can not be reached at ' + emuleUrl, false);
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
* @return [message, kind]: kind true (every link added or already there), false (refused, or an
* error), 'doubt' (an answer of MLDonkey that tells nothing about the links)
*/
function mldonkeyResult(count, r, url) {
	var added = (r.text.match(/Added link/g) || []).length;
	var already = (r.text.match(/already in download queue/g) || []).length;
	var unmatched = (r.text.match(/Unable to match URL/g) || []).length;
	var refused = Math.max(0, unmatched - already);

	if (r.status == 401) {
		return ['MLDonkey refused the user or the password', false];
	}
	if (r.status != 200 || !/MLdonkey/i.test(r.text)) {
		return ['No MLDonkey web interface at ' + url, false];
	}
	if (added + unmatched == 0) {
		return ['Links sent, but the answer of MLDonkey is not understood: check its downloads', 'doubt'];
	}
	if (refused == 0) {
		return [count + ' link(s) added to MLDonkey', true];
	}
	return [(count - refused) + ' link(s) added to MLDonkey, ' + refused + ' refused', false];
}

/**
* Mark a sending to aMule, eMule or MLDonkey as in progress or finished
* While it waits for its answer, the "Add all links" buttons are disabled, and the sendings
* (sendToAmuleApi(), sendToEmule(), sendToAmuleWeb(), sendToMldonkey()) ignore any other one
* (shortcut, click on a file name).
* @param busy true when the sending starts, false when its answer has arrived
*/
function setSending(busy) {
	var buttons = document.querySelectorAll('#theDiv button.emlAdd');

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
			return 'aMule refused the password';
		case 403:
			return 'This password can not add downloads: the admin password of aMule is needed';
		case 200:	// a page, not the answer of the API: an older aMule, or another server
		case 404:
			return 'No aMule API at ' + (url || emuleUrl) + ' (aMule 3.1 or later is needed)';
		case 429:
			return 'Too many failed logins to aMule' + (r.retryAfter ? ', retry in ' + r.retryAfter + ' s' : '');
		case 503:
			return 'aMule is not connected to its core (amuled)';
		default:
			return 'aMule answered HTTP ' + r.status + detail;
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
		return links.length + ' link(s) added to aMule';
	}
	if (r.status == 207) {
		if (refused.length > 0 && refused[0].error && refused[0].error.message) {
			why = ': ' + refused[0].error.message;
		}
		return (links.length - refused.length) + ' link(s) added to aMule, ' + refused.length + ' refused' + why;
	}
	return amuleApiError(r);
}

/**
* Show the result of a sending to the user
* In the popup, a line under the top toolbar. With the popup closed there is nowhere to
* show it: only the errors and the doubts are then shown, in an alert, so that a failure is
* never silent. While waiting (ok = null), the message is followed by animated dots, until the
* next message replaces it.
* @param msg the message
* @param ok true for a success (green), false for an error (red), 'doubt' for an answer that is
* not understood (orange: the links may still be added), null while waiting
*/
function showStatus(msg, ok) {
	var container = document.getElementById('theDiv');
	var line = document.getElementById('emlStatus');
	var bar;
	var dots = 0;

	trace('showStatus() ' + msg);
	if (statusTimer != null) {
		clearInterval(statusTimer);
		statusTimer = null;
	}
	if (container == null) {
		if (ok === false || ok === 'doubt') {
			alert('Emule Linker: ' + msg);
		}
		return;
	}
	if (line == null) {
		line = document.createElement('div');
		line.id = 'emlStatus';
		line.style.flex = 'none';		// never shrunk in the popup column
		line.style.padding = '2px 0';
		line.style.fontWeight = 'bold';
		bar = container.querySelector('.toolbar');
		container.insertBefore(line, bar ? bar.nextSibling : container.firstChild);
	}
	if (ok == null) {
		line.style.color = '#555';
		line.textContent = msg + '...';
		statusTimer = setInterval(function () {
			dots = (dots + 1) % 4;
			line.textContent = msg + '.'.repeat(dots);
		}, 400);
		return;
	}
	line.style.color = ok === 'doubt' ? '#a65f00' : ok ? '#060' : '#c00';
	line.textContent = msg;
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
		'section1' : { section: ['Servers', 'Where the ed2k links are sent: the servers you use, and the one that receives the links'], label: '', type: 'hidden'},
		'ed2kDlMethod': { label: 'Ed2k Download Method', title: 'How the links are sent:\nLocal: to the application of your system that handles ed2k links (default)\neMule (web): to eMule, on this computer or another one, through its web interface\naMule 3.x (amuleapi): to aMule 3.1 or later, through its REST API\naMule 2.x (amuleweb): to aMule 2.x, through its web interface\nMLDonkey (web): to MLDonkey, through its web interface\nCustom: posted to your own server', type:'select', options:{'local':'Local (your system default)','emule':'eMule (web)','amuleapi':'aMule 3.x (amuleapi)','amule':'aMule 2.x (amuleweb)','mldonkey':'MLDonkey (web)','custom':'Custom (post to your own server)'}, default: ed2kDlMethod}, // default value doesn't work with a dropdown menu => see bugfix in the lib
		'emuleUrl': { label: 'Server URL', title : 'The address of the web interface of eMule, aMule or MLDonkey, or of your own server.\nFor instance http://127.0.0.1:4711/ (a final / is added when missing).', type: 'text', size: 32, default: emuleUrl },
		'emuleUser': { label: 'User', title : 'The user of the web interface of MLDonkey (admin by default).', type: 'text', size: 20, default: emuleUser },
		'emulePwd': { label: 'Password', title : 'The password of the web interface. Optional: leave it empty if it has none.\nFor aMule 3.x, its admin password. Test (eMule, aMule, MLDonkey) checks the Server URL and the password, without saving them.', type: 'text', size: 20, default: emulePwd },
		'emuleCat': { label: 'Category', title : 'The categories offered in the popup, as name=value, separated by ;\nA * before a name makes it the default one.\neMule and aMule 3.x: the value is the number of the category (0: the default category), e.g. *default=0;Video=2\neMule and aMule: Import fills the field with their categories, in their order.\naMule 2.x: the value is the name of the category, e.g. *Audio=audio;Video=Video (a ; in a name is written \\;)', type: 'text', size: 40, default: catToStr(emuleCat) },
		'section2' : { section: ['Popup', 'How the popup is displayed'], label: '', type: 'hidden'},
		'popupPos': { label: 'Popup Position', title : 'fixed: the popup stays in view when the page scrolls.\nabsolute: the popup stays at the top of the page.', type: 'radio', options:['absolute','fixed'], default: popupPos },
		'popupHeight': { label: 'Max Popup Height in px (0=unlimited)', title : 'The maximum height of the popup, in pixels: at least 40, or 0 for unlimited.', type: 'int', size: 6, default: popupHeight },
		'popupWidth': { label: 'Max Popup Width in px (0=unlimited)', title : 'The maximum width of the popup, in pixels: at least 100, or 0 for unlimited.', type: 'int', size: 6, default: popupWidth },
		'section3' : { section: ['Edit box', 'The size of the text box of the edit mode'], label: '', type: 'hidden'},
		'editCol': { label: 'Number of columns', title : 'The width of the edit box, in characters.', type: 'int', size: 4, default: editCol },
		'editRow': { label: 'Number of rows', title : 'The height of the edit box, in lines.', type: 'int', size: 4, default: editRow },
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

// -------------------------------------------------------------------------
// Settings dialog: look and behavior added to the dialog built by GM_config
// -------------------------------------------------------------------------

/**
* The title of the settings dialog, with the version of the script given by the userscript manager
*/
function settingsTitle() {
	var version = (typeof GM_info != 'undefined' && GM_info.script) ? GM_info.script.version : '';
	return 'Emule Linker ' + (version ? version + ' ' : '') + '\u2014 Settings';
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
			help.textContent = text;
			row.appendChild(help);
		}
	}

	// the password is masked, a button shows it
	pwd.type = 'password';
	pwd.autocomplete = 'off';
	reveal = document.createElement('button');
	reveal.type = 'button';
	reveal.className = 'reveal';
	reveal.textContent = 'Show';
	reveal.addEventListener('click', function () {
		pwd.type = (pwd.type == 'password') ? 'text' : 'password';
		reveal.textContent = (pwd.type == 'password') ? 'Show' : 'Hide';
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

	// a Help button that shows or hides the helps of every field, the choice being kept
	addHelpButton();

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
	var links = [['GM_config_issuesLink', REPOSITORY + '/issues', 'Report a problem ↗'],
		['GM_config_repoLink', REPOSITORY, 'Emule Linker on GitHub ↗']];

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
	dialogEdited = dialogServers.active;

	list.className = 'slist';
	list.id = 'GM_config_servers';
	row.insertBefore(list, row.querySelector('.help'));
	row.querySelector('.help').textContent = 'The checked server receives the links: Local, or one of your servers.\n'
		+ 'Each server has a name, a download method and its own settings, shown by Edit: several servers of the same kind are possible.\n'
		+ 'Delete removes a server, + Add a server adds one. Save stores all of them.';

	// the settings of a server: its name, its method, then the fields of GM_config that the method uses
	fields.className = 'sfields';
	fields.id = 'GM_config_server_fields';
	fields.appendChild(settingRow('serverName', 'Name', 'input',
		'A name to tell your servers apart, required and different for each server.'));
	fields.appendChild(settingRow('serverMethod', 'Ed2k Download Method', 'select',
		GM_config.fields.ed2kDlMethod.settings.title));
	for (var i=0; i<METHOD_SETTINGS.length; i++) {
		fields.appendChild(document.getElementById('GM_config_' + METHOD_SETTINGS[i] + '_var'));
	}
	list.appendChild(fields);

	add.className = 'sadd';
	addBtn.type = 'button';
	addBtn.id = 'GM_config_addServer';
	addBtn.textContent = '+ Add a server';
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
	help.textContent = helpText;
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
	label.textContent = server ? server.name : 'Local';
	badge.className = 'method';
	badge.textContent = server ? methodLabel(server.method) : 'your system default';
	badge.title = badge.textContent;	// the whole name, when the badge is too narrow for it
	sum.className = 'sum' + (server ? '' : ' none');
	sum.textContent = server ? server.emuleUrl : 'nothing to configure';
	acts.className = 'acts';
	if (server) {
		var edit = document.createElement('button');
		var del = document.createElement('button');
		edit.type = 'button';
		edit.className = 'edit';
		edit.textContent = 'Edit';
		edit.style.visibility = (dialogEdited == id) ? 'hidden' : '';
		edit.addEventListener('click', function () { editServer(id); }, false);
		del.type = 'button';
		del.className = 'del';
		del.textContent = 'Delete';
		del.addEventListener('click', function () { deleteServer(id); }, false);
		acts.appendChild(edit);
		acts.appendChild(del);
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
		errors.push(['serverName', 'A name is required']);
	}
	else if (dialogServers.list.some(function (srv) {
			return srv.id != dialogEdited && srv.name.trim().toLowerCase() == name.toLowerCase(); })) {
		errors.push(['serverName', 'Another server already has this name']);
	}
	if (METHOD_FIELDS[method].indexOf('emuleUrl') != -1 && !SERVER_URL.test(settingsField('emuleUrl').value.trim())) {
		errors.push(['emuleUrl', SERVER_URL_ERROR]);
	}
	if (METHOD_FIELDS[method].indexOf('emuleCat') != -1 && strToCat(settingsField('emuleCat').value.trim()) == -1) {
		errors.push(['emuleCat', CATEGORY_ERROR]);
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
	var name = 'New server';
	var n = 1;
	var server;

	if (!keepEditedServer()) {
		return;
	}
	clearSettingsMarks();
	while (dialogServers.list.some(function (srv) { return srv.name.toLowerCase() == name.toLowerCase(); })) {
		name = 'New server ' + (++n);
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
	if (dialogServers.active == id) {
		dialogServers.active = null;
	}
	if (dialogEdited == id) {
		dialogEdited = null;
	}
	showServers();
	// the notice goes before the server that followed the deleted one, or before "+ Add a server"
	next = dialogServers.list[index] ? document.getElementById('GM_config_server_' + dialogServers.list[index].id)
		: document.querySelector('#GM_config_servers .sadd');
	showNotice('Server "' + server.name + '" deleted, not saved yet.', function () {
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
		button.textContent = '\u21b6 Undo';
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
		make('GM_config_testBtn', 'Test', 'Test the server URL and the password', testServer));
	catbox.className = 'catbox';
	cat.parentNode.insertBefore(catbox, cat);
	catbox.appendChild(cat);
	catbox.appendChild(make('GM_config_importBtn', 'Import', 'Fill the field with the categories of eMule or aMule',
		importCategories));

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
	button.textContent = '↶ Undo';
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
		showSettingsError('emuleUrl', SERVER_URL_ERROR);
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
	return e.timeout ? client + ' has not answered within ' + Math.round(e.timeout / 1000) + ' s'
		: client + ' can not be reached at ' + url;
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
	var ctx = startApiAction(button, 'Test…');
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
			result = {which: 'test', kind: 'ko', text: 'MLDonkey refused the user or the password'};
		}
		else if (r.status == 200 && /MLdonkey/i.test(r.text)) {
			result = {which: 'test', kind: 'ok', text: 'Connected to MLDonkey' + (version ? ' ' + version[1].replace(/\.git$/, '') : '') + '.'};
		}
		else {
			result = {which: 'test', kind: 'ko', text: 'No MLDonkey web interface at ' + ctx.url};
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
	var ctx = startApiAction(button, 'Test…');
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
		result = {which: 'test', kind: 'ok', text: 'Connected to aMule ' + (version ? version[1] : '2.x') + '.'};
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
	var ctx = startApiAction(button, 'Test…');
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
				text: 'Connected to ' + (title && /emule/i.test(title[1]) ? title[1] : 'eMule') + '.'};
			// the session opened by this test is closed at once
			gmRequest('GET', ctx.url + '?ses=' + session[1] + '&w=logout', null, null).catch(function () {});
		}
		else if (r.status == 200 && /<input[^>]*type=["']?password/i.test(r.text)) {
			result = {which: 'test', kind: 'ko', text: 'eMule refused the password'};
		}
		else {
			result = {which: 'test', kind: 'ko', text: 'No eMule web interface at ' + ctx.url};
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
	var ctx = startApiAction(button, 'Test…');
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
			result = {which: 'test', kind: 'warn', text: 'Connected to ' + name
				+ ', but this password can not add downloads: the admin password of aMule is needed'};
		}
		else if (state.status == 503 || (state.json && state.json.ec_connected === false)) {
			result = {which: 'test', kind: 'warn', text: 'Connected to ' + name
				+ ', but aMule is not connected to its core (amuled): the links would be refused'};
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
				text: 'Connected to ' + name + (networks.length ? ' (' + networks.join(', ') + ')' : '') + '.'};
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
	var ctx = startApiAction(button, 'Import…');
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
			result = {which: 'import', kind: 'ko', text: 'No aMule 2.x web interface at ' + ctx.url};
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
		return {which: 'import', kind: 'ok', text: 'The field already holds the categories of ' + client + '.'};
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
	var ctx = startApiAction(button, 'Import…');
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
			result = {which: 'import', kind: 'ko', text: 'eMule refused the password'};
		}
		else {
			result = {which: 'import', kind: 'ko', text: 'No eMule web interface at ' + ctx.url};
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
	var ctx = startApiAction(button, 'Import…');
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
		entries.push({name: name || 'Category ' + index, index: byName ? raw.trim().replace(/;/g, '\\;') : index});
	}
	if (entries.length == 0) {
		return {value: '*Default=0', message: client + ' has no category: Default=0 is used.'};
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
		parts.push(added.length + ' new (' + names(added) + ')');
	}
	if (removed.length > 0) {
		parts.push(removed.length + ' removed (' + names(removed) + ')');
	}
	message = entries.length + (entries.length > 1 ? ' categories' : ' category') + ' imported from ' + client
		+ (parts.length ? ': ' + parts.join(', ') : '') + '. ' + def.name
		+ (oldDefault != '' && lower(def.name) == lower(oldDefault) ? ' stays' : ' is now') + ' the default (*).';
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
		button.textContent = on ? 'Hide help' : '? Show help';
		button.title = on ? 'Hide the explanations of the fields' : 'Show the explanation under every field';
	};

	button.type = 'button';
	button.id = 'GM_config_helpBtn';
	button.className = 'helpbtn';
	button.addEventListener('click', function () {
		var on = !root.classList.contains('helps');
		GM_setValue('settings_help', on ? 1 : 0);
		show(on);
	}, false);
	show(GM_getValue('settings_help', 0) == 1);
	document.getElementById('GM_config_header').appendChild(button);
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
	var others = ['popupPos', 'popupHeight', 'popupWidth', 'editCol', 'editRow'];
	var editor = ['serverName', 'serverMethod'].concat(METHOD_SETTINGS);

	button.type = 'button';
	button.id = 'GM_config_resetBtn';
	button.className = 'resetbtn';
	button.textContent = '\u21ba Reset to defaults';
	button.title = 'Set every setting back to its default value (not saved until you press Save)';
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
		if (changed == 0) {
			showNotice('Every setting already has its default value.', null);
			return;
		}
		showNotice(changed + ' setting' + (changed > 1 ? 's' : '') + ' set back to ' + (changed > 1 ? 'their' : 'its')
			+ ' default value (highlighted), not saved yet.', function () {
			dialogServers = JSON.parse(before.servers);
			dialogEdited = before.edited;
			for (var i=0; i<others.length; i++) {
				setSettingsFieldValue(others[i], before.values[others[i]]);
			}
			showServers();
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
		errors.push(['popupHeight', 'A whole number is expected']);
	}
	else if (parseInt(value('popupHeight'), 10) > 0 && parseInt(value('popupHeight'), 10) < 40) {
		errors.push(['popupHeight', 'At least 40 px, or 0 for unlimited: a smaller popup would hide its Settings button']);
	}
	if (!whole.test(value('popupWidth'))) {
		errors.push(['popupWidth', 'A whole number is expected']);
	}
	else if (parseInt(value('popupWidth'), 10) > 0 && parseInt(value('popupWidth'), 10) < 100) {
		errors.push(['popupWidth', 'At least 100 px, or 0 for unlimited: a smaller popup would hide its Settings button']);
	}
	if (!whole.test(value('editCol')) || parseInt(value('editCol'), 10) < 1) {
		errors.push(['editCol', 'A whole number, at least 1, is expected']);
	}
	if (!whole.test(value('editRow')) || parseInt(value('editRow'), 10) < 1) {
		errors.push(['editRow', 'A whole number, at least 1, is expected']);
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
		// a ; in a name or a value is written \; (strToCat())
		str +=String(cat[i].name).replace(/;/g, '\\;')+'=';
		str +=String(cat[i].value).replace(/;/g, '\\;') +';';
	}

	trace('catToStr() -> ' + str);
	return str;
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

