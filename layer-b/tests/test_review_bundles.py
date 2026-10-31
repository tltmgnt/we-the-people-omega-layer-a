import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import zipfile
from civic_portfolio.scenarios import Scenarios
from civic_portfolio.scenario_comparisons import ScenarioComparisons
from civic_portfolio.review_bundles import ReviewBundles
from civic_portfolio.store import Store
from civic_portfolio.__main__ import server
from scripts.verify_review_bundle import verify_bytes

class ReviewBundleTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/'db.sqlite3';self.store=Store(self.path);self.lab=Scenarios(self.store);self.bundles=ReviewBundles(self.store)
        self.lab.create(dict(run_id='SYN-SOURCE',workflow='p024',label='Selected fictional record',start_at='2026-01-01T00:00:00Z',actor='RECORDER',note='Selected note'))
        self.command('SYN-SOURCE','PRESET',stage='CLOSED',quality='PASS')
        self.first=self.command('SYN-SOURCE','OBSERVE',metric_id='referral_wait_minutes',value=30,numerator=None,denominator=None,missing_reason=None)['version']
        self.second=self.command('SYN-SOURCE','OBSERVE',metric_id='referral_wait_minutes',value=15,numerator=None,denominator=None,missing_reason=None)['version']
    def command(self,key,action,**params):
        return self.lab.command(key,dict(version=self.lab.run(key)['version'],action=action,parameters=params,actor='CHECKER',note='Fictional selected evidence'))
    def build(self,selections=None,comparisons=None):
        if selections is None:selections=[dict(run_id='SYN-SOURCE',sequence=self.second)]
        return self.bundles.build(dict(bundle_id='SYN-REVIEW',selections=selections,comparison_ids=comparisons or [],actor='REVIEWER',note='Selected fictional scope only'))
    def files(self,raw):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:return {name:z.read(name) for name in z.namelist()}
    def rewrite(self,files,reauthor_manifest=False):
        if reauthor_manifest:
            manifest=json.loads(files['manifest.json'])
            manifest['files']={name:dict(bytes=len(content),sha256=hashlib.sha256(content).hexdigest()) for name,content in files.items() if name!='manifest.json'}
            files['manifest.json']=json.dumps(manifest).encode()
        result=io.BytesIO()
        with zipfile.ZipFile(result,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,content in files.items():z.writestr(name,content)
        return result.getvalue()
    def comparison(self):
        return ScenarioComparisons(self.store).create(dict(comparison_id='SYN-COMPARE',baseline_run_id='SYN-SOURCE',baseline_sequence=self.first,alternative_run_id='SYN-SOURCE',alternative_sequence=self.second,actor='REVIEWER',note='Fictional comparison'))
    def test_selected_scope_architecture_and_independent_verifier(self):
        self.lab.create(dict(run_id='SYN-UNRELATED',workflow='p007',label='UNRELATED PRIVATE MARKER',start_at='2026-01-01T00:00:00Z',actor='RECORDER',note='DO NOT INCLUDE THIS NOTE'))
        bundle=self.build();result=verify_bytes(bundle['content']);files=self.files(bundle['content'])
        self.assertEqual(result['verified_snapshots'],1);self.assertFalse(result['execution_authorized'])
        self.assertNotIn(b'DO NOT INCLUDE THIS NOTE',b'\n'.join(files.values()))
        architecture=json.loads(files['architecture/five-layer-summary.json']);self.assertEqual([l['key'] for l in architecture['layers']],list('ABCDE'))
        self.assertFalse(architecture['full_documents_imported']);self.assertIn('verify_bundle.py',files)
    def test_comparison_resolves_both_snapshots_and_saved_arithmetic(self):
        self.comparison();bundle=self.build([],['SYN-COMPARE']);result=verify_bytes(bundle['content'])
        self.assertEqual(result['verified_comparisons'],1);self.assertEqual(result['verified_snapshots'],2)
        saved=json.loads(self.files(bundle['content'])['comparisons/SYN-COMPARE.json'])
        self.assertEqual(saved['result']['metrics'][0]['delta'],-15)
    def test_capstone_dependencies_are_included_transitively(self):
        self.lab.create(dict(run_id='SYN-CAPSTONE',workflow='p050',label='Selected capstone',start_at='2026-01-01T00:00:00Z',actor='RECORDER',note='Fictional only'))
        self.command('SYN-CAPSTONE','ATTACH',source_run_id='SYN-SOURCE',source_sequence=self.second)
        cap=self.command('SYN-CAPSTONE','PRESET',stage='CLOSED',quality='PASS')
        bundle=self.build([dict(run_id='SYN-CAPSTONE',sequence=cap['version'])])
        self.assertEqual(verify_bytes(bundle['content'])['verified_snapshots'],2)
    def test_file_tampering_fails_checksum(self):
        bundle=self.build();files=self.files(bundle['content']);name=bundle['index']['snapshot_files'][0]
        files[name]+=b' '
        with self.assertRaises(ValueError):verify_bytes(self.rewrite(files))
    def test_reauthored_manifest_cannot_claim_execution_authority(self):
        files=self.files(self.build()['content']);boundary=json.loads(files['boundary.json']);boundary['execution_authorized']=True
        files['boundary.json']=json.dumps(boundary).encode()
        with self.assertRaises(ValueError):verify_bytes(self.rewrite(files,True))
    def test_unsafe_extra_and_duplicate_names_are_rejected(self):
        files=self.files(self.build()['content']);files['../escape.txt']=b'unsafe'
        with self.assertRaises(ValueError):verify_bytes(self.rewrite(files,True))
        files=self.files(self.build()['content']);files['extra.txt']=b'unlisted'
        with self.assertRaises(ValueError):verify_bytes(self.rewrite(files))
        raw=io.BytesIO(self.build()['content'])
        with zipfile.ZipFile(raw,'a') as z:z.writestr('boundary.json',b'{}')
        with self.assertRaises(ValueError):verify_bytes(raw.getvalue())
    def test_comparison_arithmetic_is_checked_even_with_matching_file_hashes(self):
        self.comparison();files=self.files(self.build([],['SYN-COMPARE'])['content'])
        comparison=json.loads(files['comparisons/SYN-COMPARE.json']);comparison['result']['metrics'][0]['delta']=-14
        files['comparisons/SYN-COMPARE.json']=json.dumps(comparison).encode()
        with self.assertRaises(ValueError):verify_bytes(self.rewrite(files,True))
    def test_snapshot_hash_is_checked_beyond_file_manifest(self):
        bundle=self.build();files=self.files(bundle['content']);name=bundle['index']['snapshot_files'][0]
        snapshot=json.loads(files[name]);snapshot['event']['state']['clock_minutes']+=1;files[name]=json.dumps(snapshot).encode()
        with self.assertRaises(ValueError):verify_bytes(self.rewrite(files,True))
    def test_invalid_scope_and_size_failure_do_not_write_build_audit(self):
        with self.store.connect() as db:count=db.execute('SELECT COUNT(*) FROM audit').fetchone()[0]
        with self.assertRaises(ValueError):self.build([])
        with self.assertRaises(ValueError):self.build([dict(run_id='SYN-SOURCE',sequence=self.second)]*2)
        with self.assertRaises(ValueError):self.build([dict(run_id='../bad',sequence=1)])
        with patch('civic_portfolio.review_bundles.MAX_FILE',10):
            with self.assertRaises(ValueError):self.build()
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM audit').fetchone()[0],count)
    def test_source_runs_are_unchanged_and_build_is_audited(self):
        before=self.lab.run('SYN-SOURCE');self.build();self.assertEqual(self.lab.run('SYN-SOURCE'),before)
        with self.store.connect() as db:self.assertEqual(db.execute("SELECT COUNT(*) FROM audit WHERE action='build_synthetic_review_bundle'").fetchone()[0],1)
        self.assertFalse(self.store.project('024')['execution_authorized'])
    def test_cli_export_verify_and_refuse_overwrite(self):
        path=Path(self.tmp.name)/'review.zip'
        args=[sys.executable,'-m','civic_portfolio','--db',str(self.path),'export-review-bundle','--bundle-id','SYN-CLI-REVIEW','--snapshot','SYN-SOURCE:'+str(self.second),'--actor','TEST','--note','Fictional selected scope','--output',str(path)]
        result=subprocess.run(args,capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
        verify=subprocess.run([sys.executable,'-m','scripts.verify_review_bundle',str(path)],capture_output=True,text=True)
        self.assertEqual(verify.returncode,0,verify.stderr);self.assertEqual(json.loads(verify.stdout)['verified_snapshots'],1)
        original=path.read_bytes();again=subprocess.run(args,capture_output=True,text=True)
        self.assertNotEqual(again.returncode,0);self.assertEqual(path.read_bytes(),original)
    def test_http_download_requires_token_and_has_safe_headers(self):
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base='http://127.0.0.1:'+str(app.server_port);boot=json.load(urlopen(base+'/api/scenarios'))
        self.assertIn(b'Build a selected review bundle',urlopen(base+'/review-bundles').read())
        payload=json.dumps(dict(bundle_id='SYN-HTTP-REVIEW',selections=[dict(run_id='SYN-SOURCE',sequence=self.second)],comparison_ids=[],actor='TEST',note='Selected fictional data')).encode()
        with self.assertRaises(HTTPError) as error:urlopen(Request(base+'/api/review-bundles',data=payload,headers={'Content-Type':'application/json'}))
        self.assertEqual(error.exception.code,403)
        response=urlopen(Request(base+'/api/review-bundles',data=payload,headers={'Content-Type':'application/json','X-Portfolio-Token':boot['token']}))
        self.assertEqual(response.headers.get_content_type(),'application/zip');self.assertIn('SYN-HTTP-REVIEW.zip',response.headers['Content-Disposition'])
        self.assertEqual(verify_bytes(response.read())['verified_snapshots'],1)
