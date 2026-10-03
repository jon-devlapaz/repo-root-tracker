"""One-tree artwork trial. Production rendering stays unchanged."""
import base64
from pathlib import Path

ASSET = Path(__file__).parent / 'fixtures/bonsai-pixel/gold.png'
TARGET = '/review/team-00/cedar'


def pixel_dashboard(source):
    anchor = 'function buildBonsaiTree(path, palette, ink = false) {'
    if source.count(anchor) != 1:
        raise ValueError('Expected one bonsai renderer')
    uri = 'data:image/png;base64,' + base64.b64encode(ASSET.read_bytes()).decode()
    trial = '''
    if (path === '/review/team-00/cedar' && palette.mid === BONSAI_GOLD.mid) {
      return `<rect class="tree-bounds" x="-40" y="-85" width="80" height="110" fill="none"/>
        <image data-pixel-trial="gold" href="SPRITE" x="-39" y="-66" width="78" height="70"
          preserveAspectRatio="xMidYMax meet" style="image-rendering:pixelated"/>`;
    }
    '''.replace('SPRITE', uri)
    return source.replace(anchor, anchor + trial)
