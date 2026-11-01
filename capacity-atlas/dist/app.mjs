import {LAYERS,clone,fixture,valid,blockers,metrics,change,validateSession} from './model.mjs';
const $=id=>document.getElementById(id),NS='http://www.w3.org/2000/svg',STORAGE='wtp-capacity-atlas-v1';
let session={version:1,core:fixture(),baseline:null,history:[]},selected='A',view='all';
const min=x=>`${x} min`;
function msg(text){$('message').textContent=text;}
function event(action,core){if(session.history.length>=200)throw Error('History limit reached. Export this session, then load a fresh example.');valid(core);session.core=clone(core);session.history.push({at:new Date().toISOString(),action,core:clone(core)});render();}
function attempt(action,fn){try{fn();msg(action);}catch(e){msg(e.message);}}
function el(tag,attrs={},text){const n=document.createElementNS(NS,tag);for(const [key,value] of Object.entries(attrs))n.setAttribute(key,String(value));if(text!==undefined)n.textContent=text;return n;}
function draw(){
 const svg=$('map');svg.replaceChildren();
 const defs=el('defs');const pattern=el('pattern',{id:'dots',width:24,height:24,patternUnits:'userSpaceOnUse'});pattern.append(el('circle',{cx:1,cy:1,r:.6,fill:'#4a635d',opacity:.28}));defs.append(pattern);
 const marker=el('marker',{id:'arrow',markerWidth:6,markerHeight:6,refX:5,refY:3,orient:'auto'});marker.append(el('path',{d:'M 0 0 L 6 3 L 0 6',fill:'#5d7d80'}));defs.append(marker);svg.append(defs,el('rect',{width:760,height:440,fill:'url(#dots)'}));
 const nodes=session.core.nodes,focus=nodes.find(n=>n.id===selected);
 const connected=new Set([selected,...focus.deps,...nodes.filter(n=>n.deps.includes(selected)).map(n=>n.id)]);
 for(const node of nodes)for(const dep of node.deps){
  const a=LAYERS[dep],b=LAYERS[node.id],dx=b.x-a.x,dy=b.y-a.y,len=Math.hypot(dx,dy),x1=a.x+dx/len*46,y1=a.y+dy/len*46,x2=b.x-dx/len*49,y2=b.y-dy/len*49;
  const complete=nodes.find(n=>n.id===dep).status==='completed';const opacity=view==='focus'&&(!connected.has(dep)||!connected.has(node.id))?.14:view==='constraints'&&complete?.2:1;
  svg.append(el('path',{d:`M ${x1} ${y1} Q ${(x1+x2)/2} ${Math.min(y1,y2)-15} ${x2} ${y2}`,class:'edge'+(complete?' ready':''),'marker-end':'url(#arrow)',opacity}));
 }
 for(const node of nodes){
  const pos=LAYERS[node.id],ratio=node.estimate?node.worked/node.estimate:node.status==='completed'?1:0;
  const hidden=view==='focus'&&!connected.has(node.id)||view==='constraints'&&node.status==='completed';
  const g=el('g',{transform:`translate(${pos.x},${pos.y})`,class:`node ${node.status} ${selected===node.id?'selected':''}`,role:'button',tabindex:0,'aria-label':`${node.id} ${pos.full}, ${node.status}, ${node.estimate-node.worked} minutes remaining`,'aria-pressed':selected===node.id,opacity:hidden?.25:1});
  g.append(el('circle',{class:'outer',r:43}),el('circle',{class:'ring',r:48,'stroke-dasharray':`${ratio*301.6} 301.6`,opacity:ratio?1:0}),el('text',{class:'letter','text-anchor':'middle',y:9},node.id),el('text',{'text-anchor':'middle',y:72},pos.name),el('text',{class:'status','text-anchor':'middle',y:91},`${node.status} · ${node.estimate-node.worked}m`));
  g.addEventListener('click',()=>select(node.id));g.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();select(node.id);}});svg.append(g);
 }
}
function select(id){selected=id;render();}
function render(){
 const core=session.core,n=core.nodes.find(n=>n.id===selected),m=metrics(core),b=blockers(core,selected),layer=LAYERS[selected];
 for(const key of ['session','breaks','interruptions','recovery']){$(key).value=core.settings[key];$(key+'-value').value=key==='interruptions'?core.settings[key]:min(core.settings[key]);}
 $('usable').textContent=min(m.usable);$('demand').textContent=min(m.demand);$('remaining').textContent=min(m.remaining);$('margin').textContent=(m.margin>0?'+':'')+min(m.margin);$('margin-label').textContent=m.margin<0?'Planning shortfall':'Planning margin';document.querySelector('.margin-stat').classList.toggle('shortfall',m.margin<0);$('recovery-total').textContent=min(m.reserved);
 $('layer-chip').textContent=selected;$('layer-name').textContent=layer.name;$('layer-full').textContent=layer.full;$('task-title').value=n.title;$('estimate').value=n.estimate;$('worked').value=n.worked;$('task-state').textContent=n.status.toUpperCase();
 $('dependencies').replaceChildren();for(const id of Object.keys(LAYERS).filter(id=>id!==selected)){const label=document.createElement('label');label.className='dependency';const checkbox=document.createElement('input');checkbox.type='checkbox';checkbox.value=id;checkbox.checked=n.deps.includes(id);label.append(checkbox,document.createTextNode(`${id} · ${LAYERS[id].name}`));$('dependencies').append(label);}
 $('blockers').textContent=b.length?`Waiting on ${b.map(id=>id+' '+LAYERS[id].name).join(', ')}.`:n.status==='blocked'?'Manually blocked. Unblock when ready.':'Prerequisites are complete or none are required.';
 const actions={queued:['start','block'],active:['pause','block','complete'],paused:['resume','block'],blocked:['unblock'],completed:['reopen']}[n.status];
 $('state-actions').replaceChildren();for(const action of actions){const button=document.createElement('button');button.textContent=action[0].toUpperCase()+action.slice(1);button.disabled=(['start','resume'].includes(action)&&(b.length>0||core.nodes.some(x=>x.id!==selected&&x.status==='active')||(m.remaining<=0&&n.worked<n.estimate)))||(action==='complete'&&n.worked!==n.estimate);button.addEventListener('click',()=>attempt(`${selected}: ${action} recorded.`,()=>event(`${selected} ${action}`,change(core,selected,action))));$('state-actions').append(button);}
 $('work-form').querySelector('button').disabled=n.status!=='active'||n.worked===n.estimate||m.remaining<=0;
 $('task-strip').replaceChildren();for(const node of core.nodes){const button=document.createElement('button');button.textContent=node.id+' · '+node.status;button.setAttribute('aria-pressed',String(node.id===selected));button.setAttribute('aria-label',`Select ${node.id} ${LAYERS[node.id].full}`);button.addEventListener('click',()=>select(node.id));$('task-strip').append(button);}
 const blocked=core.nodes.filter(x=>x.status!=='completed'&&blockers(core,x.id).length);
 $('map-status').textContent=`${core.nodes.filter(x=>x.status==='completed').length} of 5 complete · ${blocked.length} waiting on prerequisites`;
 $('insight').textContent=m.margin<0?`The plan asks for ${-m.margin} more minutes than remain. Reduce scope, revise the session, or change your interruption assumptions.`:m.remaining<0?`Recorded work exceeds usable time by ${-m.remaining} minutes. Revise your time assumptions before adding work.`:`There are ${m.margin} unallocated minutes in this plan. ${blocked.length?`Start upstream: ${core.nodes.filter(x=>x.status==='queued'&&!blockers(core,x.id).length).map(x=>x.id+' '+LAYERS[x.id].name).join(', ')||'inspect blocked work'}.`:'Review completed work and capture what changed.'}`;
 if(session.baseline){const base=metrics(session.baseline);$('comparison').textContent=`Versus baseline: usable time ${signed(m.usable-base.usable)} min · remaining work ${signed(m.demand-base.demand)} min · planning margin ${signed(m.margin-base.margin)} min. Descriptive differences only.`;$('baseline').textContent='Replace baseline';}else{$('comparison').textContent='No baseline yet. Your current session is the starting point.';$('baseline').textContent='Set baseline';}
 $('history').replaceChildren();if(!session.history.length)$('history').textContent='Your first edit starts the revision trail.';
 session.history.map((e,index)=>({e,index})).reverse().forEach(({e,index})=>{const row=document.createElement('div');row.className='event';const time=document.createElement('time');time.textContent=String(index+1).padStart(2,'0');time.dateTime=e.at;const label=document.createElement('span');label.textContent=e.action;const button=document.createElement('button');button.textContent='Restore';button.setAttribute('aria-label',`Restore snapshot ${index+1}: ${e.action}`);button.addEventListener('click',()=>attempt(`Restored snapshot ${index+1} into new history.`,()=>event(`Restored snapshot ${index+1}`,e.core)));row.append(time,label,button);$('history').append(row);});
 for(const button of document.querySelectorAll('[data-view]'))button.setAttribute('aria-pressed',String(view===button.dataset.view));
 draw();
}
function signed(n){return n>0?'+'+n:String(n);}
$('budget-form').addEventListener('submit',e=>{e.preventDefault();attempt('Session assumptions updated.',()=>{const s=Object.fromEntries(['session','breaks','interruptions','recovery'].map(k=>[k,Number($(k).value)]));event('Session inputs edited',change(session.core,selected,'settings',s));});});
for(const key of ['session','breaks','interruptions','recovery'])$(key).addEventListener('input',()=>{$(key+'-value').value=key==='interruptions'?$(key).value:min($(key).value);});
$('task-form').addEventListener('submit',e=>{e.preventDefault();attempt(`${selected} edits saved. Dependencies rechecked.`,()=>event(`${selected} node edited`,change(session.core,selected,'edit',{title:$('task-title').value,estimate:Number($('estimate').value),worked:Number($('worked').value),deps:[...$('dependencies').querySelectorAll('input:checked')].map(x=>x.value)})));});
$('work-form').addEventListener('submit',e=>{e.preventDefault();attempt('Focused work recorded.',()=>event(`${selected} recorded ${$('work-minutes').value} minutes`,change(session.core,selected,'work',{minutes:Number($('work-minutes').value)})));});
for(const button of document.querySelectorAll('[data-view]'))button.addEventListener('click',()=>{view=button.dataset.view;render();});
$('baseline').addEventListener('click',()=>{if(session.baseline&&!confirm('Replace the frozen baseline with this session?'))return;attempt('Baseline frozen. Future edits will be compared with this snapshot.',()=>{if(session.history.length>=200)throw Error('Export and start a new session before adding history.');session.baseline=clone(session.core);event('Baseline frozen',session.core);});});
$('load-preset').addEventListener('click',()=>{if(session.history.length&&!confirm('Start a fresh example? Export or save the current session first. Current history and baseline will be replaced.'))return;session={version:1,core:fixture($('preset').value),baseline:null,history:[]};selected='A';view='all';event('Example loaded',session.core);msg('New fictional example loaded. Saved browser data is unchanged until you save.');});
$('save-local').addEventListener('click',()=>attempt('Saved in this browser only. No data was sent to the project repository.',()=>localStorage.setItem(STORAGE,JSON.stringify(session))));
$('export').addEventListener('click',()=>{const blob=new Blob([JSON.stringify(session,null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='capacity-atlas-session.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);msg('Session exported. Review entered text before sharing.');});
$('import').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;try{if(file.size>2000000)throw Error('Session file exceeds 2 MB');const imported=validateSession(JSON.parse(await file.text()));if(!confirm('Replace this session with the imported record? Export current work first.'))return;session=imported;selected='A';view='all';render();msg('Session imported. Imported history is unverified user data.');}catch(error){msg(error.message);}finally{e.target.value='';}});
$('about-button').addEventListener('click',()=>$('about').showModal());$('close-about').addEventListener('click',()=>$('about').close());
try{const saved=localStorage.getItem(STORAGE);if(saved){session=validateSession(JSON.parse(saved));msg('Loaded your saved browser session.');}}catch{msg('Saved session could not be read. A fresh example is shown.');}
render();
