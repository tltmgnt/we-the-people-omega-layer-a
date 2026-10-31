'use strict';
let state = {projects: [], sources: [], token: ''}, selected = '009';
const $ = id => document.getElementById(id);
function el(tag, text, cls) { const n = document.createElement(tag); if (text !== undefined) n.textContent = text; if (cls) n.className = cls; return n; }
function input(label, value, multiline = false) { const wrap = el('label', label), n = el(multiline ? 'textarea' : 'input'); n.value = value || ''; wrap.append(n); return [wrap, n]; }
function actor() { const value = $('actor').value.trim(); if (!value) throw new Error('Enter your name or identifier before recording changes.'); return value; }
async function request(path, body) { const response = await fetch(path, body === undefined ? {} : {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Portfolio-Token': state.token}, body: JSON.stringify(body)}); const data = await response.json(); if (!response.ok) throw new Error(data.error || 'Request failed'); return data; }
function action(label, fn) { const b = el('button', label); b.type = 'button'; b.onclick = async () => { b.disabled = true; $('message').textContent = ''; try { await fn(); } catch(e) { $('message').textContent = e.message; } finally { b.disabled = false; } }; return b; }
async function refresh() { state = await request('/api/bootstrap'); render(); }
function safeLink(url, title) { const n = el('a', title || url); try { const u = new URL(url); if (['https:', 'http:'].includes(u.protocol)) { n.href = u.href; n.target = '_blank'; n.rel = 'noopener noreferrer'; } } catch {} return n; }
function render() {
  const complete = state.projects.filter(p => !p.blockers.length).length, imported = state.sources.filter(s => s.revision).length;
  $('summary').replaceChildren(...[[50, 'Registered projects'], [state.projects.filter(p => !p.title).length, 'Definitions unresolved'], [imported, 'Sources imported'], [complete, 'Complete as recorded']].map(([v,l]) => { const n = el('div', undefined, 'stat'); n.append(el('strong', String(v)), el('span', l)); return n; }));
  const query = $('search').value.toLowerCase(), status = $('filter').value;
  const projects = state.projects.filter(p => `${p.project_id} ${p.title || ''}`.toLowerCase().includes(query) && (!status || p.status === status));
  $('projects').replaceChildren(...projects.map(p => { const b = action(`${p.project_id} · ${p.title || 'Title to confirm'}`, async () => { selected = p.project_id; render(); }); b.classList.toggle('selected', p.project_id === selected); b.append(el('small', `${p.status.replaceAll('_', ' ')} · ${p.completed_steps}/${p.total_steps} steps`)); return b; }));
  if (!projects.length) $('projects').append(el('p', 'No matching projects.'));
  renderDetail();
  $('sources').replaceChildren(...state.sources.map(sourcePanel));
}
function renderDetail() {
  const p = state.projects.find(p => p.project_id === selected), root = $('detail'); root.replaceChildren(); if (!p) return;
  root.append(el('p', `PROJECT ${p.project_id} · ${p.status.replaceAll('_', ' ')}`, 'meta'), el('h2', p.title || 'Project definition needed'));
  root.append(el('p', p.plan.basis, 'notice'), el('h3', 'Proposed outcome'), el('p', p.plan.outcome));
  const list = el('ul'); p.blockers.forEach(b => list.append(el('li', b))); root.append(el('h3', 'Open requirements'), list);
  const form = el('form'), [tl, title] = input('Confirmed project title', p.title), [ol, owner] = input('Accountable owner', p.owner), [sl, scope] = input('Scope and requirements', p.scope, true);
  const checkWrap = el('div', undefined, 'checks'), checkLabel = el('label', 'Scope checked against the current source'), check = el('input'); check.type = 'checkbox'; check.checked = p.scope_confirmed; checkLabel.prepend(check); checkWrap.append(checkLabel);
  form.append(tl,ol,sl,checkWrap,action('Save definition', async () => { const changed = title.value.trim() !== (p.title || '') || scope.value.trim() !== p.scope; await request(`/api/projects/${p.project_id}`, {version:p.version, actor:actor(), title:title.value, owner:owner.value, scope:scope.value, scope_confirmed:check.checked}); await refresh(); $('message').textContent = changed ? 'Definition saved. Changed requirements reset work evidence; review and confirm the new scope in a separate save.' : 'Definition saved.'; })); form.onsubmit = e => e.preventDefault(); root.append(el('h3','Project definition'),form);
  root.append(el('h3','Proposed measurement'), el('p',p.plan.metric), el('p',`Input records: ${p.plan.records}`), el('p',`Safeguard: ${p.plan.safeguard}`));
  const steps = el('ol', undefined, 'steps');
  p.plan.steps.forEach(step => { const work = p.tasks[step.id], item = el('li'); item.append(el('strong',step.title),el('p',step.deliverable),el('p',`Acceptance: ${step.acceptance}`)); const [label, evidence] = input('Evidence reference and verification result',work.evidence,true); item.append(label); if (work.done) item.append(el('p',`Recorded by ${work.actor} · ${work.at}`, 'evidence')); item.append(action(work.done ? 'Reopen step' : 'Record step complete',async()=>{await request(`/api/projects/${p.project_id}`,{version:p.version,actor:actor(),task:{id:step.id,done:!work.done,evidence:evidence.value}});await refresh();})); steps.append(item); });
  root.append(el('h3','Implementation and acceptance'), steps,el('h3','Project source'),sourcePanel(p.source));
}
function sourcePanel(s) {
  const d = el('details',undefined,'source-row'); d.append(el('summary',`${s.id} · ${s.revision ? `v${s.revision} · ${s.reviewer ? 'review recorded' : 'needs review'}` : 'not imported'}`));
  if (s.url) d.append(safeLink(s.url,'Open registered source')); else d.append(el('p','No registered source URL. Supply a documented origin with your export.'));
  if (s.revision) { d.append(el('p',`SHA-256: ${s.sha256}`, 'evidence')); const pre = el('pre','Source content is not loaded.'); d.append(action('Read current source',async()=>{const data=await request(`/api/sources/${s.id}`);pre.textContent=data.content;}),pre,action('Record current source review',async()=>{await request(`/api/sources/${s.id}/review`,{revision:s.revision,actor:actor()});await refresh();})); }
  const [ol,origin]=input('Origin (document URL, export filename, or supplied source identity)',s.url || ''), [cl,content]=input('Full source text', '',true); const file = el('input'); file.type='file'; file.accept='.txt,.md,.json,text/plain,text/markdown,application/json'; file.setAttribute('aria-label',`Load text export for ${s.id}`); file.onchange=async()=>{try { if (file.files[0].size>4000000) throw new Error('Source exceeds 4 MB.');content.value=await file.files[0].text();if(!origin.value)origin.value=file.files[0].name;}catch(e){$('message').textContent=e.message;}};
  d.append(ol,file,cl,action('Import source version',async()=>{await request(`/api/sources/${s.id}/import`,{actor:actor(),origin:origin.value,content:content.value});await refresh();$('message').textContent='Source imported. Review the new version before reconfirming scope and work.';}));return d;
}
$('search').addEventListener('input',render);$('filter').addEventListener('change',render);
refresh().catch(e=>$('message').textContent=`Unable to load workspace: ${e.message}`);
