import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen

from civic_portfolio.__main__ import server
from civic_portfolio.rights import Rights
from civic_portfolio.store import Conflict,Store
from scripts.validate_packet import ROOT,require_valid


class RightsTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'test.sqlite3');self.lab=Rights(self.store)

    def create(self,case_id='SYN-RIGHTS',jurisdiction='FICTIONAL AREA'):
        return self.lab.create_case(dict(case_id=case_id,proposal_id='SYN-PROPOSAL',summary='Fictional bounded service proposal',institution='Fictional institution',jurisdiction=jurisdiction,at='2026-01-01T00:00:00Z',actor='TEST'))

    def payload(self,hour,**fields):
        return dict(version=self.lab.case('SYN-RIGHTS')['version'],at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST',**fields)

    def snapshot(self,hour=1,content='\nFictional evidence Ω\n'):
        return self.lab.add_evidence('SYN-RIGHTS',self.payload(hour,evidence_id='SYN-EVIDENCE',content=content,origin='fictional-source.txt'))

    def pins(self,revision=None):
        records=self.lab.case('SYN-RIGHTS')['evidence'];e=records[-1] if revision is None else next(e for e in records if e['revision']==revision)
        return [dict(evidence_id=e['evidence_id'],revision=e['revision'],sha256=e['sha256'])]

    def screen(self,hour=2,pins=None,name='A1'):
        return self.lab.screen('SYN-RIGHTS',self.payload(hour,domain=name,relevance='RELEVANT',rationale='Fictional screening rationale; applicability unassessed',evidence_pins=pins or []))

    def question(self,hour=3,pins=None):
        return self.lab.add_question('SYN-RIGHTS',self.payload(hour,question_id='SYN-QUESTION',domain='A1',question='Which process condition needs qualified review?',alternative_explanation='Evidence may be incomplete rather than showing a rights failure.',limitations='Fictional scenario; no actual authority or individual assessed.',evidence_pins=pins or []))

    def response(self,hour=4,status='RESPONSE_RECORDED',pins=None):
        return self.lab.respond('SYN-RIGHTS','SYN-QUESTION',self.payload(hour,status=status,evidence_pins=pins or [],evidence='Fictional local response or challenge; no legal finding'))

    def test_initial_screening_and_permanent_hold(self):
        self.create();r=self.lab.report('2026-01-01T01:00:00Z')
        self.assertEqual((r['screened_current_domains'],r['unassessed_or_stale_domains']),(0,7))
        self.screen(1);r=self.lab.report('2026-01-01T02:00:00Z')
        self.assertEqual((r['screened_current_domains'],r['screenings_without_evidence']),(1,1))
        self.assertEqual(r['review_status'],'LEGAL_REVIEW_REQUIRED');self.assertEqual(r['qualified_legal_reviews'],0)
        self.assertFalse(r['execution_authorized'])

    def test_exact_snapshots_pins_and_integrity(self):
        self.create();raw='\nFictional evidence Ω\n';self.snapshot(content=raw)
        snapshot=self.lab.case('SYN-RIGHTS')['evidence'][0]
        self.assertEqual(snapshot['content'],raw)
        self.assertEqual(snapshot['sha256'],hashlib.sha256(raw.encode()).hexdigest())
        pin=self.pins()[0]
        for pins in [[{**pin,'sha256':'0'*64}],[pin,pin],[{**pin,'revision':True}],[{**pin,'evidence_id':'SYN-UNKNOWN'}]]:
            with self.subTest(pins=pins),self.assertRaises(ValueError):self.screen(pins=pins)
        with self.store.connect() as db:db.execute("UPDATE rights_evidence SET content='tampered'")
        with self.assertRaises(ValueError):self.lab.bundle('SYN-RIGHTS')

    def test_source_revisions_mark_dependencies_stale_without_rewriting_history(self):
        self.create();self.snapshot();pin1=self.pins();self.screen(pins=pin1);self.question(pins=pin1);self.response(pins=pin1)
        r=self.lab.report('2026-01-01T04:30:00Z');self.assertEqual(r['current_evidence_responses'],1)
        self.snapshot(5,'Fictional revised evidence')
        r=self.lab.report('2026-01-01T05:30:00Z')
        self.assertEqual((r['stale_evidence_questions'],r['current_evidence_responses'],r['screened_current_domains']),(1,0,0))
        self.assertEqual(self.lab.report('2026-01-01T04:30:00Z')['current_evidence_responses'],1)
        self.response(6,pins=self.pins());self.screen(7,pins=self.pins())
        r=self.lab.report('2026-01-01T08:00:00Z');self.assertEqual((r['current_evidence_responses'],r['screened_current_domains']),(1,1))
        self.assertEqual(len(self.lab.case('SYN-RIGHTS')['evidence']),2)

    def test_questions_candidates_and_challenges_do_not_imply_applicable_law(self):
        self.create();self.snapshot();self.question(2)
        with self.assertRaises(ValueError):self.response(3)
        self.response(3,pins=self.pins());self.response(4,'OPEN',self.pins())
        self.lab.add_authority('SYN-RIGHTS',self.payload(5,authority_id='SYN-CANDIDATE',reference='Fictional candidate source label',proposed_scope='Unassessed scenario scope only',source_date=None))
        r=self.lab.report('2026-01-01T06:00:00Z');self.assertEqual((r['reopen_events'],r['open_or_stale_questions'],r['unknown_authority_dates']),(1,1,1))
        self.assertEqual(r['unanswered_question_age_hours']['median'],4)
        self.assertEqual(self.lab.bundle('SYN-RIGHTS')['record']['legal_authorities'],[])

    def test_layer_a_bridge_is_schema_valid_but_always_blocked(self):
        self.create();self.snapshot();self.question(2,pins=self.pins());self.response(3,pins=self.pins())
        for i in range(1,8):self.screen(3,pins=self.pins(),name=f'A{i}')
        bundle=self.lab.bundle('SYN-RIGHTS');record=bundle['record']
        require_valid(record,ROOT/'vendor/layer-a/review-record.schema.json')
        self.assertEqual(record['review_status'],'LEGAL_REVIEW_REQUIRED')
        self.assertNotIn('reviewer_id',record);self.assertNotIn('reviewed_at',record)
        self.assertTrue(record['unresolved_questions']);self.assertTrue(record['conditions']);self.assertTrue(record['jurisdictional_limitations'])
        self.assertEqual(set(record['evidence_ids']),{e['evidence_id'] for e in bundle['evidence_manifest']})
        draft=Path(self.directory.name)/'draft.json';draft.write_text(json.dumps(record))
        result=subprocess.run([sys.executable,str(ROOT.parent/'scripts/validate_review.py'),'--require-ready',str(draft)],capture_output=True,text=True)
        self.assertEqual(result.returncode,2,result.stderr);self.assertIn('BLOCKED',result.stdout)

    def test_versions_chronology_inputs_and_cutoff_filters(self):
        self.create()
        with self.assertRaises(Conflict):self.create()
        self.snapshot()
        with self.assertRaises(Conflict):
            self.lab.screen('SYN-RIGHTS',dict(version=1,domain='A1',relevance='RELEVANT',rationale='Test',evidence_pins=[],at='2026-01-01T02:00:00Z',actor='TEST'))
        with self.assertRaises(ValueError):self.screen(0)
        with self.assertRaises(ValueError):self.screen(name='A8')
        self.question(2)
        with self.assertRaises(ValueError):self.response(3,'READY_FOR_HUMAN_DECISION',self.pins())
        self.create('SYN-OTHER','OTHER FICTIONAL AREA')
        self.assertEqual(self.lab.report('2026-01-01T03:00:00Z','FICTIONAL AREA')['cases'],1)
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['cases'],0)

    def test_backup_export_and_http_workflow(self):
        self.create();self.snapshot();self.question(2,pins=self.pins());self.response(3,pins=self.pins())
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=Rights(Store(backup));self.assertEqual(restored.case('SYN-RIGHTS'),self.lab.case('SYN-RIGHTS'))
        self.assertEqual(len(self.store.export()['synthetic_rights']['evidence']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/rights') as response:token=json.load(response)['token']
        payload=self.payload(4,status='OPEN',evidence_pins=self.pins(),evidence='Synthetic HTTP challenge')
        with urlopen(Request(base+'/api/rights/cases/SYN-RIGHTS/questions/SYN-QUESTION/events',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:self.assertEqual(json.load(response)['questions'][0]['events'][-1]['status'],'OPEN')
        with urlopen(base+'/api/rights/cases/SYN-RIGHTS/layer-a') as response:self.assertEqual(json.load(response)['review_status'],'LEGAL_REVIEW_REQUIRED')
        with urlopen(base+'/api/rights/cases/SYN-RIGHTS/bundle') as response:self.assertEqual(len(json.load(response)['evidence_manifest']),1)
        with urlopen(base+'/rights') as response:self.assertIn(b'Synthetic rights evidence lab',response.read())


if __name__=='__main__':unittest.main()
