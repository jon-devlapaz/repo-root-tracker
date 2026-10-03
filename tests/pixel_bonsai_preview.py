"""Layered artwork trial. Production rendering stays unchanged."""
import base64
from pathlib import Path

ASSETS = Path(__file__).parent / 'fixtures/bonsai-pixel'
TARGET = '/review/team-00/cedar'
COLORS = {
    'gold': ['5a3d05','d4a017','ffd966','fff6c9'],
    'teal': ['0f2926','1f6b64','6fc2b7','c6ece6'],
    'mauve': ['26171f','6e4d60','c19bb2','f0c9d8'],
    'indigo': ['171a3a','50559a','a3a8dd','d6d9ff'],
    'olive': ['25261a','6b7048','b8bd8a','e6e9c8'],
}


def pixel_dashboard(source):
    anchor = 'function bonsaiTree(path,palette,ink=false) {'
    if source.count(anchor) != 1:
        raise ValueError('Expected one bonsai renderer')
    definitions = []
    for name in ['trunk', 'foliage', 'pot']:
        uri = 'data:image/png;base64,' + base64.b64encode((ASSETS / (name+'.png')).read_bytes()).decode()
        definitions.append(f'<symbol id="pixel-{name}" viewBox="0 0 100 100" preserveAspectRatio="none"><image href="{uri}" width="100" height="100" preserveAspectRatio="none"/></symbol>')
    for name, palette in COLORS.items():
        channels = ''.join('<feFunc'+channel+' type="table" tableValues="'+' '.join(str(int(c[offset:offset+2],16)/255) for c in palette)+'"/>' for channel,offset in [('R',0),('G',2),('B',4)])
        definitions.append(f'<filter id="pixel-{name}" color-interpolation-filters="sRGB"><feComponentTransfer>{channels}</feComponentTransfer></filter>')
    definitions = '<svg aria-hidden="true" width="0" height="0" style="position:absolute"><defs>'+''.join(definitions)+'</defs></svg>'
    source=source.replace('<body>', '<body>'+definitions, 1)
    trial = "\n if(path === '/review/team-00/cedar' || path === '/review/team-00/cedar-worktree-1') return pixelFamilyTree(palette, PIXEL_SAMPLE_MERGES.get(path));\n"
    return source.replace(anchor, (ASSETS / 'family.js').read_text()+'\n'+anchor+trial)
