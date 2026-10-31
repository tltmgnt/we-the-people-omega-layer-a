'use strict';
const $=id=>document.getElementById(id);
let state;
const labels={EVIDENCE:'D · Record/revise evidence',EVIDENCE_REVIEW:'D · Check current evidence',STUDY:'C · Define outcome study',OBSERVATION:'C · Record observation',OUTCOME_REVIEW:'C · Check observation',TRIAL:'E · Define rehearsal',TRIAL_EVENT:'E · Control/check rehearsal'};
const choice={confidence:['C','B','A'],kind:['COUNT','PROPORTION'],counter_kind:['COUNT','PROPORTION'],phase:['BASELINE','FOLLOW_UP'],action:['RECORD','CHECK','REOPEN','ROLLBACK'],status:['', 'DESIGNED','BASELINE_RECORDED','REHEARSAL_RECORDED','EVALUATION_RECORDED','LEARNING_RECORDED'],passed:['true','false']};
const numeric=new Set(['expected_revision','revision','version','observation_sequence','target_sequence','primary_numerator','primary_denominator','counter_numerator','counter_denominator']);
const nullable=new Set(['verification_reference','primary_missing','counter_missing','primary_numerator','primary_denominator','counter_numerator','counter_denominator','status','target_sequence','passed']);
const multiline=new Set(['content','corroborating_refs','limitations','definition','exclusions','uncertainty','counter_definition','scope','resources','continuity','rollback']);
const pretty=value=>JSON.stringify(value,null,2);
function options(select,items,value){select.replaceChildren();for(const item of items){const o=document.createElement('option');o.value=typeof item==='string'?item:item.value;o.textContent=typeof item==='string'?(item||'Not applicable'):item.label;select.append(o);}if(value!==undefined&&[...select.options].some(o=>o.value===value))select.value=value;}
async function request(path,body){const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Portfolio-Token':state.token},body:JSON.stringify(body)});const result=await response.json();if(!response.ok)throw Error(result.error||'Request failed');return result;}
function synchronize(){
 const kind=$('record-kind').value;
 const evidence=state.evidence.find(e=>e.evidence_id===($('field-evidence_id')||{}).value);
 const study=state.studies.find(e=>e.study_id===($('field-study_id')||{}).value);
 const trial=state.trials.find(e=>e.trial_id===($('field-trial_id')||{}).value);
 if($('field-expected_revision'))$('field-expected_revision').value=evidence?evidence.current_revision:0;
 if($('field-revision'))$('field-revision').value=evidence?evidence.current_revision:'';
 if($('field-version'))$('field-version').value=(kind==='TRIAL_EVENT'?trial:study)?.version||'';
 if(kind==='TRIAL_EVENT'){
  const action=$('field-action').value;
  for(const name of ['status','target_sequence','passed'])$('field-'+name).disabled=name==='status'?action!=='RECORD':action!=='CHECK';
  if(action==='CHECK'&&trial){const current=[...trial.events].reverse().find(e=>['RECORD','REOPEN','ROLLBACK'].includes(e.action));$('field-target_sequence').value=current?.action==='RECORD'?current.sequence:'';}
 }
}
function drawForm(){
 const kind=$('record-kind').value;$('fields').replaceChildren();
 for(const name of state.schemas[kind].split(' ')){
  let element;
  const target=name==='study_id'&&kind!=='STUDY'?state.studies.map(s=>s.study_id):name==='trial_id'&&kind!=='TRIAL'?state.trials.map(t=>t.trial_id):name==='evidence_id'&&kind==='EVIDENCE_REVIEW'?state.evidence.map(e=>e.evidence_id):null;
  if(name==='pins'||name==='study_ids'){
   element=document.createElement('select');element.multiple=true;element.size=4;
   options(element,name==='pins'?state.evidence.map(e=>({value:JSON.stringify({evidence_id:e.evidence_id,revision:e.current_revision}),label:e.evidence_id+' · revision '+e.current_revision})):state.studies.map(s=>s.study_id));
  }else if(target||choice[name]){element=document.createElement('select');options(element,target||choice[name]);}
  else if(multiline.has(name)){element=document.createElement('textarea');}
  else{element=document.createElement('input');if(numeric.has(name)){element.type='number';element.step='1';element.min='0';}else element.type='text';}
  element.id='field-'+name;element.name=name;
  if(['version','revision','expected_revision'].includes(name))element.readOnly=true;
  if(!nullable.has(name)&&name!=='corroborating_refs')element.required=true;
  if(['evidence_id','study_id','trial_id'].includes(name)&&element.tagName==='INPUT')element.placeholder='SYN-EXAMPLE';
  if(name==='group')element.placeholder='Fictional aggregate cohort';
  if(name.startsWith('window_'))element.placeholder='2026-01-01T00:00:00Z';
  const label=document.createElement('label');label.textContent=name.replaceAll('_',' ');label.append(element);$('fields').append(label);
  element.addEventListener('change',synchronize);if(name==='evidence_id')element.addEventListener('input',synchronize);
 }
 $('form-help').textContent='Blank nullable fields are unknown/not applicable. Counts use no denominator; proportions need a positive denominator. Corroborating references: one per line. Select one or more evidence pins/studies. Enter fictional records only.';
 synchronize();
}
async function reports(){
 const source=state.evidence.find(e=>e.evidence_id===$('evidence-report').value);$('evidence-output').textContent=source?pretty(source):'No evidence recorded.';
 $('study-output').textContent=$('study-report').value?pretty(await request('/api/layers/studies/'+encodeURIComponent($('study-report').value))):'No studies recorded.';
 $('trial-output').textContent=$('trial-report').value?pretty(await request('/api/layers/trials/'+encodeURIComponent($('trial-report').value))):'No trials recorded.';
}
async function refresh(){
 const selected=[$('evidence-report').value,$('study-report').value,$('trial-report').value];
 state=await request('/api/layers');
 options($('evidence-report'),state.evidence.map(e=>e.evidence_id),selected[0]);options($('study-report'),state.studies.map(s=>s.study_id),selected[1]);options($('trial-report'),state.trials.map(t=>t.trial_id),selected[2]);
 drawForm();await reports();
}
$('record-kind').addEventListener('change',drawForm);
for(const id of ['evidence-report','study-report','trial-report'])$(id).addEventListener('change',()=>reports().catch(e=>$('message').textContent=e.message));
$('layer-form').addEventListener('submit',async event=>{
 event.preventDefault();$('save-layer').disabled=true;
 try{
  const kind=$('record-kind').value;const body={actor:$('actor').value,note:$('note').value,at:$('at').value};
  for(const name of state.schemas[kind].split(' ')){
   const field=$('field-'+name);let value=field.value;
   if(field.disabled)value=null;
   else if(name==='pins')value=[...field.selectedOptions].map(o=>JSON.parse(o.value));
   else if(name==='study_ids')value=[...field.selectedOptions].map(o=>o.value);
   else if(name==='corroborating_refs')value=value.split('\n').map(v=>v.trim()).filter(Boolean);
   else if(value===''&&nullable.has(name))value=null;
   else if(numeric.has(name))value=Number(value);
   else if(name==='passed')value=value==='true';
   body[name]=value;
  }
  await request('/api/layers/'+kind,body);await refresh();$('message').textContent='Saved local '+labels[kind]+'. Live execution remains unauthorized.';
 }catch(error){$('message').textContent=error.message;}finally{$('save-layer').disabled=false;}
});
options($('record-kind'),Object.entries(labels).map(([value,label])=>({value,label})));
$('at').value=new Date().toISOString();
refresh().catch(error=>$('message').textContent=error.message);
