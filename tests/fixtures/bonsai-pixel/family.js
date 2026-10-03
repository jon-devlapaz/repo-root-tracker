/* Preview renderer: one informal-upright family, with independent history inputs. */
const PIXEL_COLORS = ['teal', 'mauve', 'indigo', 'olive'];
// These counts are synthetic preview data, never inferred from open PRs or age.
const PIXEL_SAMPLE_MERGES = new Map([['/review/team-00/cedar', 12], ['/review/team-00/cedar-worktree-1', 12]]);
function pixelGrowth(count) {
  const known=Number.isSafeInteger(count) && count>=0;
  return !known ? {stage:'unknown',scale:.7,count:null,label:'Merged PR history unknown'} :
    count<=5 ? {stage:'seedling',scale:.4,count,label:count+' merged PRs · seedling'} :
    count<=20 ? {stage:'growing',scale:.7,count,label:count+' merged PRs · growing'} :
    {stage:'mature',scale:1,count,label:count+' merged PRs · mature'};
}
function pixelFamilyTree(palette, count=null) {
  const growth=pixelGrowth(count);
  const color = palette.mid === BONSAI_GOLD.mid ? 'gold' :
    PIXEL_COLORS[BONSAI_FOLIAGE.findIndex(p => p.mid === palette.mid)] || 'teal';
  const leaf = (x,y,w,h) => `<use href="#pixel-foliage" x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" filter="url(#pixel-${color})"/>`;
  const pads = [[0,-67,24,14],[7,-60,21,12],[-8,-55,24,13],[11,-46,25,14],[-14,-44,24,13],[-24,-34,25,14],[23,-35,25,14],[-10,-24,17,10]];
  const canopy = pads.map(([x,y,w,h])=>leaf(x,y,w,h)).join('');
  return `<g data-pixel-family="moyogi" data-pixel-color="${color}" data-growth="${growth.stage}" data-merged-prs="${growth.count ?? 'unknown'}" style="image-rendering:pixelated">
    <title>${growth.label}. Sample data.</title>
    <rect class="tree-bounds" x="-40" y="-85" width="80" height="110" fill="none"/>
    <g data-growth-body transform="translate(0 -8) scale(${growth.scale}) translate(0 8)">
      <use href="#pixel-trunk" x="-27" y="-70" width="54" height="66"/>${canopy}
    </g>
    <use href="#pixel-pot" x="-22" y="-10" width="44" height="15"/>
    ${growth.stage==='unknown'?'<text x="26" y="-12" fill="#ded8ca" font-size="10">?</text>':''}</g>`;
}
function showPixelFamily() {
  let dialog=document.getElementById('pixel-family-review');
  if(dialog){dialog.showModal();return;}
  dialog=document.createElement('dialog');dialog.id='pixel-family-review';
  dialog.style.cssText='width:min(1080px,94vw);max-height:90vh;overflow:auto;background:#161514;color:#ded8ca;border:1px solid #555;padding:24px';
  const specimens=(title,width)=>`<section><h2>${title}</h2><div style="display:flex;flex-wrap:wrap;gap:24px;align-items:start">`+
    [0,12,30,null].map(count=>`<figure style="margin:0;width:${Math.max(width,140)}px"><svg width="${width}" height="${width*1.15}" viewBox="-40 -85 80 92">${pixelFamilyTree(BONSAI_GOLD,count)}</svg><figcaption>${pixelGrowth(count).label}</figcaption></figure>`).join('')+'</div></section>';
  dialog.innerHTML='<button id="pixel-family-close" style="float:right">Close</button><h1>Growth from merged work</h1><p>Sample counts · proposed bands: 0–5, 6–20, 21+ merged PRs. Size shows merged work, not quality.</p>'+
    specimens('At board size',96)+specimens('Small worktree size',48)+specimens('Closer look',160)+
    '<h2>Color changes without changing growth</h2><div style="display:flex;flex-wrap:wrap;gap:24px">'+[BONSAI_GOLD,...BONSAI_FOLIAGE].map((palette,i)=>`<figure style="margin:0"><svg width="96" height="110" viewBox="-40 -85 80 92">${pixelFamilyTree(palette,12)}</svg><figcaption>${['Clean','Teal','Mauve','Indigo','Olive'][i]} · 12 PRs</figcaption></figure>`).join('')+'</div><p>Age, commit activity and branch count no longer change this family’s size. Inactivity does not shrink it. Unknown history has a question mark and is never counted as zero.</p><p>The board uses a sample total of 12 for cedar and its worktree. Live GitHub totals are not connected yet.</p>';
  document.body.append(dialog);dialog.querySelector('button').onclick=()=>dialog.close();dialog.showModal();
}
window.addEventListener('load',()=>{
  const button=document.createElement('button');button.textContent='Pixel tree states';
  button.style.cssText='position:fixed;right:18px;bottom:18px;z-index:1000;background:#ded8ca;color:#161514;padding:10px 16px;border-radius:6px';
  button.onclick=showPixelFamily;document.body.append(button);
  if(new URLSearchParams(location.search).has('family'))showPixelFamily();
});
