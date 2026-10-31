import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.request import Request,urlopen

from civic_portfolio.__main__ import server
from civic_portfolio.housing import Housing
from civic_portfolio.store import Conflict,Store


class HousingTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        self.store=Store(Path(self.directory.name)/'test.sqlite3');self.lab=Housing(self.store)

    def create(self,case_id='SYN-CASE',program='DEMO',area='AREA',at='2026-01-01T00:00:00Z'):
        return self.lab.create_case(dict(case_id=case_id,program=program,area=area,at=at,actor='TEST',evidence='Fictional intake',notice_reference=None))

    def consent(self,status='RECORDED',hour=1,case_id='SYN-CASE'):
        return self.lab.consent(case_id,dict(version=self.lab.case(case_id)['version'],status=status,at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST',evidence='Synthetic consent assertion'))

    def event(self,stage,hour,case_id='SYN-CASE',continuity=None,due=None):
        return self.lab.advance(case_id,dict(version=self.lab.case(case_id)['version'],stage=stage,at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST RECORDER',evidence='Synthetic stage and handoff',continuity=continuity,follow_up_due_at=due))

    def verify(self,hour,case_id='SYN-CASE',verifier='TEST VERIFIER',passed=True):
        return self.lab.verify(case_id,dict(version=self.lab.case(case_id)['version'],at=f'2026-01-01T{hour:02}:00:00Z',verifier=verifier,passed=passed,evidence='Synthetic event check'))

    def ready(self,due=None):
        self.create();self.consent();self.event('REFERRED',2);self.event('HANDOFF_ACCEPTED',3);self.event('SERVICE_STARTED',4,due=due)

    def review_request(self):
        return self.lab.create_request(dict(request_id='SYN-REVIEW',case_id='SYN-CASE',description='Fictional review-route concern',at='2026-01-01T09:00:00Z',actor='TEST',evidence='Synthetic request'))

    def test_consent_holds_verified_start_and_no_invented_continuity(self):
        r=self.lab.report();self.assertIsNone(r['referral_to_service_hours']['median'])
        self.create()
        with self.assertRaises(ValueError):self.event('REFERRED',1)
        self.consent();self.event('REFERRED',2);self.event('HANDOFF_ACCEPTED',3);self.event('SERVICE_STARTED',4,due='2026-01-01T08:00:00Z')
        r=self.lab.report('2026-01-01T04:30:00Z');self.assertEqual(r['unverified_service_start_cases'],1)
        self.assertIsNone(r['referral_to_service_hours']['median'])
        with self.assertRaises(ValueError):self.event('CLOSED_WITH_SERVICE',5)
        self.verify(5);r=self.lab.report('2026-01-01T09:00:00Z')
        self.assertEqual(r['referral_to_service_hours']['median'],2)
        self.assertEqual((r['service_cases_without_followup'],r['overdue_followups'],r['verified_continuing_followups']),(1,1,0))
        self.assertFalse(r['execution_authorized'])

    def test_returns_do_not_reset_clock_and_failed_closures_are_separate(self):
        self.create();self.consent();self.event('REFERRED',2);self.event('RETURNED',3);self.event('REFERRED',4);self.event('HANDOFF_ACCEPTED',5);self.event('SERVICE_STARTED',6);self.verify(7)
        for identifier in ['SYN-CLOSED','SYN-OPEN']:
            self.create(identifier);self.consent(case_id=identifier);self.event('REFERRED',2,identifier)
        self.event('CLOSED_NO_SERVICE',3,'SYN-CLOSED')
        r=self.lab.report('2026-01-01T08:00:00Z')
        self.assertEqual((r['referred_cases'],r['returned_referral_events'],r['closed_without_service_cases']),(3,1,1))
        self.assertEqual(r['referral_to_service_hours']['median'],4)
        self.assertEqual(r['unverified_referral_age_hours']['median'],6)

    def test_followup_proof_is_event_specific_and_interruptions_remain_visible(self):
        self.ready();self.verify(4)
        self.event('FOLLOW_UP',5,continuity='UNKNOWN',due='2026-01-01T10:00:00Z')
        self.assertEqual(self.lab.report('2026-01-01T05:30:00Z')['unverified_followups'],1)
        self.verify(6);self.assertEqual(self.lab.report('2026-01-01T06:30:00Z')['verified_unknown_followups'],1)
        self.event('FOLLOW_UP',7,continuity='CONTINUING',due='2026-01-01T10:00:00Z')
        self.assertEqual(self.lab.report('2026-01-01T07:30:00Z')['verified_continuing_followups'],0)
        self.verify(8);self.event('SERVICE_INTERRUPTED',9)
        r=self.lab.report('2026-01-01T10:00:00Z')
        self.assertEqual((r['current_interruption_cases'],r['verified_continuing_followups']),(1,0))
        self.assertEqual(r['referral_to_service_hours']['median'],2)
        self.assertEqual(self.lab.report('2026-01-01T08:30:00Z')['verified_continuing_followups'],1)

    def test_withdrawal_blocks_actions_but_keeps_closure_and_review_routes(self):
        self.ready();self.verify(5);self.consent('WITHDRAWN',6)
        with self.assertRaises(ValueError):self.event('FOLLOW_UP',7,continuity='UNKNOWN')
        self.event('SERVICE_INTERRUPTED',7);self.event('CLOSED_NO_SERVICE',8);self.review_request()
        r=self.lab.report('2026-01-01T09:30:00Z');self.assertEqual(r['consent_hold_cases'],1)
        self.assertEqual(r['open_review_requests'],1)
        for status,hour in [('RESPONDED',10),('OPEN',11)]:
            self.lab.respond('SYN-REVIEW',dict(version=self.lab.request('SYN-REVIEW')['version'],status=status,at=f'2026-01-01T{hour:02}:00:00Z',actor='TEST',evidence='Synthetic recorded response/repeat'))
        self.assertEqual(self.lab.report('2026-01-01T10:30:00Z')['review_response_hours']['median'],1)
        self.assertEqual(self.lab.report('2026-01-01T11:30:00Z')['reopened_review_requests'],1)
        self.assertEqual(self.lab.case('SYN-CASE')['stage'],'CLOSED_NO_SERVICE')

    def test_validation_chronology_and_versions(self):
        self.create()
        with self.assertRaises(Conflict):self.create()
        self.consent()
        with self.assertRaises(ValueError):self.event('REFERRED',0)
        self.event('REFERRED',2)
        with self.assertRaises(Conflict):
            self.lab.consent('SYN-CASE',dict(version=1,status='RECORDED',at='2026-01-01T03:00:00Z',actor='TEST',evidence='Test'))
        with self.assertRaises(ValueError):self.verify(3)
        self.event('HANDOFF_ACCEPTED',3)
        with self.assertRaises(ValueError):self.event('SERVICE_STARTED',4,due='2026-01-01T03:00:00Z')
        self.event('SERVICE_STARTED',4)
        with self.assertRaises(ValueError):self.verify(5,verifier='TEST RECORDER')
        with self.assertRaises(ValueError):self.event('FOLLOW_UP',5,continuity=None)
        self.verify(5)
        with self.assertRaises(ValueError):self.consent('WITHDRAWN',4)
        self.assertEqual(self.lab.case('SYN-CASE')['stage'],'SERVICE_STARTED')

    def test_cutoffs_program_area_filters_and_missing_followup_plans(self):
        self.ready();self.verify(5)
        self.create('SYN-OTHER','OTHER','OTHER AREA')
        self.create('SYN-FUTURE',at='2026-01-03T00:00:00Z')
        r=self.lab.report('2026-01-02T00:00:00Z','DEMO','AREA')
        self.assertEqual((r['cases'],r['verified_service_start_cases'],r['missing_followup_plans']),(1,1,1))
        self.assertEqual(self.lab.report('2026-01-01T04:30:00Z')['referral_to_service_hours']['sample_size'],0)
        self.assertEqual(self.lab.report('2025-12-31T23:00:00Z')['cases'],0)
        self.assertEqual(self.lab.report('2026-01-02T00:00:00Z',program='MISSING')['cases'],0)

    def test_backup_export_and_http_workflow(self):
        self.ready();self.verify(5);self.review_request()
        backup=Path(self.directory.name)/'backup.sqlite3';self.store.backup(backup)
        restored=Housing(Store(backup));self.assertEqual(restored.case('SYN-CASE'),self.lab.case('SYN-CASE'))
        self.assertEqual(restored.request('SYN-REVIEW'),self.lab.request('SYN-REVIEW'))
        self.assertEqual(len(self.store.export()['synthetic_housing']['checks']),1)
        app=server(self.store,0);thread=threading.Thread(target=app.serve_forever,daemon=True);thread.start()
        self.addCleanup(app.server_close);self.addCleanup(thread.join,2);self.addCleanup(app.shutdown)
        base=f'http://127.0.0.1:{app.server_port}'
        with urlopen(base+'/api/housing') as response:token=json.load(response)['token']
        payload=dict(version=1,status='RESPONDED',at='2026-01-01T10:00:00Z',actor='TEST',evidence='Synthetic HTTP review response')
        with urlopen(Request(base+'/api/housing/requests/SYN-REVIEW/events',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Portfolio-Token':token})) as response:self.assertEqual(json.load(response)['status'],'RESPONDED')
        with urlopen(base+'/api/housing/report?program=DEMO&area=AREA') as response:self.assertEqual(json.load(response)['verified_service_start_cases'],1)
        with urlopen(base+'/housing') as response:self.assertIn(b'Synthetic housing referral lab',response.read())


if __name__=='__main__':unittest.main()
