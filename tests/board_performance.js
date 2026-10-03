/* Reference gate: measure production callbacks, including deferred ground work. */
(()=>{window.runBoardReferenceSample=async function(run) {
  await document.fonts.ready;
  const probe=window.boardWorkProbe={currentId:null,depth:0,updates:new Map(),components:{},nextId:0};
  const originals=new Map();
  const names=['render','renderBoard','renderBoardView','rebuildProjectModel','boardProjectAggregate','renderIsometricScene',
    'applyBoardCamera','layoutBoardNames','cacheBoardMemberHits','applyReplay','boardGroundFor','groundChunk','finishBoardGround',
    'requestLocalStatus','applyLocalStatus','finishLocalStatus','rememberRepoMetadata',
    // deferred work: layoutBoardNames only queues; these are the real label placement and the batched tile patches
    'runLayoutBoardNames','patchBoardTile'];
  for(const name of names){
    const original=window[name];originals.set(name,original);
    window[name]=function(...args){
      const start=performance.now(),root=probe.depth++===0;
      const id=['groundChunk','finishBoardGround'].includes(name)?args[0].originUpdateId:probe.currentId;
      try{return original.apply(this,args);}
      finally{
        const elapsed=performance.now()-start;probe.depth--;
        probe.components[name]=(probe.components[name]||0)+elapsed;
        if(root && id && probe.updates.has(id))probe.updates.get(id).work+=elapsed;
      }
    };
  }
  const taskEntries=[];
  const observer=new PerformanceObserver(list=>taskEntries.push(...list.getEntries().map(e=>({start:e.startTime,duration:e.duration}))));
  observer.observe({type:'longtask',buffered:false});
  const frame=()=>new Promise(resolve=>requestAnimationFrame(resolve));
  const paint=async()=>{await frame();await frame();};
  const stage=document.getElementById('board-stage');
  const cameraPositions=new Set();let measuredPromotions=0;
  const actions={
    pan:i=>{boardCamera.x+=i%2?7:-7;boardCamera.y+=i%2?3:-3;boardFitPending=false;applyBoardCamera();cameraPositions.add(boardCamera.x+','+boardCamera.y);},
    zoom:i=>zoomBoardAt(i%2?1.025:1/1.025,stage.clientWidth/2,stage.clientHeight/2),
    replay:i=>scrubReplay(30-i%30),
    promotion:i=>{const project=boardScene.plots[i%25].project;
      const path=project.worktreePaths.find(path=>!boardScene.targets.some(t=>t.path===path));
      if(!path)throw Error('Performance promotion requires an overflow checkout');
      selectBoardRepo(path);document.getElementById('board-tile-'+encodeURIComponent(path)).focus({preventScroll:true});
      measuredPromotions++;},
  };
  boardNamesVisible=true;boardReplay.open=true;
  boardReplay.data={repos:Object.fromEntries(repos.map((r,i)=>[r.path,{[replayKey(i%4)]:i%6+1}]))};
  syncReplayControls();
  renderBoard();
  zoomBoardAt(1.8/boardCamera.zoom,stage.clientWidth/2,stage.clientHeight/2);
  locateBoardPlot(boardScene.plots[0].project.defaultPath);
  // Exactly 120 warm-up animation frames; none enter the retained samples.
  for(let i=0;i<120;i++){actions[i===119?'promotion':['pan','zoom','replay'][i%3]](i);await frame();}
  await new Promise(resolve=>setTimeout(resolve,300));
  while(groundCache.pendingSig || refreshingLocal || refreshingBoard)await frame();
  probe.components={};taskEntries.length=0;cameraPositions.clear();measuredPromotions=0;
  const started=performance.now();let refreshStart=null,refreshEnd=null,refreshPromise=null;
  const originalFetch=window.fetch;
  let requests=0,active=0,peak=0,backgroundRequests=0,measuringRefresh=false;
  window.fetch=(url,...args)=>{
    if(!String(url).startsWith('/api/repos/status?'))return originalFetch(url,...args);
    const path=new URL(url,location.href).searchParams.get('path'),index=repos.findIndex(r=>r.path===path);
    // The regular 15-second poll remains active and contributes to timing.
    // Count only the explicit board refresh in its 360-request contract.
    const measured=measuringRefresh && refreshingBoard;
    if(measured){requests++;active++;peak=Math.max(peak,active);}else backgroundRequests++;
    return new Promise(resolve=>setTimeout(()=>{
      if(measured)active--;const status=structuredClone(repoByPath.get(path)._status);
      status.dirty={is_clean:index%7!==0,modified:index%7===0?2:0};
      status.activity_30d=index%18;status.first_commit_date='2020-01-01';
      resolve({ok:true,status:200,json:async()=>status});
    },20+(index%3)*20));
  };
  const sample=async(category,index)=>{
    const id=++probe.nextId,entry={id,category,work:0,latency:0,start:performance.now()};
    probe.updates.set(id,entry);probe.currentId=id;
    const start=performance.now();probe.depth++;
    try{actions[category](index);}finally{probe.depth--;entry.work+=performance.now()-start;}
    await paint();
    entry.latency=performance.now()-start;
  };
  try{
    for(const category of ['pan','zoom','replay','promotion']){
      const count=category==='promotion'?30:300;
      for(let i=0;i<count;i++){
        if(category==='pan' && i===10){
          while(refreshingLocal || refreshingBoard)await frame();
          refreshStart=performance.now();measuringRefresh=true;
          refreshPromise=fetchBoardAll(false).then(()=>{refreshEnd=performance.now();measuringRefresh=false;});
        }
        await sample(category,i);
      }
    }
    await refreshPromise;
    while(groundCache.pendingSig)await frame();
    await paint();
    const rank=(values,p)=>values.slice().sort((a,b)=>a-b)[Math.max(0,Math.ceil(values.length*p)-1)];
    const stats=values=>({count:values.length,median:rank(values,.5),p95:rank(values,.95),max:Math.max(0,...values)});
    const categories={};
    for(const category of Object.keys(actions)){
      const entries=[...probe.updates.values()].filter(e=>e.category===category);
      categories[category]={work:stats(entries.map(e=>e.work)),paint:stats(entries.map(e=>e.latency))};
    }
    const overlap=[...probe.updates.values()].filter(e=>e.start>=refreshStart && e.start<=refreshEnd);
    categories.refreshGroundOverlap={work:stats(overlap.map(e=>e.work)),paint:stats(overlap.map(e=>e.latency))};
    observer.takeRecords().forEach(e=>taskEntries.push({start:e.startTime,duration:e.duration}));
    const measuredTasks=taskEntries.filter(e=>e.start+e.duration>=started && e.start<performance.now());
    return {run,categories,components:probe.components,taskObserver:'PerformanceObserver longtask (reports tasks >=50ms)',
      longestObservedTaskMs:Math.max(0,...measuredTasks.map(e=>e.duration)),tasks:measuredTasks,
      refresh:{requests,peak,backgroundRequests,ms:refreshEnd-refreshStart},plots:boardScene.plots.length,targets:boardScene.targets.length,
      measuredPromotions,panCameraPositions:cameraPositions.size,
      groundTotalWorkMs:groundCache.workMs,elapsed:performance.now()-started};
  }finally{
    observer.disconnect();window.fetch=originalFetch;
    for(const [name,original]of originals)window[name]=original;
    window.boardWorkProbe=null;
  }
};return true;})();
