const PIXEL_COLORS = ['teal', 'mauve', 'indigo', 'olive'];
function pixelGrowth(count) {
  const known=Number.isSafeInteger(count) && count>=0;
  return !known ? {stage:'unknown',scale:.7,count:null,label:'Merged PR history unknown'} :
    count<=5 ? {stage:'seedling',scale:.4,count,label:count+' merged PRs · seedling'} :
    count<=20 ? {stage:'growing',scale:.7,count,label:count+' merged PRs · growing'} :
    {stage:'mature',scale:1,count,label:count+' merged PRs · mature'};
}
function pixelGrowthTransform(count) {
  return `translate(0 -8) scale(${pixelGrowth(count).scale}) translate(0 8)`;
}
function pixelStaleBranches(count, total, layoutScale) {
  return `<g data-marker="stale" class="tree-fx" transform="scale(${layoutScale}) ${pixelGrowthTransform(count)}">
    <path class="jin pixel-jin" d="M-4 -29h-5v-4h-4v-5h-3M-9 -33h-7"/>
    ${total>1?'<path class="jin pixel-jin" d="M0 -43h6v-5h5v-4M6 -48v-7"/>':''}</g>`;
}
function pixelFamilyTree(palette, count=null) {
  const growth=pixelGrowth(count);
  const color = palette.mid === BONSAI_GOLD.mid ? 'gold' :
    PIXEL_COLORS[BONSAI_FOLIAGE.findIndex(p => p.mid === palette.mid)] || 'teal';
  const leaf = (x,y,w,h) => `<use href="#pixel-foliage" x="${x-w/2}" y="${y-h/2}" width="${w}" height="${h}" filter="url(#pixel-${color})"/>`;
  const pads = [[0,-67,24,14],[7,-60,21,12],[-8,-55,24,13],[11,-46,25,14],[-14,-44,24,13],[-24,-34,25,14],[23,-35,25,14],[-10,-24,17,10]];
  const canopy = pads.map(([x,y,w,h])=>leaf(x,y,w,h)+`<ellipse cx="${x}" cy="${y}" rx="${w*.4}" ry="${h*.35}" fill="transparent"/>`).join('');
  return `<g data-pixel-family="moyogi" data-pixel-color="${color}" data-growth="${growth.stage}" data-merged-prs="${growth.count ?? 'unknown'}" style="image-rendering:pixelated">
    <title>${growth.label}.</title>
    <rect class="tree-bounds" x="-40" y="-85" width="80" height="110" fill="none"/>
    <g data-growth-body transform="${pixelGrowthTransform(count)}">
      <ellipse class="tree-hit" cx="0" cy="-52" rx="8" ry="32" fill="transparent"/>
      <use href="#pixel-trunk" x="-27" y="-70" width="54" height="66"/>${canopy}
    </g>
    <ellipse cx="0" cy="-4" rx="17" ry="4" fill="transparent"/>
    <use href="#pixel-pot" x="-22" y="-10" width="44" height="15"/>
    ${growth.stage==='unknown'?'<text x="26" y="-12" fill="#ded8ca" font-size="10">?</text>':''}</g>`;
}

function pixelFamilyForPath(path) {
  const repo=repoByPath.get(path), project=projectForPath(path);
  const identity=project?.mainRepoPath || repoIdentities.get(path)?.project_path || repo?._status?.project_path || path;
  return BONSAI_STYLES[bonsaiSeed(identity)%BONSAI_STYLES.length]==='moyogi';
}
function mergedPrGrowthInfo(repo) {
  const snapshot=githubSnapshotForRepo(repo), record=snapshot?.mergedGrowth;
  const count=record?.count ?? null;
  return {count, checkedAt:record?.checkedAt || null,
    stale:count!==null && (!snapshot?.mergedGrowthCurrent || !!snapshot?.info?.merged_pr_error || !githubSnapshotFresh(snapshot) || snapshot?.transportFailed),
    stage:pixelGrowth(count).stage};
}
function mergedPrGrowthLine(repo) {
  const growth=mergedPrGrowthInfo(repo);
  const text=growth.count===null?'Merged PR total unknown':growth.count+' merged PRs · '+(growth.stale?'last known total':'project total');
  return `<p class="merged-pr-growth" data-growth="${growth.stage}">${escapeHtml(text)}${growth.checkedAt?'<br>'+checkedTime(growth.checkedAt,'Total checked'):''}</p>`;
}
