"""Embed the pixel family into the standalone dashboard; repeatable without API calls."""
import base64
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'src/repo_root_tracker/artwork'
PAGE=ROOT/'src/repo_root_tracker/dashboard.html'
COLORS={'gold':['5a3d05','d4a017','e5bc56','ead18b'],'teal':['0f2926','1f6b64','65aaa1','86bcb3'],'mauve':['26171f','6e4d60','b28ea4','c6a3b6'],'indigo':['171a3a','50559a','9399c4','adb3d8'],'olive':['25261a','6b7048','a7ad7c','bfc497']}

def replace_block(source,start,end,content,anchor):
    block=start+'\n'+content+'\n'+end
    if start in source:
        a=source.index(start);b=source.index(end,a)+len(end)
        return source[:a]+block+source[b:]
    return source.replace(anchor,anchor+'\n'+block,1)

def build():
    source=PAGE.read_text();definitions=[]
    for name in ['trunk','foliage','pot']:
        uri='data:image/png;base64,'+base64.b64encode((ART/(name+'.png')).read_bytes()).decode()
        definitions.append(f'<symbol id="pixel-{name}" viewBox="0 0 100 100" preserveAspectRatio="none"><image href="{uri}" width="100" height="100" preserveAspectRatio="none"/></symbol>')
    for name,palette in COLORS.items():
        channels=''.join('<feFunc'+channel+' type="table" tableValues="'+' '.join(str(int(c[offset:offset+2],16)/255) for c in palette)+'"/>' for channel,offset in [('R',0),('G',2),('B',4)])
        definitions.append(f'<filter id="pixel-{name}" color-interpolation-filters="sRGB"><feComponentTransfer>{channels}</feComponentTransfer></filter>')
    source=replace_block(source,'<!-- pixel artwork start -->','<!-- pixel artwork end -->','<svg aria-hidden="true" width="0" height="0" style="position:absolute"><defs>'+''.join(definitions)+'</defs></svg>','<body>')
    source=replace_block(source,'/* pixel family start */','/* pixel family end */',(ART/'pixel-family.js').read_text(),'const bonsaiTreeMarkup=new Map();')
    PAGE.write_text(source)

if __name__=='__main__':
    build()
