export const LAYERS={A:{name:'Legitimacy',full:'Constitutional Legitimacy',x:120,y:145},B:{name:'Operations',full:'Government Operations',x:350,y:95},C:{name:'Outcomes',full:'Human and Community Outcomes',x:455,y:300},D:{name:'Evidence',full:'Intelligence and Evidence',x:145,y:335},E:{name:'Learning',full:'Transformation and Institutional Learning',x:650,y:200}};
const keys=Object.keys(LAYERS),statuses=['queued','active','paused','blocked','completed'];
export const clone=x=>JSON.parse(JSON.stringify(x));
export function fixture(preset='balanced'){
 const settings={balanced:{session:120,breaks:15,interruptions:2,recovery:5},fragmented:{session:90,breaks:10,interruptions:6,recovery:6},recovery:{session:150,breaks:25,interruptions:1,recovery:5}}[preset];
 if(!settings)throw Error('Unknown example');
 const titles=['Review authority and rights','Map the service handoffs','Interpret access outcomes','Check sources and uncertainty','Plan a controlled improvement'];
 const estimates=[15,25,20,20,15],deps=[[],['A'],['B','D'],[],['C','D']];
 return {settings:clone(settings),nodes:keys.map((id,i)=>({id,title:titles[i],estimate:estimates[i],worked:0,status:'queued',deps:deps[i]}))};
}
export function valid(core){
 if(!core||!core.settings||!Array.isArray(core.nodes)||core.nodes.length!==5)throw Error('A five-layer session is required');
 const s=core.settings;
 for(const [k,max] of [['session',480],['breaks',120],['interruptions',20],['recovery',30]])if(!Number.isInteger(s[k])||s[k]<0||s[k]>max)throw Error('Invalid '+k+' input');
 if(s.session<15)throw Error('Session must be at least 15 minutes');
 const found=new Set();
 for(const n of core.nodes){
  if(!keys.includes(n.id)||found.has(n.id))throw Error('Layer IDs must be unique A–E');found.add(n.id);
  if(typeof n.title!=='string'||!n.title.trim()||n.title.length>100)throw Error('Work item needs 1–100 characters');
  if(!Number.isInteger(n.estimate)||n.estimate<0||n.estimate>480||!Number.isInteger(n.worked)||n.worked<0||n.worked>n.estimate)throw Error('Recorded minutes must be between zero and the estimate');
  if(!statuses.includes(n.status)||!Array.isArray(n.deps)||n.deps.length>4||new Set(n.deps).size!==n.deps.length||n.deps.some(id=>!keys.includes(id)||id===n.id))throw Error('Invalid status or dependencies');
  if(n.status==='completed'&&n.worked!==n.estimate)throw Error('Completed work must account for its estimate');
 }
 if(core.nodes.filter(n=>n.status==='active').length>1)throw Error('Only one work item may be active');
 const visiting=new Set(),visited=new Set();
 function visit(id){if(visiting.has(id))throw Error('Dependency cycle detected; keep the map acyclic');if(visited.has(id))return;visiting.add(id);for(const dep of core.nodes.find(n=>n.id===id).deps)visit(dep);visiting.delete(id);visited.add(id);}keys.forEach(visit);
 for(const n of core.nodes)if(['active','completed'].includes(n.status)&&blockers(core,n.id).length)throw Error('Active or completed work needs completed prerequisites');
 return core;
}
export function blockers(core,id){return core.nodes.find(n=>n.id===id).deps.filter(dep=>core.nodes.find(n=>n.id===dep).status!=='completed');}
export function metrics(core){const s=core.settings;const reserved=s.interruptions*s.recovery;const usable=Math.max(0,s.session-s.breaks-reserved);const spent=core.nodes.reduce((a,n)=>a+n.worked,0);const demand=core.nodes.reduce((a,n)=>a+(n.status==='completed'?0:n.estimate-n.worked),0);return {reserved,usable,spent,demand,remaining:usable-spent,margin:usable-spent-demand};}
function invalidate(core){let changed=true;while(changed){changed=false;for(const n of core.nodes)if(['active','completed'].includes(n.status)&&blockers(core,n.id).length){n.status='blocked';changed=true;}}}
export function change(original,id,action,payload={}){
 const core=clone(original),n=core.nodes.find(x=>x.id===id);if(!n)throw Error('Choose a layer');
 if(action==='settings')core.settings=payload;
 else if(action==='edit'){n.title=payload.title;n.estimate=payload.estimate;n.worked=payload.worked;n.deps=payload.deps;if(n.status==='completed'&&n.worked!==n.estimate)n.status='queued';invalidate(core);}
 else if(action==='work'){
  if(n.status!=='active')throw Error('Start or resume this work item first');
  if(!Number.isInteger(payload.minutes)||payload.minutes<=0)throw Error('Enter positive whole minutes');
  if(payload.minutes>n.estimate-n.worked)throw Error('Minutes exceed the remaining estimate');
  if(payload.minutes>metrics(core).remaining)throw Error('Not enough session time; revise inputs or reduce the work');
  n.worked+=payload.minutes;
 }else{
  const transitions={queued:{start:'active',block:'blocked'},active:{pause:'paused',block:'blocked',complete:'completed'},paused:{resume:'active',block:'blocked'},blocked:{unblock:'queued'},completed:{reopen:'queued'}};
  const next=transitions[n.status]?.[action];if(!next)throw Error('That control is unavailable in this state');
  if(next==='active'){
   if(blockers(core,id).length)throw Error('Complete prerequisites first: '+blockers(core,id).join(', '));
   if(core.nodes.some(x=>x.id!==id&&x.status==='active'))throw Error('Pause the current active item before switching');
   if(metrics(core).remaining<=0&&n.worked<n.estimate)throw Error('No usable session time remains');
  }
  if(next==='completed'&&n.worked!==n.estimate)throw Error('Record remaining work, or revise its estimate, before completing');
  n.status=next;invalidate(core);
 }
 return valid(core);
}
export function validateSession(value){
 if(!value||value.version!==1)throw Error('Unsupported session format');
 valid(value.core);
 if(value.baseline!==null)valid(value.baseline);
 if(!Array.isArray(value.history)||value.history.length>200)throw Error('Invalid history');
 for(const e of value.history){if(typeof e.action!=='string'||e.action.length>200||typeof e.at!=='string'||!Number.isFinite(Date.parse(e.at)))throw Error('Invalid history event');valid(e.core);}
 return {version:1,core:clone(value.core),baseline:value.baseline===null?null:clone(value.baseline),history:clone(value.history)};
}
