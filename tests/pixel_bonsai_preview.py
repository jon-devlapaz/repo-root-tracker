"""Synthetic gallery overlay for the production pixel renderer."""
from pathlib import Path
ASSETS=Path(__file__).parent/'fixtures/bonsai-pixel'
TARGET='/review/team-00/cedar'
def pixel_dashboard(source):
    anchor='function bonsaiTree(path,palette,ink=false) {'
    gallery=(ASSETS/'family.js').read_text().split('function showPixelFamily()',1)[1]
    overlay="const PIXEL_SAMPLE_MERGES = new Map([['/review/team-00/cedar',12],['/review/team-00/cedar-worktree-1',12]]);\nfunction showPixelFamily()"+gallery
    trial="\nif(path==='/review/team-00/cedar' || path==='/review/team-00/cedar-worktree-1')return pixelFamilyTree(palette,PIXEL_SAMPLE_MERGES.get(path));\n"
    return source.replace(anchor,overlay+'\n'+anchor+trial,1)
