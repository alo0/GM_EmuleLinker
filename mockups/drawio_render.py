"""Draw the pages of a draw.io file with draw.io itself, to compare a mockup with the real screens.

    python mockups/drawio_render.py <file.drawio> <folder for the pictures> [--zoom 3] [--page 1] [--clip x,y,w,h]
    python mockups/drawio_render.py mockups/wip/emulelinker_<version>_en_light.drawio mockups/wip/render --zoom 3

--clip draws only that part of the pages (in pixels of the drawing at zoom 1), to look at a detail.

draw.io is the copy embedded in the draw.io extension of VS Code (hediet.vscode-drawio): its viewer
(viewer-static.min.js) draws each page in headless Chrome, as the editor does. For each page, three
pictures: <n>_mockup.png (the layer Mockup and the guides), <n>_reference.png (the screenshot of
the real screen, alone) and <n>_overlay.png (the mockup over the screenshot at 50 %: a gap between
them shows as a double outline). Nothing in the repository is changed.
"""
import base64
import glob
import json
import os
import pathlib
import sys
import time
import xml.etree.ElementTree as ET

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(ROOT, 'tests'))
import run_tests  # noqa: E402

SOURCE, OUT = sys.argv[1:3]
OPTIONS = dict(zip(sys.argv[3::2], sys.argv[4::2]))
ZOOM = float(OPTIONS.get('--zoom', 1))
PAGES = {int(OPTIONS['--page'])} if '--page' in OPTIONS else None
CLIP = [float(v) for v in OPTIONS['--clip'].split(',')] if '--clip' in OPTIONS else None
VIEWERS = sorted(glob.glob(os.path.join(os.path.expanduser('~'), '.vscode', 'extensions', 'hediet.vscode-drawio-*',
                                        'drawio', 'src', 'main', 'webapp', 'js', 'viewer-static.min.js')))
if not VIEWERS:
    sys.exit('draw.io not found: the extension hediet.vscode-drawio of VS Code is needed')
VIEWER = pathlib.Path(VIEWERS[-1]).as_uri()


def page_xml(diagram, mode):
    """The XML of a page, its layers shown or hidden as the mode asks: mockup, reference or overlay."""
    d = ET.fromstring(ET.tostring(diagram))
    for cell in d.iter('mxCell'):
        if cell.get('parent') == '0':
            layer = cell.get('id')
            show = {'mockup': layer != 'ref', 'reference': layer == 'ref', 'overlay': True}[mode]
            cell.set('visible', '1' if show else '0')
    model = d.find('mxGraphModel')
    if mode == 'overlay':
        # the screenshot over the mockup, at 50 %: the white background of the popup would hide it
        root = model.find('root')
        for node in list(root):
            cell = node if node.tag == 'mxCell' else node.find('mxCell')
            if node.get('id') == 'ref' or (cell is not None and cell.get('parent') == 'ref'):
                root.remove(node)
                root.append(node)
                if cell is not None and cell.get('parent') == 'ref':
                    cell.set('style', cell.get('style') + 'opacity=50;')
    return ET.tostring(model, encoding='unicode')


def main():
    os.makedirs(OUT, exist_ok=True)
    diagrams = list(ET.parse(SOURCE).getroot().iter('diagram'))
    chrome = run_tests.Chrome()     # without the script of the tests: it would run in the page of draw.io
    cdp = chrome.page()
    try:
        cdp.call('Page.enable')
        cdp.call('Runtime.enable')
        cdp.call('Emulation.setScrollbarsHidden', {'hidden': True})
        cdp.call('Emulation.setDeviceMetricsOverride', {'width': int(2200 * ZOOM), 'height': int(3000 * ZOOM), 'deviceScaleFactor': 1, 'mobile': False})
        page = os.path.join(os.path.abspath(OUT), '_render.html')
        for n, diagram in enumerate(diagrams, 1):
            if PAGES and n not in PAGES:
                continue
            for mode in ('mockup', 'reference', 'overlay'):
                config = {'xml': page_xml(diagram, mode), 'toolbar': '', 'nav': False, 'resize': False,
                          'zoom': ZOOM, 'border': 0, 'lightbox': False}
                with open(page, 'w', encoding='utf-8') as f:
                    f.write('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body style="margin:0;background:#fff">'
                            f'<div class="mxgraph" data-mxgraph="{json.dumps(config).replace("&", "&amp;").replace(chr(34), "&quot;")}"></div>'
                            f'<script src="{VIEWER}"></script></body></html>')
                cdp.navigate(pathlib.Path(page).as_uri())
                for _ in range(100):
                    if cdp.js("!!document.querySelector('.mxgraph svg') && document.images.length == [].filter.call(document.images, function (i) { return i.complete; }).length"):
                        break
                    time.sleep(0.1)
                time.sleep(0.5)
                r = cdp.js("(function(){var s=document.querySelector('.mxgraph svg').getBoundingClientRect();"
                           "return {x: s.left, y: s.top, width: Math.ceil(s.width), height: Math.ceil(s.height)};})()")
                if CLIP:
                    r = {'x': r['x'] + CLIP[0] * ZOOM, 'y': r['y'] + CLIP[1] * ZOOM, 'width': CLIP[2] * ZOOM, 'height': CLIP[3] * ZOOM}
                shot = cdp.call('Page.captureScreenshot', {'format': 'png', 'clip': dict(r, scale=1)})['data']
                path = os.path.join(OUT, f'{n}_{mode}.png')
                with open(path, 'wb') as f:
                    f.write(base64.b64decode(shot))
            print('written', n, diagram.get('name'))
        os.remove(page)
    finally:
        cdp.close()
        chrome.close()


if __name__ == '__main__':
    main()
