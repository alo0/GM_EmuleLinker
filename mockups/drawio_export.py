"""Editable mockups for draw.io, made from the real screens of the script: the starting point of the
design of a version, reworked in draw.io.

    python mockups/drawio_export.py [--language en|fr] [--theme <theme>] [<repository> [<output folder>]]

--language: the language of the screens (en by default, or fr); --theme: their theme, one of the table
THEMES of the script (light by default: Default light; win11, chrome, steel, oled). By default, the
repository is the parent folder of mockups/, and the output folder mockups/wip/, ignored by Git, as every
mockup, variant and work file: only the tools of mockups/ are versioned.

The script runs in headless Chrome through the test tools; the position, size, text and colors of
each element are read from the page and written as draw.io shapes, one page per scenario. Each shape
keeps in its data (Edit Data) the element it comes from (`mk`), to compare an edited file with this
one (drawio_diff.py). Layers: "Mockup" (editable); "Vertical guides" and "Horizontal guides" (dashed
lines, one color per group of aligned controls, each layer to hide when not needed); "Reference
(screenshot)" (the real rendering, hidden and locked). It writes
emulelinker_<version>_<language>_<theme>.generated.drawio, the version being the @version of the script,
and copies it to emulelinker_<version>_<language>_<theme>.drawio, the file to edit, only when that one
does not exist: the edits are never overwritten. drawio_render.py draws
the pages with draw.io itself, over the screenshots, to check that both agree.
"""
import argparse
import base64
import datetime
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_args = argparse.ArgumentParser(description='Editable draw.io mockups made from the real screens of the script.')
_args.add_argument('--language', default='en', help='the language of the screens: en (default) or fr')
_args.add_argument('--theme', default='light', help='the theme of the screens, one of THEMES in the script (default: light)')
_args.add_argument('root', nargs='?', default=os.path.dirname(HERE), help='the repository (default: the parent of mockups/)')
_args.add_argument('out', nargs='?', default=os.path.join(HERE, 'wip'), help='the output folder (default: mockups/wip/)')
ARGS = _args.parse_args()
ROOT, OUT, LANGUAGE, THEME = ARGS.root, ARGS.out, ARGS.language, ARGS.theme
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import run_tests  # noqa: E402
import take_screenshots as ts  # noqa: E402

with open(os.path.join(ROOT, 'GM_EmuleLinker.user.js'), encoding='utf-8') as _f:
    _script = _f.read()
VERSION = re.search(r'^// @version\s+(\S+)', _script, re.M).group(1)     # the version captured
_themes = re.findall(r'(?m)^\t(\w+): \{', _script[_script.index('var THEMES = {'):_script.index('\n};', _script.index('var THEMES = {'))])
_languages = re.findall(r'(?m)^\t(\w+): \{', _script[_script.index('var TEXTS = {'):_script.index('\n};', _script.index('var TEXTS = {'))])
if THEME not in _themes:
    sys.exit(f'unknown theme {THEME}: one of {", ".join(_themes)}')
if LANGUAGE not in _languages:
    sys.exit(f'unknown language {LANGUAGE}: one of {", ".join(_languages)}')
SETTINGS = dict(ts.SPEC_SETTINGS, language=LANGUAGE, theme=THEME)     # the fictitious settings of the screenshots, in this language and theme
NAME = f'emulelinker_{VERSION}_{LANGUAGE}_{THEME}'
FILE = os.path.join(OUT, NAME + '.drawio')                  # the file edited by the user: never overwritten
GENERATED = os.path.join(OUT, NAME + '.generated.drawio')  # what this script made, to compare the edited file with
ORIGIN = (40, 90)       # top left corner of the mockup on each page, under the title
SELECT_INSET = 4        # Chrome draws the text of a select 4 px inside its padding (measured)
DRAWIO_TOP = 4          # draw.io draws a label aligned at the top 4 px below its shape (measured, whatever the font size)

# Reads the shapes of the elements under the roots: boxes (background, border), texts (one per text
# node, with the font of its parent), and the controls (button, checkbox, radio, select, field).
# Each item belongs to the group of its nearest ancestor matching groupSel, if any.
WALKER = r"""
window.__mk = function (roots, groupSel) {
  var out = [], gid = 0, names = {};
  function hex(c) {
    var m = (c || '').match(/rgba?\(([\d.]+),\s*([\d.]+),\s*([\d.]+)(?:,\s*([\d.]+))?\)/);
    if (!m || (m[4] !== undefined && +m[4] < 0.05)) return null;
    return '#' + [m[1], m[2], m[3]].map(function (v) { return ('0' + (Math.round(+v)).toString(16)).slice(-2); }).join('');
  }
  function R(r) { return [r.left, r.top, r.width, r.height]; }
  function shown(el) {
    var s = getComputedStyle(el);
    return s.display != 'none' && s.visibility != 'hidden' && el.getClientRects().length > 0;
  }
  function font(el) {
    var s = getComputedStyle(el);
    return {color: hex(s.color), fs: parseFloat(s.fontSize), bold: +s.fontWeight >= 600, italic: s.fontStyle == 'italic',
            under: (s.textDecorationLine || '').indexOf('underline') >= 0,
            ff: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(), mono: /mono|consol|courier/i.test(s.fontFamily)};
  }
  function frame(s) {
    // the look of the system: a control whose border the page has not changed (outset or inset);
    // pl, pt: where its text starts (border and padding)
    return {bg: hex(s.backgroundColor), bc: hex(s.borderTopColor), bw: parseFloat(s.borderTopWidth),
            rad: parseFloat(s.borderTopLeftRadius), native: /outset|inset/.test(s.borderTopStyle),
            pl: (parseFloat(s.borderLeftWidth) || 0) + (parseFloat(s.paddingLeft) || 0),
            pt: (parseFloat(s.borderTopWidth) || 0) + (parseFloat(s.paddingTop) || 0)};
  }
  // the height of a line of the element: its line-height, or measured when it is "normal" (about
  // 1.33 times the font size with Segoe UI, where draw.io would take 1.2)
  function lineHeight(s) {
    if (s.lineHeight != 'normal') return parseFloat(s.lineHeight);
    var d = document.createElement('div');
    ['fontFamily', 'fontSize', 'fontWeight', 'fontStyle'].forEach(function (k) { d.style[k] = s[k]; });
    d.style.cssText += ';position:absolute;visibility:hidden;white-space:nowrap;line-height:normal;';
    d.textContent = 'Xg';
    document.body.appendChild(d);
    var h = d.getBoundingClientRect().height;
    d.remove();
    return h;
  }
  // the lines of a text node, as the page wraps it: [{text, r}]
  function lines(c) {
    var t = c.textContent, res = [], cur = null, rg = document.createRange();
    for (var i = 0; i < t.length; i++) {
      rg.setStart(c, i); rg.setEnd(c, i + 1);
      var rs = rg.getClientRects();
      if (!rs.length) continue;
      var r = rs[rs.length - 1], blank = /\s/.test(t[i]);
      if (cur && Math.abs(r.top - cur.top) > r.height / 2) cur = null;
      if (!cur) {
        if (blank) continue;
        cur = {top: r.top, left: r.left, right: r.right, bottom: r.bottom, s: ''};
        res.push(cur);
      }
      cur.s += t[i];
      if (!blank) cur.right = Math.max(cur.right, r.right);
      cur.bottom = Math.max(cur.bottom, r.bottom);
    }
    return res.map(function (l) { return {text: l.s.replace(/\s+/g, ' ').trim(), r: [l.left, l.top, l.right - l.left, l.bottom - l.top]}; })
              .filter(function (l) { return l.text; });
  }
  function group(el) {
    var g = groupSel ? el.closest(groupSel) : null;
    if (!g) return null;
    if (!g.dataset.mkg) { g.dataset.mkg = 'g' + (++gid); names[g.dataset.mkg] = g.id || String(g.className) || g.tagName.toLowerCase(); }
    return g.dataset.mkg;
  }
  function add(el, o) {
    o.g = group(el);
    o.mk = el.id || (el.name ? 'name=' + el.name : '') || String(el.className || '') || el.tagName.toLowerCase();
    if (el.title && !o.title) o.title = el.title;
    out.push(o);
  }
  // A block of text: only text, inline elements (bold, code, link...) and lists, without boxes nor
  // controls. It becomes one shape, its text in HTML, rather than one shape per line.
  var INLINE = {B: 1, STRONG: 1, I: 1, EM: 1, U: 1, A: 1, CODE: 1, SPAN: 1, BR: 1, SMALL: 1, KBD: 1, SUB: 1, SUP: 1};
  var LIST = {UL: 1, OL: 1, LI: 1};
  function plain(s) {
    return !hex(s.backgroundColor) && !['Top', 'Right', 'Bottom', 'Left'].some(function (k) {
      return parseFloat(s['border' + k + 'Width']) > 0 && s['border' + k + 'Style'] != 'none'; });
  }
  function textBlock(el) {
    if (!el.textContent.trim()) return false;
    var all = el.getElementsByTagName('*');
    for (var i = 0; i < all.length; i++) {
      var d = all[i], s = getComputedStyle(d);
      if (!INLINE[d.tagName] && !LIST[d.tagName]) return false;
      if (s.display == 'none') continue;
      if (INLINE[d.tagName] && s.display != 'inline') return false;
      if (!plain(s)) return false;
    }
    return true;
  }
  function esc(t) { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
  function ser(node, ps) {
    if (node.nodeType == 3) {
      var t = node.textContent;
      // a <br> where the browser wraps the line: draw.io, whose text is a little wider or narrower,
      // would wrap it elsewhere; and at each line feed of a text whose line feeds are kept (pre-line...)
      var out = '', rg = document.createRange(), feeds = /pre/.test(ps.whiteSpace);
      for (var i = 0; i < t.length; i++) {
        if (feeds && t[i] == '\n') {
          out = out.replace(/ $/, '') + '<br>';
          lineTop = null;
          continue;
        }
        if (/\s/.test(t[i])) {
          if (!/( |<br>)$/.test(out)) out += ' ';
          continue;
        }
        rg.setStart(node, i); rg.setEnd(node, i + 1);
        var rs = rg.getClientRects();
        if (rs.length) {
          var top = rs[rs.length - 1].top;
          if (lineTop !== null && Math.abs(top - lineTop) > rs[0].height / 2) out = out.replace(/ $/, '') + '<br>';
          lineTop = top;
        }
        out += esc(t[i]);
      }
      return out;
    }
    if (node.nodeType != 1) return '';
    var s = getComputedStyle(node), tag = node.tagName;
    if (s.display == 'none') return '';
    if (tag == 'BR') { lineTop = null; return '<br>'; }
    if (tag == 'LI' || tag == 'UL' || tag == 'OL') lineTop = null;     // a block starts a new line by itself
    var inner = [].map.call(node.childNodes, function (c) { return ser(c, s); }).join(''), css = [];
    if (tag == 'LI' || tag == 'UL' || tag == 'OL') lineTop = null;
    if (s.color != ps.color) css.push('color:' + hex(s.color));
    if (s.fontWeight != ps.fontWeight) css.push('font-weight:' + (+s.fontWeight >= 600 ? 'bold' : 'normal'));
    if (s.fontStyle != ps.fontStyle) css.push('font-style:' + s.fontStyle);
    if (s.fontFamily != ps.fontFamily) css.push('font-family:' + s.fontFamily.replace(/"/g, "'"));
    if (s.fontSize != ps.fontSize) css.push('font-size:' + s.fontSize);
    if (s.textDecorationLine && s.textDecorationLine != 'none') css.push('text-decoration:' + s.textDecorationLine);
    var attr = css.length ? ' style="' + css.join(';') + '"' : '';
    if (tag == 'UL' || tag == 'OL') {
      // its margins, but for a list that is the block itself: its rectangle is inside them
      var m = node === richRoot ? '0' : s.marginTop + ' 0 ' + s.marginBottom;
      return '<' + tag.toLowerCase() + ' style="margin:' + m + ';padding-left:' + s.paddingLeft + (css.length ? ';' + css.join(';') : '') + '">'
        + inner + '</' + tag.toLowerCase() + '>';
    }
    if (tag == 'LI') {
      css.push('margin:' + s.marginTop + ' 0 ' + s.marginBottom, 'padding:' + s.paddingTop + ' 0 ' + s.paddingBottom);
      return '<li style="' + css.join(';') + '">' + inner + '</li>';
    }
    return css.length ? '<span' + attr + '>' + inner + '</span>' : inner;
  }
  var richRoot = null;     // the element of the block of text being written
  var lineTop = null;      // the top of the line being written, to find where the browser wraps
  function rich(el, s, r, f) {
    richRoot = el;
    lineTop = null;
    var w = function (k) { return parseFloat(s[k]) || 0; };
    var x = r[0] + w('borderLeftWidth') + w('paddingLeft'), y = r[1] + w('borderTopWidth') + w('paddingTop');
    var html = [].map.call(el.childNodes, function (c) { return ser(c, s); }).join('').trim()
      .replace(/^(<br>\s*)+|(\s*<br>)+$/g, '');
    if (LIST[el.tagName]) html = ser(el, getComputedStyle(el.parentNode));
    var lh = lineHeight(s);
    var h = r[3] - (LIST[el.tagName] ? 0 : w('borderTopWidth') + w('paddingTop') + w('borderBottomWidth') + w('paddingBottom'));
    if (s.display == 'table-cell' && s.verticalAlign != 'top' && s.verticalAlign != 'baseline') {
      // a cell centers its text (or puts it at the bottom): the block is the height of its lines, where they are
      var rg = document.createRange(); rg.selectNodeContents(el);
      var used = Math.max(1, Math.round(rg.getBoundingClientRect().height / lh)) * lh;
      y += s.verticalAlign == 'bottom' ? h - used : (h - used) / 2;
      h = used;
    }
    add(el, Object.assign({kind: 'rich', html: html, lh: lh, align: s.textAlign,
      r: [LIST[el.tagName] ? r[0] : x, LIST[el.tagName] ? r[1] : y,
          r[2] - (LIST[el.tagName] ? 0 : w('borderLeftWidth') + w('paddingLeft') + w('borderRightWidth') + w('paddingRight')), h]}, f));
  }
  // the text of an edit box, a line feed where the browser wraps it: a copy of the same width and font
  // (the long ed2k links are broken anywhere, which draw.io would not do)
  function wrapped(el, s) {
    var d = document.createElement('div');
    ['fontFamily', 'fontSize', 'fontWeight', 'lineHeight', 'letterSpacing', 'wordBreak', 'overflowWrap', 'tabSize'].forEach(function (k) { d.style[k] = s[k]; });
    d.style.cssText += ';position:absolute;left:0;top:0;visibility:hidden;white-space:pre-wrap;padding:0;border:0;'
      + 'width:' + (el.clientWidth - parseFloat(s.paddingLeft) - parseFloat(s.paddingRight)) + 'px';
    d.textContent = el.value;
    document.body.appendChild(d);
    var text = lines(d.firstChild).map(function (l) { return l.text; }).join('\n');
    d.remove();
    return text;
  }
  function visit(el) {
    var tag = el.tagName;
    if (tag == 'STYLE' || tag == 'SCRIPT' || !shown(el)) return;
    var s = getComputedStyle(el), r = R(el.getBoundingClientRect()), f = font(el);
    if (tag.toLowerCase() == 'svg') {     // an icon outside a button (the help): a picture, in its color
      add(el, {kind: 'svg', r: r, svg: new XMLSerializer().serializeToString(el).replace(/currentColor/g, f.color || '#000000')});
      return;
    }
    if (tag == 'INPUT' && el.type == 'hidden') return;
    if (tag == 'INPUT' && (el.type == 'checkbox' || el.type == 'radio')) {
      add(el, Object.assign({kind: el.type, r: r, on: el.checked, mixed: el.indeterminate, off: el.disabled}, f));
      return;
    }
    if (tag == 'INPUT' || tag == 'TEXTAREA') {
      add(el, Object.assign({kind: 'field', r: r, multi: tag == 'TEXTAREA', lh: lineHeight(s),
                             text: el.type == 'password' ? el.value.replace(/./g, '•') : tag == 'TEXTAREA' ? wrapped(el, s) : el.value},
                            f, frame(s)));
      return;
    }
    if (tag == 'SELECT') {
      var o = el.options[el.selectedIndex];
      add(el, Object.assign({kind: 'select', r: r, text: o ? o.text : '',
                             options: [].map.call(el.options, function (x) { return x.text; })}, f, frame(s)));
      return;
    }
    if (tag == 'BUTTON') {
      // its icons apart, where the browser draws them (centered): in the label, draw.io would put them
      // on the baseline of the text
      var icons = [].map.call(el.querySelectorAll('svg'), function (g) {
        return {r: R(g.getBoundingClientRect()),
                svg: new XMLSerializer().serializeToString(g).replace(/currentColor/g, font(g).color || '#000000')};
      });
      var copy = el.cloneNode(true);
      [].forEach.call(copy.querySelectorAll('svg'), function (g) { g.remove(); });
      add(el, Object.assign({kind: 'button', r: r, html: copy.innerHTML.replace(/\s+/g, ' ').trim(), icons: icons,
                             off: el.disabled}, f, frame(s)));
      return;
    }
    var sides = ['Top', 'Right', 'Bottom', 'Left'].map(function (k) {
      var w = parseFloat(s['border' + k + 'Width']);
      return (w > 0 && s['border' + k + 'Style'] != 'none') ? [w, hex(s['border' + k + 'Color'])] : null;
    });
    if (tag == 'LI' && s.listStyleType != 'none') {
      add(el, Object.assign({kind: 'text', r: [r[0] - 12, r[1], 8, f.fs * 1.4], text: '•', lines: 1}, f));
    }
    var bg = hex(s.backgroundColor);
    if (tag == 'TR') bg = null;     // the cells carry the background of the rows
    if (bg || sides.some(Boolean)) {
      add(el, {kind: 'box', r: r, bg: bg, sides: sides, rad: parseFloat(s.borderTopLeftRadius),
               shadow: s.boxShadow != 'none', opacity: parseFloat(s.opacity)});
    }
    if (textBlock(el)) {
      rich(el, s, r, f);
      return;
    }
    for (var c = el.firstChild; c; c = c.nextSibling) {
      if (c.nodeType == 3) {
        var txt = c.textContent.replace(/\s+/g, ' ').trim();
        if (!txt) continue;
        var rg = document.createRange();
        rg.selectNodeContents(c);
        var rr = rg.getBoundingClientRect();
        if (rr.width < 1) continue;
        if (rg.getClientRects().length < 2) {
          add(el, Object.assign({kind: 'text', r: R(rr), text: txt, lines: 1}, f));
        }
        else {
          lines(c).forEach(function (l) { add(el, Object.assign({kind: 'text', r: l.r, text: l.text, lines: 1}, f)); });
        }
      }
      else if (c.nodeType == 1) visit(c);
    }
  }
  roots.forEach(function (sel) { document.querySelectorAll(sel).forEach(visit); });
  return {items: out, groups: names};
};
"""


# ---- draw.io XML ---------------------------------------------------------------------------

class Page:
    def __init__(self, name, title, note):
        self.name, self.title, self.note = name, title, note
        self.cells = []         # XML of the cells
        self.n = 0
        self.size = [0, 0]

    def id(self):
        self.n += 1
        return f'c{self.n}'

    def cell(self, style, x, y, w, h, label='', parent='1', data=None, vertex=True):
        cid = self.id()
        geometry = f'<mxGeometry x="{x:.1f}" y="{y:.1f}" width="{max(w, 1):.1f}" height="{max(h, 1):.1f}" as="geometry" />'
        kind = 'vertex="1"' if vertex else ''
        if parent in ('1', 'ref'):
            self.size = [max(self.size[0], x + w), max(self.size[1], y + h)]
        attrs = ''.join(f' {k}="{html.escape(str(v), quote=True)}"' for k, v in (data or {}).items() if v not in (None, ''))
        self.cells.append(f'<UserObject label="{html.escape(label, quote=True)}"{attrs} id="{cid}">'
                          f'<mxCell style="{style}" {kind} parent="{parent}">{geometry}</mxCell></UserObject>')
        return cid

    def edge(self, style, x1, y1, x2, y2, parent='1', data=None):
        """A line from (x1, y1) to (x2, y2), connected to no shape."""
        cid = self.id()
        attrs = ''.join(f' {k}="{html.escape(str(v), quote=True)}"' for k, v in (data or {}).items() if v not in (None, ''))
        self.cells.append(f'<UserObject label=""{attrs} id="{cid}"><mxCell style="{style}" edge="1" parent="{parent}">'
                          f'<mxGeometry relative="1" as="geometry"><mxPoint x="{x1:.1f}" y="{y1:.1f}" as="sourcePoint" />'
                          f'<mxPoint x="{x2:.1f}" y="{y2:.1f}" as="targetPoint" /></mxGeometry></mxCell></UserObject>')
        return cid

    def xml(self, index):
        w, h = int(self.size[0] + 60), int(self.size[1] + 60)
        return (f'<diagram id="page{index}" name="{html.escape(self.name, quote=True)}">'
                f'<mxGraphModel grid="1" gridSize="10" guides="1" tooltips="1" connect="0" arrows="0" fold="1" page="1"'
                f' pageScale="1" pageWidth="{w}" pageHeight="{h}" math="0" shadow="0"><root>'
                '<mxCell id="0" />'
                '<mxCell id="ref" value="Reference (screenshot)" style="locked=1;" parent="0" visible="0" />'
                '<mxCell id="1" value="Mockup" parent="0" />'
                '<mxCell id="vguides" value="Vertical guides" parent="0" />'
                '<mxCell id="hguides" value="Horizontal guides" parent="0" />'
                + ''.join(self.cells) + '</root></mxGraphModel></diagram>')


def style(**kv):
    """A draw.io style: True writes the key alone (text, ellipse), None leaves it out."""
    return ''.join(f'{k};' if v is True else f'{k}={v};' for k, v in kv.items() if v is not None)


def font_style(it):
    return (1 if it.get('bold') else 0) + (2 if it.get('italic') else 0) + (4 if it.get('under') else 0)


def text_style(it, **more):
    kv = dict(text=True, html=1, strokeColor='none', fillColor='none', align='left', verticalAlign='top',
              spacing=0, spacingTop=-DRAWIO_TOP, spacingLeft=0, spacingRight=0, overflow='visible',
              whiteSpace='wrap' if it.get('lines', 1) > 1 else 'nowrap',
              fontSize=round(it['fs'], 1), fontColor=it.get('color') or '#000000',
              fontFamily=(it.get('ff') or 'Helvetica'), fontStyle=font_style(it))
    kv.update(more)
    return style(**kv)


def control_frame(it, fill='#ffffff', stroke='#767676', radius=3):
    """A control drawn as the browser does: its own colors, or those of the system ones."""
    if it.get('native') or not (it.get('bg') or it.get('bc')):
        return dict(fillColor=fill, strokeColor=stroke, strokeWidth=1, rounded=1, absoluteArcSize=1, arcSize=radius * 2)
    return dict(fillColor=it.get('bg') or 'none', strokeColor=it.get('bc') if it.get('bw') else 'none',
                strokeWidth=it.get('bw') or 1, rounded=1 if it.get('rad') else 0, absoluteArcSize=1, arcSize=(it.get('rad') or 0) * 2)


def add_item(page, it, x, y, parent):
    w, h = it['r'][2], it['r'][3]
    data = {'mk': it['mk'], 'tooltip': it.get('title')}
    kind = it['kind']
    if kind == 'box':
        sides = it['sides']
        full = all(sides) and len({tuple(s) for s in sides}) == 1
        page.cell(style(rounded=1 if it['rad'] else 0, absoluteArcSize=1, arcSize=it['rad'] * 2, html=1, whiteSpace='wrap',
                        fillColor=it['bg'] or 'none', strokeColor=sides[0][1] if full else 'none',
                        strokeWidth=sides[0][0] if full else None, shadow=1 if it['shadow'] else None,
                        opacity=round(it['opacity'] * 100) if it['opacity'] < 1 else None),
                  x, y, w, h, parent=parent, data=data)
        if not full:    # the borders drawn one by one: a line on a side (the section titles), a separator
            for side, b in zip(('top', 'right', 'bottom', 'left'), sides):
                if not b:
                    continue
                bw, color = b
                geo = {'top': (x, y, w, bw), 'bottom': (x, y + h - bw, w, bw),
                       'left': (x, y, bw, h), 'right': (x + w - bw, y, bw, h)}[side]
                page.cell(style(fillColor=color or '#000000', strokeColor='none'), *geo, parent=parent,
                          data={'mk': it['mk'] + ' border-' + side})
    elif kind == 'text':
        # the rectangle of a text node is its content area: a line of that height centers the text as the browser does
        page.cell(text_style(it), x, y, w + (4 if it.get('lines', 1) > 1 else 2), h,
                  f'<div style="line-height:{h:.1f}px">{html.escape(it["text"])}</div>', parent, data)
    elif kind == 'rich':
        # one shape for a block of text: its HTML (bold, code, links, bullets), its line height kept
        lines = max(1, round(h / it['lh']))
        label = f'<div style="line-height:{it["lh"]:.1f}px">{it["html"]}</div>'     # draw.io would take 1.2
        align = {'right': 'right', 'end': 'right', '-webkit-right': 'right', 'center': 'center',
                 '-webkit-center': 'center'}.get(it['align'], 'left')     # as the browser computes text-align
        # the lines end where the browser ends them (<br>): 4 px wider, so that draw.io wraps none of them
        # sooner, on the side away from its alignment
        more = 4
        page.cell(text_style(dict(it, lines=lines), align=align),
                  x - {'left': 0, 'center': more / 2, 'right': more}[align], y, w + more, h, label, parent, data)
    elif kind == 'button':
        page.cell(style(html=1, whiteSpace='nowrap', fontSize=round(it['fs'], 1), fontColor=it.get('color') or '#000000',
                        fontFamily=it.get('ff') or 'Helvetica', fontStyle=font_style(it), textOpacity=40 if it['off'] else None,
                        spacing=0, **control_frame(it, fill='#efefef')),
                  x, y, w, h, it['html'], parent, data)
        for icon in it.get('icons') or []:      # at the same place relative to the button as in the browser
            svg = base64.b64encode(icon['svg'].encode('utf-8')).decode('ascii')
            page.cell(style(shape='image', imageAspect=0, image='data:image/svg+xml,' + svg, opacity=40 if it['off'] else None),
                      x + icon['r'][0] - it['r'][0], y + icon['r'][1] - it['r'][1], icon['r'][2], icon['r'][3],
                      parent=parent, data={'mk': it['mk'] + ' icon'})
    elif kind in ('checkbox', 'radio'):
        on = it['on'] or it['mixed']
        mark = '–' if it['mixed'] else ('✓' if it['on'] else '')
        if kind == 'checkbox':
            st = style(rounded=1, absoluteArcSize=1, arcSize=4, html=1, fillColor='#0075ff' if on else '#ffffff',
                       strokeColor='#0075ff' if on else '#767676', fontColor='#ffffff', fontStyle=1,
                       fontSize=round(max(6, h * 0.8), 1), spacing=0, opacity=45 if it['off'] else None)
        else:
            st = style(ellipse=True, html=1, fillColor='#ffffff', strokeColor='#0075ff' if on else '#767676',
                       strokeWidth=1, fontColor='#0075ff', fontSize=round(max(5, h * 0.7), 1), spacing=0,
                       opacity=45 if it['off'] else None)
            mark = '●' if on else ''
        data['state'] = 'mixed' if it['mixed'] else ('checked' if it['on'] else 'unchecked')
        page.cell(st, x, y, w, h, mark, parent, data)
    elif kind == 'select':
        data['options'] = ' | '.join(it['options'])
        page.cell(style(html=1, whiteSpace='nowrap', overflow='hidden', align='left', spacing=0, spacingLeft=round(it['pl'] + SELECT_INSET, 1),
                        spacingRight=20, fontSize=round(it['fs'], 1), fontColor=it.get('color') or '#000000',
                        fontFamily=it.get('ff') or 'Helvetica', **control_frame(it)),
                  x, y, w, h, html.escape(it['text']), parent, data)
        # the arrow of Chrome: a chevron, 8 px from the right edge
        chevron = ('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="6" viewBox="0 0 10 6">'
                   f'<path d="M1 1 L5 5 L9 1" fill="none" stroke="{it.get("color") or "#000000"}" stroke-width="1.6"/></svg>')
        page.cell(style(shape='image', imageAspect=0, image='data:image/svg+xml,' + base64.b64encode(chevron.encode()).decode('ascii')),
                  x + w - 18, y + (h - 6) / 2, 10, 6, parent=parent, data={'mk': it['mk'] + ' arrow'})
    elif kind == 'svg':
        svg = base64.b64encode(it['svg'].encode('utf-8')).decode('ascii')
        page.cell(style(shape='image', imageAspect=0, aspect='fixed', image='data:image/svg+xml,' + svg),
                  x, y, w, h, parent=parent, data=data)
    elif kind == 'field':
        text = html.escape(it['text']).replace('\n', '<br>')
        page.cell(style(html=1, whiteSpace='wrap' if it['multi'] else 'nowrap', overflow='hidden', align='left',
                        verticalAlign='top' if it['multi'] else 'middle', spacing=0, spacingLeft=round(it['pl'], 1),
                        spacingTop=round(it['pt'] - DRAWIO_TOP, 1) if it['multi'] else 0,
                        fontSize=round(it['fs'], 1), fontColor=it.get('color') or '#000000',
                        fontFamily=it.get('ff') or 'Helvetica',
                        **control_frame(it, radius=2)),
                  x, y, w, h, f'<div style="line-height:{it["lh"]:.1f}px;overflow-wrap:break-word">{text}</div>' if it['multi'] else text,
                  parent, data)


def add_page(page, found, shot, area):
    """The items read in the page, moved to ORIGIN, in their groups; the screenshot under them."""
    ox, oy = ORIGIN[0] - area['x'], ORIGIN[1] - area['y']
    page.cell(style(text=True, html=1, strokeColor='none', fillColor='none', align='left', verticalAlign='top',
                    fontSize=16, fontStyle=1, fontColor='#2b5c8a'), ORIGIN[0], 20, 900, 24, html.escape(page.title))
    page.cell(style(text=True, html=1, strokeColor='none', fillColor='none', align='left', verticalAlign='top',
                    fontSize=11, fontColor='#666666', whiteSpace='wrap'),
              ORIGIN[0], 46, 1300, 30, html.escape(f'Generated from the real script ({VERSION}, language {LANGUAGE}, theme {THEME}) on {datetime.date.today()} by'
                                                   ' mockups/drawio_export.py. Layers: Mockup (editable), Vertical guides, Horizontal guides,'
                                                   ' Reference (screenshot, hidden and locked).'))
    page.cell(style(shape='image', imageAspect=0, aspect='fixed', image='data:image/png,' + shot),
              ORIGIN[0], ORIGIN[1], area['width'], area['height'], parent='ref', data={'mk': 'screenshot'})
    # each group is made where its first element comes, so that the shapes keep the stacking order of
    # the page (the background of the popup under its toolbars, not over them)
    groups = {}
    for it in found['items']:
        g = it['g']
        if g and g not in groups:
            rects = [i['r'] for i in found['items'] if i['g'] == g]
            x0, y0 = min(r[0] for r in rects), min(r[1] for r in rects)
            x1, y1 = max(r[0] + r[2] for r in rects), max(r[1] + r[3] for r in rects)
            groups[g] = (page.cell('group;', x0 + ox, y0 + oy, x1 - x0, y1 - y0, data={'mk': 'group ' + found['groups'][g]}),
                         x0, y0)
        if g:
            gid, gx, gy = groups[g]
            add_item(page, it, it['r'][0] - gx, it['r'][1] - gy, gid)
        else:
            add_item(page, it, it['r'][0] + ox, it['r'][1] + oy, '1')
    if page.note:
        page.cell(style(shape='note', html=1, whiteSpace='wrap', align='left', verticalAlign='top', spacing=10, size=14,
                        fillColor='#fff2cc', strokeColor='#d6b656', fontSize=12),
                  ORIGIN[0] + area['width'] + 60, ORIGIN[1], 360, 40 + 17 * (page.note.count('<br>') + 2),
                  page.note, data={'mk': 'note'})


def add_guides(page, guides, area):
    """Dashed lines across the whole mockup, in the layer "Vertical guides" or "Horizontal guides": one
    per edge read in the page, colored after its group, the name of the group in its data."""
    ox, oy = ORIGIN[0] - area['x'], ORIGIN[1] - area['y']
    for name, color, vertical, pos in guides:
        st = style(endArrow='none', startArrow='none', html=1, dashed=1, dashPattern='4 3', strokeColor=color, strokeWidth=1)
        if vertical:
            page.edge(st, pos + ox, ORIGIN[1] - 12, pos + ox, ORIGIN[1] + area['height'] + 12,
                      parent='vguides', data={'mk': 'guide ' + name})
        else:
            page.edge(st, ORIGIN[0] - 12, pos + oy, ORIGIN[0] + area['width'] + 12, pos + oy,
                      parent='hguides', data={'mk': 'guide ' + name})


# the edges read for the guides: (group, color, selector, side); left, right and center give vertical
# lines, top, bottom and middle horizontal ones; a selector that matches nothing is skipped
GUIDES_JS = """(function (specs) {
  var out = [];
  specs.forEach(function (s) {
    document.querySelectorAll(s[2]).forEach(function (el) {
      if (!el.getClientRects().length) return;
      var r = el.getBoundingClientRect(), v = ['left', 'right', 'center'].indexOf(s[3]) >= 0;
      var p = {left: r.left, right: r.right, center: (r.left + r.right) / 2,
               top: r.top, bottom: r.bottom, middle: (r.top + r.bottom) / 2}[s[3]];
      if (!out.some(function (o) { return o[0] == s[0] && o[2] == v && Math.abs(o[3] - p) < 0.5; })) out.push([s[0], s[1], v, p]);
    });
  });
  return out;
})"""


def capture(t, cdp, roots, groups, page, guides=None):
    t.js(WALKER)
    found = t.js(f'__mk({json.dumps(roots)}, {json.dumps(groups)})')
    rects = [it['r'] for it in found['items']]
    x0, y0 = min(r[0] for r in rects), min(r[1] for r in rects)
    area = {'x': x0, 'y': y0, 'width': max(r[0] + r[2] for r in rects) - x0, 'height': max(r[1] + r[3] for r in rects) - y0}
    shot = cdp.call('Page.captureScreenshot', {'format': 'png', 'clip': dict(area, scale=1)})['data']
    add_page(page, found, shot, area)
    lines = t.js(f'{GUIDES_JS}({json.dumps(guides or [])})')
    add_guides(page, lines, area)
    print(f'{page.name}: {len(found["items"])} shapes, {len(found["groups"])} groups, {len(lines)} guides')
    return page


# ---- the scenarios -------------------------------------------------------------------------

POPUP_GROUPS = '#theDiv .toolbar, #divBody table, #emlStatus, .emlMsgBar, .emlHelpBar, .emlHelpRows'
SETTINGS_GROUPS = '.config_var, .srow, .sadd, #GM_config_header, #GM_config_buttons_holder, .footer, .section_header_holder'

# the alignment guides: (group, color, selector, side of the element)
POPUP_GUIDES = [
    ('checkboxes', '#e03131', '#theDiv input[type=checkbox]', 'left'),
    ('counter and file names', '#2f9e44', '#theDiv .emlCount', 'left'),
    ('counter and file names', '#2f9e44', '#divBody td a', 'left'),
    ('server and category lists', '#f08c00', '#theDiv select', 'left'),
    ('Download', '#1971c2', '#theDiv .emlAdd', 'right'),
    ('right edge', '#9c36b5', '#theDiv .emlClose, #theDiv #emlClose, #divBody td:last-child', 'right'),
    ('toolbar controls, top and bottom', '#1971c2', '#theDiv .toolbar button, #theDiv .toolbar select', 'top'),
    ('toolbar controls, top and bottom', '#1971c2', '#theDiv .toolbar button, #theDiv .toolbar select', 'bottom'),
    ('middle of the toolbars', '#e03131', '#theDiv .toolbar input[type=checkbox]', 'middle'),
    ('edges of the list', '#9c36b5', '#divBody, #theDiv textarea', 'top'),
    ('edges of the list', '#9c36b5', '#divBody, #theDiv textarea', 'bottom'),
    ('rows of the list', '#2f9e44', '#divBody tr', 'top'),
]
BOX_GUIDES = [      # the message of the closed popup, the help
    ('text', '#2f9e44', '#emlMsg .emlMsgTitle, #emlHelp .emlHelpTitle, #emlHelp .emlHelpRows td:first-child', 'left'),
    ('second column', '#f08c00', '#emlHelp .emlHelpRows td:nth-child(2)', 'left'),
    ('buttons', '#1971c2', '#emlMsgOk, #emlHelpOk', 'right'),
    ('title bar and bottom bar', '#9c36b5', '#emlMsg .emlMsgTitle, #emlHelp .emlHelpTitle', 'bottom'),
    ('title bar and bottom bar', '#9c36b5', '#emlMsg .emlMsgBar.bottom, #emlHelp .emlHelpBar.bottom', 'top'),
    ('middle of the bars', '#e03131', '#emlMsgOk, #emlHelpOk, #emlMsgClose, #emlHelpClose', 'middle'),
]
SETTINGS_GUIDES = [
    ('labels', '#2f9e44', '#GM_config .field_label', 'left'),
    ('fields', '#f08c00', '#GM_config .config_var input[type=text], #GM_config .config_var select', 'left'),
    ('server rows', '#e03131', '#GM_config .srow input[type=radio]', 'left'),
    ('buttons, right edge', '#1971c2', '#GM_config_saveBtn, #GM_config .srow .acts', 'right'),
    ('section titles', '#9c36b5', '#GM_config .section_header', 'top'),
    ('section titles', '#9c36b5', '#GM_config .section_header', 'bottom'),
    ('middle of the fields', '#f08c00', '#GM_config .config_var input[type=text], #GM_config .config_var select, '
     '#GM_config .config_var input[type=checkbox]', 'middle'),
    ('middle of the server rows', '#e03131', '#GM_config .srow input[type=radio]', 'middle'),
]


def popup_page(t, cdp, name, title, note, setup=None, roots=('#theDiv',), guides=POPUP_GUIDES):
    t.load(settings=SETTINGS, servers=ts.SPEC_SERVERS, debug=0)
    if setup:
        setup(t)
    # no selection (the edit box selects its text), the test page hidden: the screenshot shows the screens only
    t.js("(function(){var a=document.activeElement; if (a && a.setSelectionRange) a.setSelectionRange(0, 0);"
         " if (a && a.blur) a.blur(); window.getSelection().removeAllRanges();})()")
    t.js(f"""(function (roots) {{
      [].forEach.call(document.body.children, function (c) {{
        if (!roots.some(function (r) {{ var e = document.querySelector(r); return e && (c === e || c.contains(e)); }})) c.style.visibility = 'hidden';
      }});
    }})({json.dumps(list(roots))})""")
    t.pump(0.3)
    return capture(t, cdp, list(roots), POPUP_GROUPS, Page(name, title, note), guides)


def built_page(t, cdp, name, title, note, markup, groups, after=None):
    """A screen that does not exist yet, built in a page without links as a starting point."""
    t.load('__nolinks', settings=SETTINGS, debug=0)
    t.js(f"(function(){{var d=document.createElement('div'); d.id='mkbuilt'; d.innerHTML={json.dumps(markup)};"
         " document.body.appendChild(d);})()")
    if after:
        t.js(after)
    t.pump(0.3)
    return capture(t, cdp, ['#mkbuilt > *'], groups, Page(name, title, note))


def settings_page(t, cdp, name, title, note, helps):
    ts.open_dialog(t, folded=(), language=LANGUAGE, theme=THEME)     # every section unfolded, every field to edit
    if helps:
        t.click('#GM_config_helpBtn')
    t.pump(0.3)
    return capture(t, cdp, ['#GM_config'], SETTINGS_GROUPS, Page(name, title, note), SETTINGS_GUIDES)


def main():
    os.makedirs(OUT, exist_ok=True)
    server, base, chrome, cdp = run_tests.start_session()
    pages = []
    try:
        cdp.call('Emulation.setScrollbarsHidden', {'hidden': True})
        t = run_tests.T(cdp, base, chrome)
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1470, 'height': 1100, 'deviceScaleFactor': 1, 'mobile': False})
        pages.append(popup_page(t, cdp, '1 Maximized', f'1 — Popup maximized (normal mode), as in {VERSION}',
                                'Two servers: the server list is shown (SF-6.11). The eMule collection is left unchecked'
                                ' by the filter of the settings (SF-5.7), so the boxes of the toolbars are mixed.'
                                '<br><br>For 0.15: Export button (I-11).'))
        pages.append(popup_page(t, cdp, '2 Edit mode', f'2 — Popup in edit mode, as in {VERSION}', None,
                                lambda t: t.edit_mode()))
        pages.append(popup_page(t, cdp, '3 Minimized', f'3 — Popup minimized, as in {VERSION}',
                                'Only the top toolbar (SF-2.12).', lambda t: t.click('#emlMin')))
        pages.append(popup_page(t, cdp, '4 Answer', f'4 — Answer of the client over the list, as in {VERSION}',
                                'A success, in green (SF-7.10). A warning is orange, an error red: their colors are in'
                                ' the PARAM block, with the other colors of the popup (themes, SF-13).',
                                lambda t: t.js("STATUS_DELAY = 600000; showStatus('8 link(s) added to aMule', true)")))
        pages.append(popup_page(t, cdp, '5 Closed message', f'5 — Message when the popup is closed, as in {VERSION}',
                                'Shown on Close (SF-10.4), centered on a backdrop (not drawn here).',
                                lambda t: t.click('#emlClose'), roots=('#emlMsg',), guides=BOX_GUIDES))
        pages.append(popup_page(t, cdp, '6 Help', f'6 — Help, beside the popup, as in {VERSION}',
                                'The ? button, Ctrl+Alt+H or the menu (SF-11).',
                                lambda t: t.click('#emlHelpBtn'), roots=('#theDiv', '#emlHelp'),
                                guides=POPUP_GUIDES + BOX_GUIDES))
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': 1470, 'height': 2600, 'deviceScaleFactor': 1, 'mobile': False})
        pages.append(settings_page(t, cdp, '7 Settings', f'7 — Settings dialog, as in {VERSION} (two servers)',
                                   'The General section holds the theme (SF-13) and the size (SF-2.5) of the'
                                   ' screens of the script.', False))
        pages.append(settings_page(t, cdp, '8 Settings (help shown)', '8 — Settings dialog, every help shown', None, True))
        if t.errors:
            sys.exit(f'JavaScript errors: {t.errors}')
    finally:
        print('temporary profile removed:', run_tests.stop_session(server, chrome, cdp))
    with open(GENERATED, 'w', encoding='utf-8', newline='\n') as f:
        f.write('<mxfile host="drawio_export.py" version="24.0.0">'
                + ''.join(p.xml(i + 1) for i, p in enumerate(pages)) + '</mxfile>\n')
    print('written', GENERATED, f'({os.path.getsize(GENERATED) // 1024} KB)')
    if os.path.exists(FILE):
        print('kept', FILE, '(already there: it may hold edits)')
    else:
        shutil.copyfile(GENERATED, FILE)
        print('written', FILE, '(the file to edit)')


if __name__ == '__main__':
    main()
