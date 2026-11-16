"""Compare an edited draw.io mockup with the generated one, and draw the pages of the edited one.

    python mockups/drawio_diff.py <generated.drawio> <edited.drawio> [<folder for the pictures>]
    python mockups/drawio_diff.py mockups/wip/emulelinker_<version>_en_light.generated.drawio mockups/wip/emulelinker_<version>_en_light.drawio

For each page: the shapes added, removed, moved or resized (absolute positions), and those whose
text or style changed. With a folder, each page of the edited file is drawn in HTML by headless
Chrome (shapes as boxes, in the stacking order of draw.io: a group with its content), an
approximation to look at the layout, not draw.io itself.
"""
import base64
import html
import os
import re
import sys
import xml.etree.ElementTree as ET


def parse(path):
    pages = {}
    for d in ET.parse(path).getroot().iter('diagram'):
        root = d.find('mxGraphModel/root')
        cells, order = {}, []
        for node in root:
            c = node if node.tag == 'mxCell' else node.find('mxCell')
            cid = node.get('id')
            label = node.get('label') if node.tag in ('UserObject', 'object') else c.get('value')
            data = {k: v for k, v in node.attrib.items() if k not in ('id', 'label')} if node.tag != 'mxCell' else {}
            g = c.find('mxGeometry')
            st = dict((kv.split('=', 1) + [''])[:2] for kv in (c.get('style') or '').split(';') if kv)
            geo = None if g is None else [float(g.get(k, 0)) for k in ('x', 'y', 'width', 'height')]
            cells[cid] = {'parent': c.get('parent'), 'style': st, 'label': label or '', 'geo': geo, 'data': data,
                          'visible': c.get('visible', '1')}
            order.append(cid)
        for cid in order:      # absolute positions
            cell, x, y, p = cells[cid], 0, 0, cells[cid]['parent']
            while p in cells and cells[p]['geo'] is not None:
                x += cells[p]['geo'][0]
                y += cells[p]['geo'][1]
                p = cells[p]['parent']
            if cell['geo']:
                cell['abs'] = [cell['geo'][0] + x, cell['geo'][1] + y, cell['geo'][2], cell['geo'][3]]
        pages[d.get('name')] = (cells, order)
    return pages


def text(label):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', label or ''))).strip()


def name(cell):
    return f"{cell['data'].get('mk', '?')} «{text(cell['label'])[:50]}»"


def fmt(r):
    return '(' + ', '.join(f'{v:.0f}' for v in r) + ')'


def compare(gen, edi):
    for page, (cells, order) in edi.items():
        print(f'\n=== {page}')
        if page not in gen:
            print('  new page')
            base = {}
        else:
            base = gen[page][0]
        for cid in order:
            c = cells[cid]
            if 'abs' not in c or c['style'].get('shape') == 'image':
                continue
            if cid not in base:
                print(f'  + {cid} {name(c)} at {fmt(c["abs"])} style={";".join(f"{k}={v}" for k, v in c["style"].items())}')
                continue
            b = base[cid]
            changes = []
            if any(abs(p - q) > 0.5 for p, q in zip(c['abs'], b['abs'])):
                changes.append(f'{fmt(b["abs"])} -> {fmt(c["abs"])}')
            if text(c['label']) != text(b['label']):
                changes.append(f'text «{text(b["label"])}» -> «{text(c["label"])}»')
            st = {k for k in set(c['style']) | set(b['style']) if c['style'].get(k) != b['style'].get(k)}
            if st:
                changes.append('style ' + ', '.join(f'{k}: {b["style"].get(k)} -> {c["style"].get(k)}' for k in sorted(st)))
            if c['parent'] != b['parent']:
                changes.append(f'parent {b["parent"]} -> {c["parent"]}')
            if changes:
                print(f'  ~ {cid} {name(c)}: ' + ' | '.join(changes))
        for cid, b in base.items():
            if cid not in cells and 'abs' in b and b['style'].get('shape') != 'image':
                print(f'  - {cid} {name(b)} was at {fmt(b["abs"])}')


def draw(edi, out):
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tests'))
    import run_tests
    server, base, chrome, cdp = run_tests.start_session()
    try:
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': 2400, 'height': 2600, 'deviceScaleFactor': 1, 'mobile': False})
        t = run_tests.T(cdp, base, chrome)
        for i, (page, (cells, order)) in enumerate(edi.items()):
            children = {}
            for cid in order:
                children.setdefault(cells[cid]['parent'], []).append(cid)
            divs = []

            def visit(cid):
                c = cells[cid]
                st = c['style']
                if c.get('abs') and st.get('shape') != 'image' and 'group' not in st and c['parent'] != 'ref':
                    divs.append(box(c))
                for k in children.get(cid, []):
                    if cells[k]['parent'] == 'ref' or cells.get(cid, {}).get('visible') == '0':
                        continue
                    visit(k)
            for layer in children.get('0', []):
                if layer != 'ref':
                    visit(layer)
            t.serve(f'/__draw{i}', '<html><body style="margin:0;background:#fff;position:relative">' + ''.join(divs) + '</body></html>')
            t.driver.navigate(base + f'/__draw{i}')
            cdp.pump(0.5)
            t.js("document.querySelectorAll('#GM_config, #GM_config_backdrop, #theDiv').forEach(function(e){e.remove();})")
            size = t.js("(function(){var w=0,h=0;document.querySelectorAll('body > div').forEach(function(e){var r=e.getBoundingClientRect();"
                        "w=Math.max(w,r.right);h=Math.max(h,r.bottom);});return [w,h];})()")
            data = cdp.call('Page.captureScreenshot', {'format': 'png', 'clip': {'x': 0, 'y': 0, 'width': min(size[0] + 10, 2400),
                                                                                 'height': min(size[1] + 10, 2600), 'scale': 1}})['data']
            path = os.path.join(out, f'edited_{i + 1}.png')
            with open(path, 'wb') as f:
                f.write(base64.b64decode(data))
            print('written', path, page)
    finally:
        run_tests.stop_session(server, chrome, cdp)


def box(c):
    st, (x, y, w, h) = c['style'], c['abs']
    css = [f'position:absolute;left:{x}px;top:{y}px;width:{w}px;height:{h}px;box-sizing:border-box;overflow:visible']
    if 'text' not in st and st.get('fillColor', '#ffffff') != 'none':
        css.append(f'background:{st.get("fillColor") or "#ffffff"}')
    if 'text' not in st and st.get('strokeColor', '#000000') != 'none':
        css.append(f'border:{st.get("strokeWidth", 1)}px solid {st.get("strokeColor") or "#000000"}')
    if st.get('rounded') == '1':
        css.append(f'border-radius:{float(st.get("arcSize", 10)) / 2 if st.get("absoluteArcSize") == "1" else 4}px')
    if 'ellipse' in st:
        css.append('border-radius:50%')
    fs = int(st.get('fontStyle', 0) or 0)
    css.append(f'font-size:{st.get("fontSize", 11)}px;color:{st.get("fontColor", "#000")};font-family:{st.get("fontFamily", "Helvetica")}')
    if fs & 1:
        css.append('font-weight:bold')
    if fs & 4:
        css.append('text-decoration:underline')
    css.append(f'white-space:{"nowrap" if st.get("whiteSpace") == "nowrap" else "normal"};line-height:1.2')
    if 'text' in st:
        css.append(f'display:block;text-align:{st.get("align", "left")}')
    else:
        align = {'left': 'flex-start', 'right': 'flex-end'}.get(st.get('align'), 'center')
        valign = {'top': 'flex-start'}.get(st.get('verticalAlign'), 'center')
        css.append(f'display:flex;justify-content:{align};align-items:{valign};padding-left:{st.get("spacingLeft", 0)}px')
    if st.get('opacity'):
        css.append(f'opacity:{int(float(st["opacity"])) / 100}')
    return f'<div style="{";".join(css)}"><span>{c["label"]}</span></div>'


if __name__ == '__main__':
    gen, edi = parse(sys.argv[1]), parse(sys.argv[2])
    compare(gen, edi)
    if len(sys.argv) > 3:
        draw(edi, sys.argv[3])
