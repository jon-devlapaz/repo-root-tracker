/* Preview renderer: one informal-upright family, with independent history inputs. */
const PIXEL_COLORS = ['teal', 'mauve', 'indigo', 'olive'];
function pixelFamilyTree(palette, vit) {
  const color = palette.mid === BONSAI_GOLD.mid ? 'gold' :
    PIXEL_COLORS[BONSAI_FOLIAGE.findIndex(p => p.mid === palette.mid)] || 'teal';
  const leaf = (x,y,w,h) => `<use href="#pixel-foliage" x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" filter="url(#pixel-${color})"/>`;
  const pads = [[0,-67,24,14],[7,-60,21,12],[-8,-55,24,13],[11,-46,25,14],[-14,-44,24,13],[-24,-34,25,14],[23,-35,25,14],[-10,-24,17,10]];
  const canopy = pads.map(([x,y,w,h])=>leaf(x*vit.girth/1.22,y,w*vit.density,h*vit.density)).join('');
  const limbs = Array.from({length:vit.br}, (_,i)=>{
    const y=-19-i*9, side=i%2 ? 1 : -1, end=side*(17+i*2);
    return `<g data-pixel-limb="${i}"><path d="M6 ${y+5}Q${end*.45} ${y+4} ${end} ${y-3}" fill="none" stroke="#81664c" stroke-width="2" shape-rendering="crispEdges"/>${leaf(end,y-4,10,6)}</g>`;
  }).join('');
  return `<g data-pixel-family="moyogi" data-pixel-color="${color}" data-girth="${vit.girth}" data-density="${vit.density}" data-branches="${vit.br}" style="image-rendering:pixelated">
    <rect class="tree-bounds" x="-40" y="-85" width="80" height="110" fill="none"/>
    ${limbs}<g transform="translate(0 -8) scale(${vit.girth/1.22} 1) translate(0 8)"><use href="#pixel-trunk" x="-27" y="-70" width="54" height="66"/></g>
    <use href="#pixel-pot" x="-22" y="-10" width="44" height="15"/>
    ${canopy}</g>`;
}
function showPixelFamily() {
  let dialog=document.getElementById('pixel-family-review');
  if(dialog){dialog.showModal();return;}
  dialog=document.createElement('dialog');dialog.id='pixel-family-review';
  dialog.style.cssText='width:min(1080px,94vw);max-height:90vh;overflow:auto;background:#161514;color:#ded8ca;border:1px solid #555;padding:24px';
  const specimens=(title,cases)=>`<section><h2>${title}</h2><div style="display:flex;flex-wrap:wrap;gap:16px">`+cases.map(c=>`<figure style="margin:0;width:170px"><svg width="170" height="170" viewBox="-43 -80 86 90">${pixelFamilyTree(c.palette||BONSAI_GOLD,{girth:1.22,density:1,br:0,...c.vit})}</svg><figcaption>${c.label}</figcaption></figure>`).join('')+'</div></section>';
  dialog.innerHTML='<button id="pixel-family-close" style="float:right">Close</button><h1>One pixel bonsai family</h1><p>Artwork trial · synthetic examples. Color, age, activity and branches vary independently.</p>'+ 
    specimens('Checkout colors',[{label:'Clean · gold'},...PIXEL_COLORS.map((color,i)=>({label:'Changed · '+color,palette:BONSAI_FOLIAGE[i]}))])+
    specimens('Age · trunk thickness',[.78,.92,1.08,1.22].map((girth,i)=>({label:['Under 45 days','45–199 days','200–799 days','800+ days'][i],vit:{girth}})))+
    specimens('Recent activity · foliage',[.86,1,1.07].map((density,i)=>({label:['No commits in 30 days','1–6 commits','7+ commits'][i],vit:{density}})))+
    specimens('Other live local branches',[0,1,2,3,4].map(br=>({label:br===4?'4 or more branches':br+' branches',vit:{br}})))+
    '<h2>Small sizes</h2><div style="display:flex;gap:24px;align-items:end">'+[48,80,128].map(w=>`<figure style="margin:0"><svg width="${w}" height="${w*1.15}" viewBox="-40 -85 80 92">${pixelFamilyTree(BONSAI_GOLD,{girth:1.22,density:1,br:1})}</svg><figcaption>${w}px</figcaption></figure>`).join('')+'</div><p>Unknown history uses neutral growth. Unavailable checks retain the last known growth. Git warnings remain separate.</p>';
  document.body.append(dialog);dialog.querySelector('button').onclick=()=>dialog.close();dialog.showModal();
}
window.addEventListener('load',()=>{
  const button=document.createElement('button');button.textContent='Pixel tree states';
  button.style.cssText='position:fixed;right:18px;bottom:18px;z-index:1000;background:#ded8ca;color:#161514;padding:10px 16px;border-radius:6px';
  button.onclick=showPixelFamily;document.body.append(button);
  if(new URLSearchParams(location.search).has('family'))showPixelFamily();
});
