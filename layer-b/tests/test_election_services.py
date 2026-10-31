import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen

from civic_portfolio.__main__ import server
from civic_portfolio.election_services import ElectionServices,ITEMS
from civic_portfolio.store import Conflict,Store


class ElectionServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'test.sqlite3');self.lab=ElectionServices(self.store)

    def create(self,session_id='SYN-SESSION',area='DEMO',channel='IN_PERSON'):
        return self.lab.create_session(dict(session_id=session_id,label='Fictional administrative information service',area=area,channel=channel,opens_at='2026-01-01T08:00:00Z',closes_at='2026-01-01T18:00:00Z',at='2026-01-01T00:00:00Z',actor='TEST',report_reference=None))

    def payload(self,hour,**fields):
        return dict(version=self.lab.session('SYN-SESSION')['version'],at=f'2026-01-01T{hour:02}:00:00Z',**fields)

    def readiness(self,hour=1,status='GAP',item='ACCESSIBLE_CHANNEL'):
        return self.lab.readiness('SYN-SESSION',self.payload(hour,item=item,status=status,criteria_reference='SYNTHETIC CRITERION ONLY',actor='TEST RECORDER',evidence='Fictional scenario readiness assertion'))

    def readiness_check(self,hour=2,item='ACCESSIBLE_CHANNEL',verifier='TEST VERIFIER'):
        return self.lab.verify_readiness('SYN-SESSION',self.payload(hour,item=item,verifier=verifier,passed=True,evidence='Synthetic readiness evidence check'))

    def observation(self,hour=3,observation_id='SYN-OBSERVATION',affected=2):
        return self.lab.create_observation('SYN-SESSION',self.payload(hour,observation_id=observation_id,barrier='PHYSICAL_ACCESS',description='Fictional non-identifying administrative access observation',affected_observations=affected,actor='TEST RECORDER',evidence='Synthetic access observation'))

    def action(self,status,hour):
        return self.lab.advance('SYN-SESSION','SYN-OBSERVATION',self.payload(hour,status=status,correction_reference='Fictional correction label' if status=='CORRECTION_RECORDED' else None,actor='TEST RECORDER',evidence='Synthetic correction or repeated observation'))

    def correction_check(self,hour=5,passed=True,verifier='TEST VERIFIER'):
        return self.lab.verify_correction('SYN-SESSION','SYN-OBSERVATION',self.payload(hour,verifier=verifier,passed=passed,evidence='Synthetic correction check'))

    def test_unknown_and_checked_readiness_never_establish_acceptance_or_validity(self):
        self.create();r=self.lab.report('2026-01-01T01:00:00Z')
        self.assertEqual(r['unknown_or_unverified_items'],5)
        self.assertEqual(r['missing_public_report_references'],1)
        for item in ITEMS:self.readiness(1,'MET',item);self.readiness_check(1,item)
        r=self.lab.report('2026-01-01T02:00:00Z');self.assertEqual(r['checked_met_items'],5)
        self.assertEqual(r['institutional_acceptance'],'NOT_ESTABLISHED')
        self.assertFalse(r['election_validity_assessed']);self.assertFalse(r['representation_assessed']);self.assertFalse(r['execution_authorized'])

    def test_readiness_revision_invalidates_older_check(self):
        self.create();self.readiness();self.readiness_check()
        self.assertEqual(self.lab.report('2026-01-01T02:30:00Z')['checked_gap_items'],1)
        self.readiness(3,'MET')
        self.assertEqual(self.lab.report('2026-01-01T03:30:00Z')['unknown_or_unverified_items'],5)
        self.readiness_check(4)
        self.assertEqual(self.lab.report('2026-01-01T04:30:00Z')['checked_met_items'],1)
        self.assertEqual(self.lab.report('2026-01-01T02:30:00Z')['checked_gap_items'],1)

    def test_corrections_need_current_checks_and_reopening_keeps_original_age(self):
        self.create();self.observation();self.action('CORRECTION_RECORDED',4)
        with self.assertRaises(ValueError):self.action('CLOSED',5)
        self.correction_check();self.action('CLOSED',6)
        r=self.lab.report('2026-01-01T06:30:00Z');self.assertEqual(r['checked_correction_hours']['median'],1)
        self.assertEqual(r['correction_check_lag_hours']['median'],1)
        self.action('REOPENED',7);r=self.lab.report('2026-01-01T08:00:00Z')
        self.assertEqual((r['open_observations'],r['reopen_events']),(1,1))
        self.assertEqual(r['unresolved_observation_age_hours']['median'],5)
        self.assertEqual(r['checked_correction_hours']['sample_size'],0)
        self.assertEqual(self.lab.report('2026-01-01T06:30:00Z')['closed_observations'],1)

    def test_same_timestamp_correction_revisions_cannot_reuse_proof(self):
        self.create();self.observation();self.action('CORRECTION_RECORDED',4);self.correction_check(4);self.action('CLOSED',4);self.action('REOPENED',4)
        self.action('CORRECTION_RECORDED',4)
        with self.assertRaises(ValueError):self.action('CLOSED',4)
        self.correction_check(4);self.action('CLOSED',4)
        self.assertEqual(self.lab.report('2026-01-01T05:00:00Z')['closed_observations'],1)

    def test_unknown_aggregate_counts_and_empty_area_inventory_do_not_imply_disparities(self):
        self.create();self.create('SYN-OTHER','OTHER','PHONE');self.observation(1,affected=None);self.observation(2,'SYN-OVERLAP',2)
        r=self.lab.report('2026-01-01T03:00:00Z');barrier=r['access_observations_by_barrier']['PHYSICAL_ACCESS']
        self.assertEqual((barrier['observations'],barrier['known_affected_counts'],barrier['aggregate_affected_service_observations']),(2,1,2))
        self.assertEqual(r['area_inventory']['OTHER'],dict(sessions=1,observations=0,open_observations=0))
        self.assertEqual(self.lab.report('2026-01-01T03:00:00Z',area='DEMO',channel='IN_PERSON')['sessions'],1)
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['sessions'],0)

    def test_inputs_versions_chronology_and_distinct_identifiers(self):
        self.create()
        with self.assertRaises(Conflict):self.create()
        with self.assertRaises(ValueError):
            self.lab.readiness('SYN-SESSION',self.payload(1,item='ACCESSIBLE_CHANNEL',status='MET',criteria_reference=None,actor='TEST',evidence='Test'))
        self.readiness()
        with self.assertRaises(ValueError):self.readiness_check(verifier='TEST RECORDER')
        self.readiness_check()
        with self.assertRaises(Conflict):
            self.lab.readiness('SYN-SESSION',dict(version=1,item='ACCESSIBLE_CHANNEL',status='UNKNOWN',criteria_reference=None,at='2026-01-01T03:00:00Z',actor='TEST',evidence='Test'))
        with self.assertRaises(ValueError):self.observation(1)
        with self.assertRaises(ValueError):self.observation(3,affected=True)
        self.observation();self.action('CORRECTION_RECORDED',4)
        with self.assertRaises(ValueError):self.correction_check(verifier='TEST RECORDER')
        self.correction_check(passed=False)
        with self.assertRaises(ValueError):self.action('CLOSED',6)

    def test_backup_export_and_http_workflow(self):
        self.create();self.readiness();self.readiness_check();self.observation();self.action('CORRECTION_RECORDED',4);self.correction_check()
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=ElectionServices(Store(backup));self.assertEqual(restored.session('SYN-SESSION'),self.lab.session('SYN-SESSION'))
        self.assertEqual(len(self.store.export()['synthetic_election_services']['correction_checks']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/election-services') as response:token=json.load(response)['token']
        payload=self.payload(6,status='CLOSED',correction_reference=None,actor='TEST',evidence='Synthetic HTTP closure')
        with urlopen(Request(base+'/api/election-services/sessions/SYN-SESSION/observations/SYN-OBSERVATION/events',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:self.assertEqual(json.load(response)['observations'][0]['status'],'CLOSED')
        with urlopen(base+'/api/election-services/report?area=DEMO&channel=IN_PERSON') as response:self.assertFalse(json.load(response)['election_validity_assessed'])
        with urlopen(base+'/election-services') as response:self.assertIn(b'Synthetic election-service evidence lab',response.read())


if __name__=='__main__':unittest.main()
