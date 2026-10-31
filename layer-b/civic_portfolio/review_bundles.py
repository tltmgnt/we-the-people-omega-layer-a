"""Selected scenario review bundles. Never exports the entire workspace implicitly."""
import io
import hashlib
import json
import zipfile
from .maintenance import fields,identifier
from .scenarios import catalog,bounded
from .scenario_comparisons import ScenarioComparisons
from .store import ROOT,text,now
from scripts.verify_review_bundle import FORMAT,MAX_TOTAL,MAX_FILE,MAX_FILES,verify_bytes

def encoded(value):
    return (json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n').encode('utf-8')

class ReviewBundles:
    def __init__(self,store):self.store=store

    def build(self,data):
        fields(data,'bundle_id selections comparison_ids actor note')
        bundle_id=identifier(data['bundle_id']);actor=text(data['actor'],'bundle actor',200);note=text(data['note'],'bundle purpose and sharing limitations')
        selections=data['selections'];comparisons=data['comparison_ids']
        if not isinstance(selections,list) or len(selections)>100:raise ValueError('at most 100 selected snapshots')
        if not isinstance(comparisons,list) or len(comparisons)>20 or any(not isinstance(c,str) for c in comparisons):raise ValueError('at most 20 comparison IDs')
        if not selections and not comparisons:raise ValueError('select at least one snapshot or comparison')
        comparison_ids=[identifier(c) for c in comparisons]
        if len(set(comparison_ids))!=len(comparison_ids):raise ValueError('duplicate comparison ID')
        queue=[];requested=[]
        for selection in selections:
            fields(selection,'run_id sequence')
            key=identifier(selection['run_id']);seq=bounded(selection['sequence'],'selected sequence',1,10000)
            if (key,seq) in requested:raise ValueError('duplicate selected snapshot')
            requested.append((key,seq));queue.append((key,seq,None))
        files={};total=0
        def add(name,content):
            nonlocal total
            if len(content)>MAX_FILE or total+len(content)>MAX_TOTAL or len(files)>=MAX_FILES-1:raise ValueError('selected review scope exceeds archive limit')
            files[name]=content;total+=len(content)
        with self.store.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            comparison_reader=ScenarioComparisons(self.store)
            comparison_files=[]
            for key in comparison_ids:
                item=comparison_reader.report(key,db)
                if not item['historical_result_intact']:raise ValueError('comparison source integrity is unavailable; bundle rejected')
                name='comparisons/'+key+'.json';add(name,encoded(item));comparison_files.append(name)
                for side in ('baseline','alternative'):
                    pin=item[side];queue.append((pin['run_id'],pin['sequence'],pin['state_sha256']))
            collected={};snapshot_files=[];definitions=set();cursor=0
            while cursor<len(queue):
                key,seq,expected=queue[cursor];cursor+=1
                if (key,seq) in collected:
                    if expected and collected[(key,seq)]['state_sha256']!=expected:raise ValueError('conflicting snapshot dependency')
                    continue
                if len(collected)>=200:raise ValueError('too many transitive snapshots')
                pin,state=comparison_reader.snapshot(key,seq,db)
                if expected and pin['state_sha256']!=expected:raise ValueError('referenced snapshot hash mismatch')
                event=json.loads(db.execute('SELECT body FROM scenario_events WHERE run_id=? AND sequence=?',(key,seq)).fetchone()['body'])
                envelope=dict(run_id=key,sequence=seq,workflow=pin['workflow'],state_sha256=pin['state_sha256'],
                              source_current_at_export=pin['current_at_creation'],event=event)
                name='snapshots/'+key+'/'+str(seq)+'.json';add(name,encoded(envelope))
                collected[(key,seq)]=envelope;snapshot_files.append(name);definitions.add(pin['workflow'])
                for attachment in state.get('attachments',{}).values():
                    source=identifier(attachment['source_run_id']);source_seq=bounded(attachment['source_sequence'],'dependency sequence',1,10000)
                    queue.append((source,source_seq,attachment['state_sha256']))
            configs=catalog()
            for workflow in sorted(definitions):add('definitions/'+workflow+'.json',encoded(configs[workflow]))
            built_at=now()
            boundary=dict(kind='SYNTHETIC',execution_authorized=False,layer_a_status='LEGAL_REVIEW_REQUIRED',institutional_acceptance='NOT_ESTABLISHED',
                          definition_blocked=[f'{i:03}' for i in range(1,7)],signature='NOT_SIGNED',
                          notice='Fictional scenario snapshots and supplied measurements; checksums do not establish source truth, qualified review, real outcomes or authority.')
            add('boundary.json',encoded(boundary))
            add('architecture/five-layer-summary.json',(ROOT/'portfolio/five-layer-architecture.json').read_bytes())
            index=dict(bundle_id=bundle_id,built_at=built_at,actor=actor,note=note,
                       requested_snapshots=[dict(run_id=k,sequence=s) for k,s in requested],requested_comparisons=comparison_ids,
                       snapshot_files=sorted(snapshot_files),comparison_files=sorted(comparison_files),definition_files=['definitions/'+w+'.json' for w in sorted(definitions)],
                       scope='Selected snapshots/comparisons plus recursively referenced scenario evidence. No unrelated runs, source documents, full database or workspace audit log.')
            add('index.json',encoded(index))
            readme=('SYNTHETIC REVIEW BUNDLE\n\nSelected scope is listed in index.json. Source actor notes and measurements are included; review before sharing.\n'
                    'Referenced scenario snapshots are included transitively so comparison/capstone pins can be checked. Current-at-export flags are local assertions at build time, not live status.\n'
                    'No full source-document imports or unrelated workspace records are included. This is not a database backup, complete source-code package or proof of source authenticity.\n'
                    'Use a trusted repository verifier: python -m scripts.verify_review_bundle bundle.zip\n'
                    'An identical standalone copy is included as verify_bundle.py for convenience; do not assume an untrusted archive authenticates its own verifier.\n'
                    'The verifier does not extract files or contact a network. Its scope is names/checksums, references, state hashes and arithmetic, not actual outcomes or legal acceptance.\n'
                    'Execution remains unauthorized and Layer A remains LEGAL_REVIEW_REQUIRED. Hashes are unsigned and the local database is editable.\n')
            add('README.txt',readme.encode())
            add('verify_bundle.py',(ROOT/'scripts/verify_review_bundle.py').read_bytes())
            manifest=dict(format=FORMAT,bundle_id=bundle_id,built_at=built_at,signature='NOT_SIGNED',
                          files={name:dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest()) for name,content in sorted(files.items())})
            manifest_bytes=encoded(manifest)
            if len(manifest_bytes)>MAX_FILE or total+len(manifest_bytes)>MAX_TOTAL:raise ValueError('manifest exceeds archive limit')
            output=io.BytesIO()
            with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as archive:
                for name,content in sorted({**files,'manifest.json':manifest_bytes}.items()):
                    info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o600<<16
                    archive.writestr(info,content)
            payload=output.getvalue();verification=verify_bytes(payload)
            self.store.log(db,actor,'build_synthetic_review_bundle',bundle_id,dict(note=note,snapshots=len(snapshot_files),comparisons=comparison_ids,archive_sha256=hashlib.sha256(payload).hexdigest()))
            return dict(content=payload,filename=bundle_id+'.zip',index=index,verification=verification)
